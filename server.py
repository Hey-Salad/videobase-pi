"""
Videobase Pi - Single Camera RTSP Server
FastAPI-based video streaming server with WebSocket support for real-time video delivery.

Features:
- Single RTSP camera stream processing via GStreamer
- WebSocket endpoint for real-time frame delivery (base64-encoded JPEG)
- MJPEG streaming endpoint for browser compatibility
- Health monitoring endpoint
- CORS support for remote frontend access

Usage:
    python server.py

Default port: 9200
WebSocket endpoint: ws://localhost:9200/ws
MJPEG stream: http://localhost:9200/stream
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
from fastapi.responses import StreamingResponse
import uvicorn

# Initialize GStreamer
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GLib
import threading

class RTSPViewer:
    def __init__(self, rtsp_url="rtsp://admin:admin@192.168.1.136:554/live"):
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing RTSP Viewer...")

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

        # Create GLib main loop
        self.loop = GLib.MainLoop()
        self.loop_thread = threading.Thread(target=self.loop.run)
        self.loop_thread.daemon = True
        self.loop_thread.start()

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
        if hasattr(self, 'loop') and self.loop.is_running():
            self.loop.quit()
        if hasattr(self, 'loop_thread'):
            self.loop_thread.join()
        self.logger.info("Cleanup complete")


# Initialize FastAPI app
app = FastAPI(title="Videobase Pi API")

# Configure CORS for Cloudflare Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Cloudflare Pages domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RTSP viewer
viewer = None

@app.on_event("startup")
async def startup_event():
    global viewer
    viewer = RTSPViewer()

@app.on_event("shutdown")
async def shutdown_event():
    global viewer
    if viewer:
        viewer.cleanup()

@app.get("/")
async def root():
    return {
        "message": "Videobase Pi API",
        "version": "2.0",
        "endpoints": {
            "websocket": "/ws",
            "stream": "/stream",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "frame_count": viewer.frame_count if viewer else 0
    }

@app.get("/stream")
async def stream():
    """MJPEG stream endpoint"""
    async def generate():
        while True:
            if viewer:
                frame_bytes = viewer.get_frame_jpeg()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            await asyncio.sleep(0.033)  # ~30 FPS

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            if viewer:
                # Get frame as JPEG
                frame_bytes = viewer.get_frame_jpeg()

                # Encode to base64 for WebSocket transmission
                frame_base64 = base64.b64encode(frame_bytes).decode('utf-8')

                # Send frame data
                await websocket.send_json({
                    "type": "frame",
                    "data": frame_base64,
                    "timestamp": datetime.now().isoformat(),
                    "frame_count": viewer.frame_count
                })

            # Control frame rate (30 FPS)
            await asyncio.sleep(0.033)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9200,
        log_level="info"
    )
