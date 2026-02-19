"""
Video Skill Service for OpenClaw
Provides REST API and WebSocket endpoints for video streaming, capture, recording, and detection queries
Integrates with Hailo inference system for real-time object detection
"""
import asyncio
import base64
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

# Import existing Hailo inference
try:
    from hailo_inference import HailoDetector
    HAILO_AVAILABLE = True
except ImportError:
    HAILO_AVAILABLE = False
    logging.warning("Hailo inference not available - running without AI detection")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
VIDEO_STORAGE_PATH = Path("/home/admin/videobase-pi/recordings")
VIDEO_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

DB_PATH = Path("/home/admin/videobase-pi/detections.db")

# Camera configurations (from server_multi_rtsp.py)
CAMERAS = {
    "camera1": {
        "rtsp_url": "rtsp://admin:admin@192.168.1.136:554/live",
        "name": "Camera 1 (136)",
        "enabled": True
    },
    "camera2": {
        "rtsp_url": "rtsp://admin:admin@192.168.1.110:554/live",
        "name": "Camera 2 (110)",
        "enabled": True
    },
    "camera3": {
        "rtsp_url": "rtsp://admin:admin@192.168.1.106:554/live",
        "name": "Camera 3 (106)",
        "enabled": True
    }
}


# ============================================================================
# Database Schema
# ============================================================================

def init_database():
    """Initialize SQLite database for detection history"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id TEXT NOT NULL,
            timestamp REAL NOT NULL,
            class_name TEXT NOT NULL,
            confidence REAL NOT NULL,
            bbox_x REAL NOT NULL,
            bbox_y REAL NOT NULL,
            bbox_w REAL NOT NULL,
            bbox_h REAL NOT NULL,
            frame_snapshot TEXT,
            INDEX idx_camera_timestamp (camera_id, timestamp),
            INDEX idx_class (class_name),
            INDEX idx_timestamp (timestamp)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recordings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id TEXT NOT NULL,
            start_time REAL NOT NULL,
            end_time REAL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            status TEXT DEFAULT 'recording',
            detection_count INTEGER DEFAULT 0,
            INDEX idx_camera_time (camera_id, start_time)
        )
    """)

    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")


# ============================================================================
# Data Models
# ============================================================================

class Detection(BaseModel):
    camera_id: str
    timestamp: float
    class_name: str
    confidence: float
    bbox: List[float]  # [x, y, w, h]
    frame_snapshot: Optional[str] = None  # base64 encoded thumbnail


class Recording(BaseModel):
    id: int
    camera_id: str
    start_time: float
    end_time: Optional[float]
    file_path: str
    file_size: Optional[int]
    status: str
    detection_count: int


class CaptureRequest(BaseModel):
    save_frame: bool = False
    run_inference: bool = True


class RecordingRequest(BaseModel):
    duration_seconds: Optional[int] = None  # None = record until stopped
    include_detections: bool = True


class DetectionQuery(BaseModel):
    camera_id: Optional[str] = None
    class_name: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    min_confidence: float = 0.5
    limit: int = 100


# ============================================================================
# Video Capture & Processing
# ============================================================================

