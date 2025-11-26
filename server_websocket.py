"""
Videobase Pi - WebSocket Proxy Server
FastAPI server that connects to camera WebSocket endpoints and proxies streams to clients.

Features:
- Multi-camera WebSocket connection management
- Automatic WebSocket discovery and fallback to HTTP polling
- Per-camera client connection tracking
- Frame buffering and distribution to multiple clients
- Support for both JSON and binary WebSocket messages
- CORS support for remote frontend access

Camera Configuration:
- camera1: ws://192.168.1.136/ws/example
- camera2: ws://192.168.1.110/ws/example
- camera3: ws://192.168.1.106/ws/example

Usage:
    python server_websocket.py

Default port: 9200
WebSocket endpoint: ws://localhost:9200/ws/{camera_id}
Health check: http://localhost:9200/health

Note: This server is ideal for cameras that expose WebSocket endpoints directly.
For RTSP streams, use server_multi_rtsp.py instead.
"""
import asyncio
import logging
import base64
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import websockets
import aiohttp
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Videobase Pi API - WebSocket Mode")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Camera configurations
CAMERAS = {
    "camera1": {
        "url": "ws://192.168.1.136/ws/example",
        "type": "websocket",
        "name": "Camera 1 (136)"
    },
    "camera2": {
        "url": "ws://192.168.1.110/ws/example",
        "type": "websocket",
        "name": "Camera 2 (110)"
    },
    "camera3": {
        "url": "ws://192.168.1.106/ws/example",
        "type": "websocket",
        "name": "Camera 3 (106)"
    }
}

# Store frames and connection state for each camera
camera_states = {
    camera_id: {
        "latest_frame": None,
        "frame_count": 0,
        "connected": False,
        "ws_connection": None
    }
    for camera_id in CAMERAS.keys()
}

# Store connected clients per camera
connected_clients = {camera_id: set() for camera_id in CAMERAS.keys()}

async def connect_to_websocket_camera(camera_id: str, ws_url: str):
    """Connect to a WebSocket camera and receive frames"""
    state = camera_states[camera_id]

    while True:
        try:
            logger.info(f"[{camera_id}] Connecting to {ws_url}...")
            async with websockets.connect(ws_url) as websocket:
                state["ws_connection"] = websocket
                state["connected"] = True
                logger.info(f"[{camera_id}] Connected!")

                async for message in websocket:
                    state["frame_count"] += 1

                    # Log first message to see format
                    if state["frame_count"] == 1:
                        logger.info(f"[{camera_id}] First message type: {type(message)}")
                        if isinstance(message, str):
                            logger.info(f"[{camera_id}] First 100 chars: {message[:100]}")
                        else:
                            logger.info(f"[{camera_id}] Message length: {len(message)} bytes")

                    # Try to parse as JSON first
                    try:
                        data = json.loads(message)
                        if isinstance(data, dict):
                            # Extract the actual image data
                            image_data = data.get("payload") or data.get("image") or data.get("data")

                            state["latest_frame"] = {
                                "type": "frame",
                                "camera_id": camera_id,
                                "data": image_data if image_data else str(data),
                                "timestamp": datetime.now().isoformat(),
                                "frame_count": state["frame_count"]
                            }
                        else:
                            state["latest_frame"] = {
                                "type": "frame",
                                "camera_id": camera_id,
                                "data": data,
                                "timestamp": datetime.now().isoformat(),
                                "frame_count": state["frame_count"]
                            }
                    except json.JSONDecodeError:
                        # If not JSON, assume it's binary image data
                        if isinstance(message, bytes):
                            # Convert binary to base64
                            b64_data = base64.b64encode(message).decode('utf-8')
                            state["latest_frame"] = {
                                "type": "frame",
                                "camera_id": camera_id,
                                "data": b64_data,
                                "timestamp": datetime.now().isoformat(),
                                "frame_count": state["frame_count"]
                            }
                        else:
                            # Assume it's already base64 string
                            state["latest_frame"] = {
                                "type": "frame",
                                "camera_id": camera_id,
                                "data": message,
                                "timestamp": datetime.now().isoformat(),
                                "frame_count": state["frame_count"]
                            }

                    if state["frame_count"] % 30 == 0:
                        logger.info(f"[{camera_id}] Frame {state['frame_count']}")

        except Exception as e:
            logger.error(f"[{camera_id}] Connection error: {e}")
            state["ws_connection"] = None
            state["connected"] = False
            await asyncio.sleep(5)

