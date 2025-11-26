"""
Videobase Pi - Multi-Camera RTSP Server with AI Support
Advanced FastAPI server supporting multiple RTSP camera streams with Hailo AI integration.

Features:
- Multi-camera RTSP stream processing (3 cameras configured)
- Per-camera WebSocket endpoints for real-time frame delivery
- AI inference data endpoint for Hailo integration (/ws/{camera_id}/ai)
- Device information endpoint (CPU temp, memory, uptime)
- Health monitoring for all camera streams
- Shared GLib main loop for efficient resource usage
- CORS support for remote frontend access

Camera Configuration:
- camera1: 192.168.1.136:554
- camera2: 192.168.1.110:554
- camera3: 192.168.1.106:554

Usage:
    python server_multi_rtsp.py

Default port: 9200
WebSocket endpoint: ws://localhost:9200/ws/{camera_id}
AI data endpoint: ws://localhost:9200/ws/{camera_id}/ai
Device info: http://localhost:9200/device-info
"""
import gi
import numpy as np
import asyncio
import logging
import base64
import cv2
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import threading

# Initialize GStreamer
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GLib

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Camera configurations
CAMERAS = {
    "camera1": {
        "rtsp_url": "rtsp://admin:admin@192.168.1.136:554/live",
        "name": "Camera 1 (136)"
    },
    "camera2": {
        "rtsp_url": "rtsp://admin:admin@192.168.1.110:554/live",
        "name": "Camera 2 (110)"
    },
    "camera3": {
        "rtsp_url": "rtsp://admin:admin@192.168.1.106:554/live",
        "name": "Camera 3 (106)"
    }
}

class RTSPViewer:
    def __init__(self, camera_id, rtsp_url):
        self.camera_id = camera_id
        self.logger = logging.getLogger(f"{__name__}.{camera_id}")
        self.logger.info(f"Initializing RTSP Viewer for {rtsp_url}...")

        # Initialize GStreamer
        Gst.init(None)

        # Create pipeline
        pipeline_str = (
            f'rtspsrc location={rtsp_url} protocols=tcp latency=0 ! '
            'queue ! rtph264depay ! h264parse ! openh264dec ! '
            'videoconvert ! video/x-raw,format=BGR ! '
            'appsink name=sink emit-signals=true max-buffers=1 drop=true'
        )

        self.logger.info(f"Creating pipeline: {pipeline_str}")
        self.pipeline = Gst.parse_launch(pipeline_str)

        # Get appsink and connect to callback
        self.appsink = self.pipeline.get_by_name('sink')
        self.appsink.connect('new-sample', self.on_new_sample)

        # Initialize frame storage
        self.latest_frame = None
        self.frame_count = 0
        self.last_frame_time = datetime.now()

        # Add bus watch
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_bus_message)

        # Start the pipeline
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            self.logger.error("Failed to start pipeline")
            raise RuntimeError("Failed to start pipeline")

        self.logger.info("Pipeline is playing")

    def on_bus_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.logger.error(f"Error: {err}, Debug: {debug}")
        elif t == Gst.MessageType.EOS:
            self.logger.info("End of stream")
        elif t == Gst.MessageType.STATE_CHANGED:
            old_state, new_state, pending_state = message.parse_state_changed()
            self.logger.debug(f"State changed from {old_state} to {new_state}")

    def on_new_sample(self, sink):
        sample = sink.emit('pull-sample')
        if sample:
            buf = sample.get_buffer()
            caps = sample.get_caps()

            # Get buffer data
            success, map_info = buf.map(Gst.MapFlags.READ)
            if not success:
                return Gst.FlowReturn.ERROR

            # Get dimensions from caps
            caps_struct = caps.get_structure(0)
            height = caps_struct.get_value('height')
            width = caps_struct.get_value('width')

            # Create numpy array from buffer data
            frame = np.ndarray(
                shape=(height, width, 3),
                dtype=np.uint8,
                buffer=map_info.data
            ).copy()

            # Unmap buffer
            buf.unmap(map_info)

            # Update frame and metrics
            self.latest_frame = frame
            self.frame_count += 1

            # Calculate FPS
            current_time = datetime.now()
            time_diff = (current_time - self.last_frame_time).total_seconds()
            fps = 1 / time_diff if time_diff > 0 else 0
            self.last_frame_time = current_time

            if self.frame_count % 30 == 0:
                self.logger.info(f"FPS: {fps:.2f}")

            return Gst.FlowReturn.OK
        return Gst.FlowReturn.ERROR

    def get_frame(self):
        if self.latest_frame is not None:
            return self.latest_frame
        return np.zeros((480, 640, 3), dtype=np.uint8)

    def get_frame_jpeg(self):
        """Get current frame as JPEG bytes"""
        frame = self.get_frame()
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return buffer.tobytes()

    def cleanup(self):
        self.logger.info("Cleaning up...")
        if hasattr(self, 'pipeline'):
            self.pipeline.set_state(Gst.State.NULL)
        self.logger.info("Cleanup complete")


