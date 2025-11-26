"""
Hailo AI Camera Client
Standalone client that connects to RTSP camera streams, performs Hailo AI inference,
and sends detection results to the multi-camera server via WebSocket.

Features:
- RTSP stream processing via GStreamer
- Real-time object detection using Hailo-8L AI accelerator
- Configurable inference FPS to manage load
- WebSocket communication with server for AI data delivery
- Automatic reconnection on connection loss
- Performance monitoring and logging

Architecture:
- GStreamer pipeline: RTSP -> H.264 decode -> BGR frames
- Hailo inference: YOLOv8 object detection on frames
- WebSocket: Send detection results to server's /ws/{camera_id}/ai endpoint

Usage:
    python hailo_camera_client.py \\
        --camera-id camera1 \\
        --rtsp-url rtsp://admin:admin@192.168.1.136:554/live \\
        --server ws://localhost:9200 \\
        --fps 5

Arguments:
    --camera-id: Camera identifier (must match server config)
    --rtsp-url: RTSP stream URL
    --server: Server WebSocket URL
    --model: Path to Hailo HEF model (default: /usr/share/hailo-models/yolov8s_h8l.hef)
    --fps: Inference FPS limit (default: 5)

Requirements:
- Hailo-8L AI accelerator
- hailo_platform Python library
- GStreamer with RTSP support
- Server running server_multi_rtsp.py
"""
import asyncio
import websockets
import json
import logging
import gi
import numpy as np
from datetime import datetime
from typing import Dict, Optional
import argparse

gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GLib
import threading