class CameraManager:
    """Manages camera connections and frame capture"""

    def __init__(self):
        self.caps: Dict[str, cv2.VideoCapture] = {}
        self.last_frames: Dict[str, np.ndarray] = {}
        self.hailo_detector: Optional[HailoDetector] = None
        self.recording_tasks: Dict[str, asyncio.Task] = {}

        # Initialize Hailo detector if available
        if HAILO_AVAILABLE:
            try:
                self.hailo_detector = HailoDetector(
                    hef_path="/usr/share/hailo-models/yolov8s_h8l.hef",
                    confidence_threshold=0.5
                )
                logger.info("Hailo detector initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Hailo detector: {e}")
                self.hailo_detector = None

    def connect_camera(self, camera_id: str) -> bool:
        """Connect to a camera's RTSP stream"""
        if camera_id not in CAMERAS:
            return False

        if camera_id in self.caps:
            return True

        camera_info = CAMERAS[camera_id]
        rtsp_url = camera_info["rtsp_url"]

        logger.info(f"Connecting to {camera_id}: {rtsp_url}")
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

        if not cap.isOpened():
            logger.error(f"Failed to open {camera_id}")
            return False

        self.caps[camera_id] = cap
        logger.info(f"Successfully connected to {camera_id}")
        return True

    def capture_frame(self, camera_id: str) -> Optional[np.ndarray]:
        """Capture a single frame from camera"""
        if not self.connect_camera(camera_id):
            return None

        cap = self.caps[camera_id]
        ret, frame = cap.read()

        if ret:
            self.last_frames[camera_id] = frame
            return frame

        logger.warning(f"Failed to capture frame from {camera_id}")
        return None

    def run_inference(self, frame: np.ndarray) -> List[Dict]:
        """Run Hailo inference on a frame"""
        if self.hailo_detector is None:
            return []

        try:
            detections = self.hailo_detector.detect(frame)
            return detections
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return []

    def draw_detections(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """Draw bounding boxes and labels on frame"""
        frame_copy = frame.copy()

        for det in detections:
            x, y, w, h = det['bbox']
            x, y, w, h = int(x), int(y), int(w), int(h)

            # Draw box
            cv2.rectangle(frame_copy, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # Draw label
            label = f"{det['class_name']} {det['confidence']:.2f}"
            cv2.putText(frame_copy, label, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        return frame_copy

    def encode_frame_base64(self, frame: np.ndarray, quality: int = 80) -> str:
        """Encode frame as base64 JPEG"""
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return base64.b64encode(buffer).decode('utf-8')

    def cleanup(self):
        """Release all camera connections"""
        for camera_id, cap in self.caps.items():
            cap.release()
            logger.info(f"Released {camera_id}")
        self.caps.clear()


# ============================================================================
# Detection History Manager
# ============================================================================

class DetectionHistoryManager:
    """Manages detection storage and queries"""

    def __init__(self):
        self.db_path = str(DB_PATH)

    def save_detection(self, detection: Detection):
        """Save a detection to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO detections
            (camera_id, timestamp, class_name, confidence, bbox_x, bbox_y, bbox_w, bbox_h, frame_snapshot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            detection.camera_id,
            detection.timestamp,
            detection.class_name,
            detection.confidence,
            detection.bbox[0],
            detection.bbox[1],
            detection.bbox[2],
            detection.bbox[3],
            detection.frame_snapshot
        ))

        conn.commit()
        conn.close()

    def query_detections(self, query: DetectionQuery) -> List[Detection]:
        """Query detections from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        conditions = ["confidence >= ?"]
        params = [query.min_confidence]

        if query.camera_id:
            conditions.append("camera_id = ?")
            params.append(query.camera_id)

        if query.class_name:
            conditions.append("class_name = ?")
            params.append(query.class_name)

        if query.start_time:
            conditions.append("timestamp >= ?")
            params.append(query.start_time)

        if query.end_time:
            conditions.append("timestamp <= ?")
            params.append(query.end_time)

        where_clause = " AND ".join(conditions)
        params.append(query.limit)

        cursor.execute(f"""
            SELECT camera_id, timestamp, class_name, confidence,
                   bbox_x, bbox_y, bbox_w, bbox_h, frame_snapshot
            FROM detections
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """, params)

        detections = []
        for row in cursor.fetchall():
            detections.append(Detection(
                camera_id=row[0],
                timestamp=row[1],
                class_name=row[2],
                confidence=row[3],
                bbox=[row[4], row[5], row[6], row[7]],
                frame_snapshot=row[8]
            ))

        conn.close()
        return detections

    def get_detection_stats(self, camera_id: Optional[str] = None, hours: int = 24) -> Dict:
        """Get detection statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_time = time.time() - (hours * 3600)

        # Total detections
        if camera_id:
            cursor.execute("""
                SELECT COUNT(*), class_name, COUNT(*)
                FROM detections
                WHERE camera_id = ? AND timestamp >= ?
                GROUP BY class_name
                ORDER BY COUNT(*) DESC
            """, (camera_id, cutoff_time))
        else:
            cursor.execute("""
                SELECT COUNT(*), class_name, COUNT(*)
                FROM detections
                WHERE timestamp >= ?
                GROUP BY class_name
                ORDER BY COUNT(*) DESC
            """, (cutoff_time,))

        class_counts = {}
        total = 0
        for row in cursor.fetchall():
            class_counts[row[1]] = row[2]
            total += row[2]

        conn.close()

        return {
            "total_detections": total,
            "class_counts": class_counts,
            "time_window_hours": hours
        }


# ============================================================================
# Recording Manager
# ============================================================================

class RecordingManager:
    """Manages video recording tasks"""

    def __init__(self, camera_manager: CameraManager):
        self.camera_manager = camera_manager
        self.active_recordings: Dict[str, Dict] = {}
        self.db_path = str(DB_PATH)

    async def start_recording(self, camera_id: str, request: RecordingRequest) -> int:
        """Start recording from a camera"""
        if camera_id in self.active_recordings:
            raise HTTPException(400, "Recording already in progress for this camera")

        # Generate file path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = VIDEO_STORAGE_PATH / f"{camera_id}_{timestamp}.mp4"

        # Insert recording record
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO recordings (camera_id, start_time, file_path, status)
            VALUES (?, ?, ?, 'recording')
        """, (camera_id, time.time(), str(file_path)))
        recording_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Start recording task
        self.active_recordings[camera_id] = {
            "id": recording_id,
            "file_path": str(file_path),
            "start_time": time.time(),
            "duration": request.duration_seconds,
            "include_detections": request.include_detections,
            "writer": None,
            "detection_count": 0
        }

        task = asyncio.create_task(self._recording_loop(camera_id))
        self.camera_manager.recording_tasks[camera_id] = task

        logger.info(f"Started recording {recording_id} for {camera_id}")
        return recording_id

    async def stop_recording(self, camera_id: str) -> Optional[int]:
        """Stop recording for a camera"""
        if camera_id not in self.active_recordings:
            return None

        recording = self.active_recordings[camera_id]
        recording_id = recording["id"]

        # Cancel recording task
        if camera_id in self.camera_manager.recording_tasks:
            self.camera_manager.recording_tasks[camera_id].cancel()
            try:
                await self.camera_manager.recording_tasks[camera_id]
            except asyncio.CancelledError:
                pass
            del self.camera_manager.recording_tasks[camera_id]

        # Release video writer
        if recording["writer"]:
            recording["writer"].release()

        # Update database
        file_size = Path(recording["file_path"]).stat().st_size if Path(recording["file_path"]).exists() else 0
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE recordings
            SET end_time = ?, file_size = ?, status = 'completed', detection_count = ?
            WHERE id = ?
        """, (time.time(), file_size, recording["detection_count"], recording_id))
        conn.commit()
        conn.close()

        del self.active_recordings[camera_id]
        logger.info(f"Stopped recording {recording_id} for {camera_id}")

        return recording_id

    async def _recording_loop(self, camera_id: str):
        """Background task for recording video"""
        recording = self.active_recordings[camera_id]
        start_time = recording["start_time"]
        duration = recording["duration"]

        # Initialize video writer
        frame = self.camera_manager.capture_frame(camera_id)
        if frame is None:
            logger.error(f"Cannot start recording - no frame from {camera_id}")
            return

        height, width = frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(
            recording["file_path"],
            fourcc,
            10.0,  # FPS
            (width, height)
        )
        recording["writer"] = writer

        try:
            while True:
                # Check duration limit
                if duration and (time.time() - start_time) >= duration:
                    break

                # Capture frame
                frame = self.camera_manager.capture_frame(camera_id)
                if frame is None:
                    await asyncio.sleep(0.1)
                    continue

                # Run inference if requested
                if recording["include_detections"]:
                    detections = self.camera_manager.run_inference(frame)
                    if detections:
                        recording["detection_count"] += len(detections)
                        frame = self.camera_manager.draw_detections(frame, detections)

                # Write frame
                writer.write(frame)

                await asyncio.sleep(0.1)  # ~10 FPS

        except asyncio.CancelledError:
            logger.info(f"Recording cancelled for {camera_id}")
        finally:
            writer.release()

    def get_recordings(self, camera_id: Optional[str] = None, limit: int = 50) -> List[Recording]:
        """Get recording history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if camera_id:
            cursor.execute("""
                SELECT id, camera_id, start_time, end_time, file_path, file_size, status, detection_count
                FROM recordings
                WHERE camera_id = ?
                ORDER BY start_time DESC
                LIMIT ?
            """, (camera_id, limit))
        else:
            cursor.execute("""
                SELECT id, camera_id, start_time, end_time, file_path, file_size, status, detection_count
                FROM recordings
                ORDER BY start_time DESC
                LIMIT ?
            """, (limit,))

        recordings = []
        for row in cursor.fetchall():
            recordings.append(Recording(
                id=row[0],
                camera_id=row[1],
                start_time=row[2],
                end_time=row[3],
                file_path=row[4],
                file_size=row[5],
                status=row[6],
                detection_count=row[7]
            ))

        conn.close()
        return recordings


# ============================================================================
# WebSocket Streaming
# ============================================================================

class StreamManager:
    """Manages WebSocket connections for live streaming"""

    def __init__(self, camera_manager: CameraManager, history_manager: DetectionHistoryManager):
        self.camera_manager = camera_manager
        self.history_manager = history_manager
        self.active_streams: Dict[str, Set[WebSocket]] = {}

    async def stream_camera(self, websocket: WebSocket, camera_id: str, include_detections: bool = True):
        """Stream camera feed with detections over WebSocket"""
        if camera_id not in self.active_streams:
            self.active_streams[camera_id] = set()

        self.active_streams[camera_id].add(websocket)

        try:
            while True:
                # Capture frame
                frame = self.camera_manager.capture_frame(camera_id)
                if frame is None:
                    await asyncio.sleep(0.1)
                    continue

                detections = []
                if include_detections:
                    detections = self.camera_manager.run_inference(frame)

                    # Save detections to history
                    for det in detections:
                        detection = Detection(
                            camera_id=camera_id,
                            timestamp=time.time(),
                            class_name=det['class_name'],
                            confidence=det['confidence'],
                            bbox=det['bbox']
                        )
                        self.history_manager.save_detection(detection)

                    # Draw detections on frame
                    frame = self.camera_manager.draw_detections(frame, detections)

                # Encode frame
                frame_base64 = self.camera_manager.encode_frame_base64(frame, quality=70)

                # Send over WebSocket
                await websocket.send_json({
                    "type": "frame",
                    "camera_id": camera_id,
                    "timestamp": time.time(),
                    "frame": frame_base64,
                    "detections": detections
                })

                await asyncio.sleep(0.1)  # ~10 FPS

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for {camera_id}")
        finally:
            self.active_streams[camera_id].discard(websocket)
            if not self.active_streams[camera_id]:
                del self.active_streams[camera_id]


# ============================================================================
# FastAPI Application
# ============================================================================

# Global managers
camera_manager = CameraManager()
history_manager = DetectionHistoryManager()
recording_manager = RecordingManager(camera_manager)
stream_manager = StreamManager(camera_manager, history_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Video Skill Service")
    init_database()

    yield

    # Shutdown
    logger.info("Shutting down Video Skill Service")
    camera_manager.cleanup()


app = FastAPI(
    title="Video Skill Service",
    description="Video streaming, capture, recording, and AI detection service for OpenClaw",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REST API Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "hailo_available": HAILO_AVAILABLE,
        "hailo_initialized": camera_manager.hailo_detector is not None,
        "cameras": len(CAMERAS),
        "active_streams": len(stream_manager.active_streams),
        "active_recordings": len(recording_manager.active_recordings)
    }


@app.get("/cameras")
async def list_cameras():
    """List all available cameras"""
    cameras = []
    for camera_id, info in CAMERAS.items():
        cameras.append({
            "id": camera_id,
            "name": info["name"],
            "rtsp_url": info["rtsp_url"].replace("admin:admin@", "***:***@"),  # Hide credentials
            "enabled": info["enabled"],
            "connected": camera_id in camera_manager.caps
        })
    return {"cameras": cameras}


@app.post("/cameras/{camera_id}/capture")
async def capture_frame_endpoint(camera_id: str, request: CaptureRequest):
    """Capture a single frame and optionally run inference"""
    if camera_id not in CAMERAS:
        raise HTTPException(404, f"Camera {camera_id} not found")

    frame = camera_manager.capture_frame(camera_id)
    if frame is None:
        raise HTTPException(500, f"Failed to capture frame from {camera_id}")

    detections = []
    if request.run_inference:
        detections = camera_manager.run_inference(frame)

        # Save detections to history
        for det in detections:
            detection = Detection(
                camera_id=camera_id,
                timestamp=time.time(),
                class_name=det['class_name'],
                confidence=det['confidence'],
                bbox=det['bbox']
            )
            history_manager.save_detection(detection)

        # Draw detections on frame
        frame = camera_manager.draw_detections(frame, detections)

    # Encode frame
    frame_base64 = camera_manager.encode_frame_base64(frame)

    # Optionally save frame
    file_path = None
    if request.save_frame:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = VIDEO_STORAGE_PATH / f"{camera_id}_capture_{timestamp}.jpg"
        cv2.imwrite(str(file_path), frame)

    return {
        "camera_id": camera_id,
        "timestamp": time.time(),
        "frame": frame_base64,
        "detections": detections,
        "file_path": str(file_path) if file_path else None
    }


@app.post("/cameras/{camera_id}/record/start")
async def start_recording_endpoint(camera_id: str, request: RecordingRequest):
    """Start recording video from a camera"""
    if camera_id not in CAMERAS:
        raise HTTPException(404, f"Camera {camera_id} not found")

    recording_id = await recording_manager.start_recording(camera_id, request)

    return {
        "recording_id": recording_id,
        "camera_id": camera_id,
        "status": "recording",
        "duration_seconds": request.duration_seconds,
        "include_detections": request.include_detections
    }


@app.post("/cameras/{camera_id}/record/stop")
async def stop_recording_endpoint(camera_id: str):
    """Stop recording video from a camera"""
    if camera_id not in CAMERAS:
        raise HTTPException(404, f"Camera {camera_id} not found")

    recording_id = await recording_manager.stop_recording(camera_id)

    if recording_id is None:
        raise HTTPException(404, f"No active recording for {camera_id}")

    return {
        "recording_id": recording_id,
        "camera_id": camera_id,
        "status": "stopped"
    }


@app.get("/recordings")
async def list_recordings(camera_id: Optional[str] = None, limit: int = 50):
    """Get recording history"""
    recordings = recording_manager.get_recordings(camera_id, limit)
    return {
        "recordings": [r.dict() for r in recordings],
        "count": len(recordings)
    }


@app.post("/detections/query")
async def query_detections_endpoint(query: DetectionQuery):
    """Query detection history"""
    detections = history_manager.query_detections(query)
    return {
        "detections": [d.dict() for d in detections],
        "count": len(detections)
    }


@app.get("/detections/stats")
async def get_detection_stats(camera_id: Optional[str] = None, hours: int = 24):
    """Get detection statistics"""
    stats = history_manager.get_detection_stats(camera_id, hours)
    return stats


# ============================================================================
# WebSocket Endpoints
# ============================================================================

@app.websocket("/ws/{camera_id}/stream")
async def websocket_stream(websocket: WebSocket, camera_id: str, detections: bool = True):
    """WebSocket endpoint for live camera streaming with detections"""
    if camera_id not in CAMERAS:
        await websocket.close(code=1008, reason=f"Camera {camera_id} not found")
        return

    await websocket.accept()
    logger.info(f"WebSocket stream started for {camera_id} (detections={detections})")

    try:
        await stream_manager.stream_camera(websocket, camera_id, include_detections=detections)
    except Exception as e:
        logger.error(f"WebSocket stream error for {camera_id}: {e}")
    finally:
        logger.info(f"WebSocket stream ended for {camera_id}")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8888

    logger.info(f"Starting Video Skill Service on port {port}")
    logger.info(f"Hailo support: {HAILO_AVAILABLE}")
    logger.info(f"Cameras configured: {len(CAMERAS)}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