# Initialize FastAPI app
app = FastAPI(title="Videobase Pi API - Multi-Camera RTSP")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RTSP viewers
viewers = {}
camera_meta = {
    cam_id: {
        "ai_data": None,
        "last_updated": None,
    }
    for cam_id in CAMERAS.keys()
}
glib_loop = None
glib_thread = None

@app.on_event("startup")
async def startup_event():
    global viewers, glib_loop, glib_thread

    # Create GLib main loop in a separate thread
    glib_loop = GLib.MainLoop()
    glib_thread = threading.Thread(target=glib_loop.run)
    glib_thread.daemon = True
    glib_thread.start()

    # Initialize viewers for each camera
    for camera_id, config in CAMERAS.items():
        try:
            viewers[camera_id] = RTSPViewer(camera_id, config["rtsp_url"])
        except Exception as e:
            logger.error(f"Failed to initialize {camera_id}: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    global viewers, glib_loop
    for camera_id, viewer in viewers.items():
        viewer.cleanup()
    if glib_loop and glib_loop.is_running():
        glib_loop.quit()
    if glib_thread:
        glib_thread.join()

@app.get("/")
async def root():
    return {
        "message": "Videobase Pi API - Multi-Camera RTSP",
        "version": "5.0",
        "cameras": {
            cam_id: {
                "name": config["name"],
                "rtsp_url": config["rtsp_url"],
                "frame_count": viewers[cam_id].frame_count if cam_id in viewers else 0
            }
            for cam_id, config in CAMERAS.items()
        },
        "endpoints": {
            "websocket": "/ws/{camera_id}",
            "health": "/health",
            "device_info": "/device-info"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "cameras": {
            cam_id: {
                "active": cam_id in viewers,
                "frame_count": viewers[cam_id].frame_count if cam_id in viewers else 0
            }
            for cam_id in CAMERAS.keys()
        }
    }

@app.get("/device-info")
async def device_info():
    """Get Raspberry Pi device information"""
    import socket
    import subprocess
    import platform

    info = {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "machine": platform.machine(),
    }

    # Get IP address
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        info["ip_address"] = s.getsockname()[0]
        s.close()
    except:
        info["ip_address"] = "Unknown"

    # Get CPU temperature (Raspberry Pi specific)
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = float(f.read().strip()) / 1000.0
            info["cpu_temp_c"] = round(temp, 1)
            info["cpu_temp_f"] = round(temp * 9/5 + 32, 1)
    except:
        info["cpu_temp_c"] = None
        info["cpu_temp_f"] = None

    # Get CPU usage
    try:
        result = subprocess.run(['uptime'], capture_output=True, text=True)
        uptime_output = result.stdout.strip()
        # Extract load average
        if 'load average:' in uptime_output:
            load = uptime_output.split('load average:')[1].strip().split(',')[0]
            info["cpu_load"] = float(load)
    except:
        info["cpu_load"] = None

    # Get memory info
    try:
        with open("/proc/meminfo", "r") as f:
            meminfo = f.readlines()
            mem_total = int([line for line in meminfo if 'MemTotal' in line][0].split()[1]) / 1024  # MB
            mem_available = int([line for line in meminfo if 'MemAvailable' in line][0].split()[1]) / 1024  # MB
            info["memory_total_mb"] = round(mem_total)
            info["memory_available_mb"] = round(mem_available)
            info["memory_used_percent"] = round((1 - mem_available / mem_total) * 100, 1)
    except:
        info["memory_total_mb"] = None
        info["memory_available_mb"] = None
        info["memory_used_percent"] = None

    # Get uptime
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.read().split()[0])
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            info["uptime"] = f"{days}d {hours}h {minutes}m"
            info["uptime_seconds"] = int(uptime_seconds)
    except:
        info["uptime"] = "Unknown"
        info["uptime_seconds"] = None

    return info

@app.websocket("/ws/{camera_id}")
async def websocket_endpoint(websocket: WebSocket, camera_id: str):
    """WebSocket endpoint for browser clients - per camera"""
    if camera_id not in CAMERAS:
        await websocket.close(code=1008, reason=f"Unknown camera: {camera_id}")
        return

    if camera_id not in viewers:
        await websocket.close(code=1008, reason=f"Camera {camera_id} not initialized")
        return

    await websocket.accept()
    viewer = viewers[camera_id]
    logger.info(f"[{camera_id}] Client connected")

    try:
        while True:
            # Get frame as JPEG
            frame_bytes = viewer.get_frame_jpeg()

            # Encode to base64 for WebSocket transmission
            frame_base64 = base64.b64encode(frame_bytes).decode('utf-8')

            # Send frame data with AI inference placeholder
            await websocket.send_json({
                "type": "frame",
                "camera_id": camera_id,
                "data": frame_base64,
                "timestamp": datetime.now().isoformat(),
                "frame_count": viewer.frame_count,
                "ai_data": camera_meta.get(camera_id, {}).get("ai_data")
            })

            # Control frame rate (30 FPS)
            await asyncio.sleep(0.033)

    except WebSocketDisconnect:
        logger.info(f"[{camera_id}] Client disconnected")
    except Exception as e:
        logger.error(f"[{camera_id}] WebSocket error: {e}")

@app.websocket("/ws/{camera_id}/ai")
async def ai_data_endpoint(websocket: WebSocket, camera_id: str):
    """WebSocket endpoint to receive AI inference data from cameras"""
    if camera_id not in CAMERAS:
        await websocket.close(code=1008, reason=f"Unknown camera: {camera_id}")
        return

    await websocket.accept()
    logger.info(f"[{camera_id}] AI data stream connected")

    try:
        while True:
            # Receive AI inference data from the camera
            data = await websocket.receive_json()

            # Log and potentially process AI data
            if "detections" in data:
                logger.debug(f"[{camera_id}] AI detections: {len(data['detections'])} objects")

            meta = camera_meta.setdefault(camera_id, {})
            ai_timestamp = datetime.now().isoformat()
            meta["ai_data"] = {
                "payload": data,
                "timestamp": ai_timestamp,
            }
            meta["last_updated"] = ai_timestamp

            logger.debug(f"[{camera_id}] Stored AI metadata")

    except WebSocketDisconnect:
        logger.info(f"[{camera_id}] AI data stream disconnected")
    except Exception as e:
        logger.error(f"[{camera_id}] AI data error: {e}")

# Legacy endpoint - defaults to camera1
@app.websocket("/ws")
async def websocket_legacy(websocket: WebSocket):
    """Legacy WebSocket endpoint - defaults to camera1"""
    await websocket_endpoint(websocket, "camera1")

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9200,
        log_level="info"
    )