async def connect_to_http_camera(camera_id: str, http_url: str):
    """Poll HTTP camera for frames (placeholder - needs implementation based on camera type)"""
    import aiohttp
    state = camera_states[camera_id]

    # Try common endpoints
    endpoints = [
        "/ws/example",  # WebSocket endpoint
        "/stream",      # MJPEG stream
        "/snapshot",    # Snapshot endpoint
        "/image",       # Image endpoint
    ]

    while True:
        try:
            # First, try WebSocket endpoints
            for endpoint in ["/ws/example"]:
                try:
                    ws_url = http_url.replace("http://", "ws://").rstrip("/") + endpoint
                    logger.info(f"[{camera_id}] Trying WebSocket at {ws_url}...")
                    await connect_to_websocket_camera(camera_id, ws_url)
                    return  # If successful, this will run indefinitely
                except Exception as e:
                    logger.debug(f"[{camera_id}] WebSocket attempt failed: {e}")

            # If WebSocket fails, try HTTP snapshot polling
            logger.info(f"[{camera_id}] Falling back to HTTP polling...")
            async with aiohttp.ClientSession() as session:
                while True:
                    for endpoint in ["/snapshot", "/image", "/"]:
                        try:
                            url = http_url.rstrip("/") + endpoint
                            async with session.get(url, timeout=5) as response:
                                if response.status == 200:
                                    data = await response.read()
                                    # Try to get base64
                                    import base64
                                    b64_data = base64.b64encode(data).decode('utf-8')

                                    state["frame_count"] += 1
                                    state["connected"] = True
                                    state["latest_frame"] = {
                                        "type": "frame",
                                        "camera_id": camera_id,
                                        "data": b64_data,
                                        "timestamp": datetime.now().isoformat(),
                                        "frame_count": state["frame_count"]
                                    }

                                    if state["frame_count"] % 30 == 0:
                                        logger.info(f"[{camera_id}] Frame {state['frame_count']}")

                                    await asyncio.sleep(0.033)  # ~30 FPS
                                    break
                        except Exception as e:
                            logger.debug(f"[{camera_id}] HTTP endpoint {endpoint} failed: {e}")
                            continue

                    await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"[{camera_id}] Error: {e}")
            state["connected"] = False
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    """Start all camera connections on startup"""
    for camera_id, config in CAMERAS.items():
        if config["type"] == "websocket":
            asyncio.create_task(connect_to_websocket_camera(camera_id, config["url"]))
        elif config["type"] == "http":
            asyncio.create_task(connect_to_http_camera(camera_id, config["url"]))

@app.get("/")
async def root():
    return {
        "message": "Videobase Pi API - Multi-Camera WebSocket Mode",
        "version": "4.0",
        "cameras": {
            cam_id: {
                "name": config["name"],
                "url": config["url"],
                "connected": camera_states[cam_id]["connected"],
                "frame_count": camera_states[cam_id]["frame_count"]
            }
            for cam_id, config in CAMERAS.items()
        },
        "endpoints": {
            "websocket": "/ws/{camera_id}",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "cameras": {
            cam_id: {
                "connected": state["connected"],
                "frame_count": state["frame_count"],
                "clients": len(connected_clients[cam_id])
            }
            for cam_id, state in camera_states.items()
        }
    }

@app.websocket("/ws/{camera_id}")
async def websocket_endpoint(websocket: WebSocket, camera_id: str):
    """WebSocket endpoint for browser clients - per camera"""
    if camera_id not in CAMERAS:
        await websocket.close(code=1008, reason=f"Unknown camera: {camera_id}")
        return

    await websocket.accept()
    connected_clients[camera_id].add(websocket)
    logger.info(f"[{camera_id}] Client connected. Total clients: {len(connected_clients[camera_id])}")

    try:
        state = camera_states[camera_id]
        while True:
            if state["latest_frame"]:
                await websocket.send_json(state["latest_frame"])
            await asyncio.sleep(0.033)  # ~30 FPS

    except WebSocketDisconnect:
        logger.info(f"[{camera_id}] Client disconnected")
    except Exception as e:
        logger.error(f"[{camera_id}] WebSocket error: {e}")
    finally:
        connected_clients[camera_id].discard(websocket)
        logger.info(f"[{camera_id}] Client removed. Total: {len(connected_clients[camera_id])}")

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