from hailo_inference import HailoDetector, format_detections_for_frontend

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HailoRTSPClient:
    """RTSP client with Hailo AI inference"""

    def __init__(
        self,
        camera_id: str,
        rtsp_url: str,
        server_url: str,
        model_path: str = "/usr/share/hailo-models/yolov8s_h8l.hef",
        fps_limit: int = 5  # Inference FPS (lower to reduce CPU/Hailo load)
    ):
        """
        Initialize Hailo RTSP client

        Args:
            camera_id: Camera identifier (e.g., 'camera1')
            rtsp_url: RTSP stream URL
            server_url: WebSocket server URL for AI data
            model_path: Path to Hailo HEF model
            fps_limit: Max inference FPS
        """
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.server_url = server_url
        self.fps_limit = fps_limit
        self.frame_interval = 1.0 / fps_limit

        # Initialize GStreamer
        Gst.init(None)

        # Create pipeline
        pipeline_str = (
            f'rtspsrc location={rtsp_url} protocols=tcp latency=0 ! '
            'queue ! rtph264depay ! h264parse ! openh264dec ! '
            'videoconvert ! video/x-raw,format=BGR ! '
            'appsink name=sink emit-signals=true max-buffers=1 drop=true'
        )

        logger.info(f"[{camera_id}] Creating pipeline: {pipeline_str}")
        self.pipeline = Gst.parse_launch(pipeline_str)

        # Get appsink
        self.appsink = self.pipeline.get_by_name('sink')
        self.appsink.connect('new-sample', self.on_new_sample)

        # Frame storage
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.last_inference_time = 0

        # Add bus watch
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_bus_message)

        # Initialize Hailo detector
        logger.info(f"[{camera_id}] Initializing Hailo detector...")
        self.detector = HailoDetector(hef_path=model_path)

        # WebSocket connection
        self.ws = None
        self.running = False

        # GLib loop
        self.glib_loop = None
        self.glib_thread = None

    def on_bus_message(self, bus, message):
        """Handle GStreamer bus messages"""
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"[{self.camera_id}] Pipeline error: {err}, {debug}")
        elif t == Gst.MessageType.EOS:
            logger.info(f"[{self.camera_id}] End of stream")
        elif t == Gst.MessageType.STATE_CHANGED:
            old_state, new_state, pending_state = message.parse_state_changed()
            logger.debug(f"[{self.camera_id}] State: {old_state} -> {new_state}")

    def on_new_sample(self, sink):
        """Callback for new frames from GStreamer"""
        sample = sink.emit('pull-sample')
        if sample:
            buf = sample.get_buffer()
            caps = sample.get_caps()

            # Get buffer data
            success, map_info = buf.map(Gst.MapFlags.READ)
            if not success:
                return Gst.FlowReturn.ERROR

            # Get dimensions
            caps_struct = caps.get_structure(0)
            height = caps_struct.get_value('height')
            width = caps_struct.get_value('width')

            # Create numpy array
            frame = np.ndarray(
                shape=(height, width, 3),
                dtype=np.uint8,
                buffer=map_info.data
            ).copy()

            buf.unmap(map_info)

            # Store frame
            with self.frame_lock:
                self.latest_frame = frame

            return Gst.FlowReturn.OK
        return Gst.FlowReturn.ERROR

    def get_frame(self) -> Optional[np.ndarray]:
        """Get latest frame"""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    async def inference_loop(self):
        """Main inference loop - runs Hailo AI and sends results"""
        logger.info(f"[{self.camera_id}] Starting inference loop (target {self.fps_limit} FPS)")

        while self.running:
            try:
                # Check if enough time has passed
                current_time = asyncio.get_event_loop().time()
                if current_time - self.last_inference_time < self.frame_interval:
                    await asyncio.sleep(0.01)
                    continue

                self.last_inference_time = current_time

                # Get frame
                frame = self.get_frame()
                if frame is None:
                    await asyncio.sleep(0.1)
                    continue

                # Run Hailo inference
                detections, inference_time = self.detector.infer(frame)

                # Format for frontend
                result = format_detections_for_frontend(
                    detections=detections,
                    frame_shape=frame.shape[:2],
                    inference_time=inference_time,
                    total_count=self.detector.total_inferences
                )

                # Send to server
                if self.ws and self.ws.open:
                    await self.ws.send(json.dumps(result))
                    logger.debug(
                        f"[{self.camera_id}] Sent {len(detections)} detections "
                        f"(inference: {inference_time:.1f}ms)"
                    )

                # Log performance stats periodically
                if self.detector.total_inferences % 50 == 0:
                    stats = self.detector.get_performance_stats()
                    logger.info(
                        f"[{self.camera_id}] Hailo stats: "
                        f"avg={stats['avg_inference_time_ms']:.1f}ms, "
                        f"fps={stats['fps']:.1f}, "
                        f"total={stats['total_inferences']}"
                    )

            except Exception as e:
                logger.error(f"[{self.camera_id}] Inference loop error: {e}")
                await asyncio.sleep(1)

    async def websocket_handler(self):
        """Handle WebSocket connection to server"""
        retry_delay = 5

        while self.running:
            try:
                logger.info(f"[{self.camera_id}] Connecting to {self.server_url}...")
                async with websockets.connect(self.server_url) as ws:
                    self.ws = ws
                    logger.info(f"[{self.camera_id}] Connected to server")

                    # Wait for connection to close
                    await ws.wait_closed()

            except Exception as e:
                logger.error(f"[{self.camera_id}] WebSocket error: {e}")
                self.ws = None

            if self.running:
                logger.info(f"[{self.camera_id}] Reconnecting in {retry_delay}s...")
                await asyncio.sleep(retry_delay)

    async def start(self):
        """Start the client"""
        logger.info(f"[{self.camera_id}] Starting Hailo RTSP client...")
        self.running = True

        # Start GLib loop in separate thread
        self.glib_loop = GLib.MainLoop()
        self.glib_thread = threading.Thread(target=self.glib_loop.run)
        self.glib_thread.daemon = True
        self.glib_thread.start()

        # Start GStreamer pipeline
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error(f"[{self.camera_id}] Failed to start pipeline")
            return

        logger.info(f"[{self.camera_id}] Pipeline started")

        # Run WebSocket and inference loops concurrently
        await asyncio.gather(
            self.websocket_handler(),
            self.inference_loop()
        )

    def stop(self):
        """Stop the client"""
        logger.info(f"[{self.camera_id}] Stopping...")
        self.running = False

        # Stop pipeline
        if hasattr(self, 'pipeline'):
            self.pipeline.set_state(Gst.State.NULL)

        # Stop GLib loop
        if self.glib_loop and self.glib_loop.is_running():
            self.glib_loop.quit()

        if self.glib_thread:
            self.glib_thread.join(timeout=2)

        # Cleanup detector
        if hasattr(self, 'detector'):
            self.detector.cleanup()

        logger.info(f"[{self.camera_id}] Stopped")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Hailo AI Camera Client')
    parser.add_argument('--camera-id', default='camera1', help='Camera ID')
    parser.add_argument('--rtsp-url', required=True, help='RTSP stream URL')
    parser.add_argument('--server', default='ws://localhost:9200', help='Server URL')
    parser.add_argument('--model', default='/usr/share/hailo-models/yolov8s_h8l.hef', help='HEF model path')
    parser.add_argument('--fps', type=int, default=5, help='Inference FPS limit')

    args = parser.parse_args()

    # Build WebSocket URL
    ws_url = f"{args.server}/ws/{args.camera_id}/ai"

    # Create client
    client = HailoRTSPClient(
        camera_id=args.camera_id,
        rtsp_url=args.rtsp_url,
        server_url=ws_url,
        model_path=args.model,
        fps_limit=args.fps
    )

    try:
        await client.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        client.stop()


if __name__ == '__main__':
    asyncio.run(main())
