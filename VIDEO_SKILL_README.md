# Video Skill Service for OpenClaw

A comprehensive video processing service that integrates with Hailo AI inference for real-time object detection on RTSP camera streams.

## Features

### 1. Live Video Streaming
- **WebSocket endpoint**: Real-time video streaming with Hailo AI detection overlays
- **Multiple cameras**: Support for all configured RTSP cameras
- **Configurable FPS**: Adjustable frame rate for bandwidth optimization

### 2. Frame Capture & Analysis
- **On-demand capture**: Grab individual frames from any camera
- **AI inference**: Run Hailo object detection on captured frames
- **Auto-save**: Optionally save captured frames to disk

### 3. Video Recording
- **Start/stop recording**: Record video clips from any camera
- **Timed recording**: Automatic stop after specified duration
- **Detection overlay**: Optional AI detection bounding boxes in recordings
- **Recording history**: Query past recordings with metadata

### 4. Detection History
- **Persistent storage**: SQLite database for all detections
- **Advanced querying**: Filter by camera, class, time range, confidence
- **Statistics**: Aggregated detection counts and trends
- **Thumbnail snapshots**: Optional frame snapshots with detections

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Video Skill Service                      │
│                         (Port 8888)                          │
├──────────────────┬──────────────────┬───────────────────────┤
│   REST API       │   WebSocket      │   Background Tasks    │
│   - /cameras     │   - /ws/stream   │   - Recording loops   │
│   - /capture     │                  │   - Detection saving  │
│   - /record      │                  │                       │
│   - /detections  │                  │                       │
└────────┬─────────┴──────────────────┴───────────────────────┘
         │
         ├──> Hailo Inference (hailo_inference.py)
         ├──> RTSP Cameras (via OpenCV)
         └──> SQLite Database (detections.db)
```

## Installation

### Prerequisites

```bash
# Python dependencies
pip install fastapi uvicorn websockets opencv-python numpy pydantic

# Hailo support (already installed if using hailo_inference.py)
# sudo apt install hailo-all
```

### Start the Service

```bash
# Default port 8888
./start-video-skill.sh

# Custom port
./start-video-skill.sh 9000
```

## API Documentation

### REST Endpoints

#### Health Check
```bash
GET /health

Response:
{
  "status": "ok",
  "hailo_available": true,
  "hailo_initialized": true,
  "cameras": 3,
  "active_streams": 1,
  "active_recordings": 0
}
```

#### List Cameras
```bash
GET /cameras

Response:
{
  "cameras": [
    {
      "id": "camera1",
      "name": "Camera 1 (136)",
      "rtsp_url": "rtsp://***:***@192.168.1.136:554/live",
      "enabled": true,
      "connected": true
    }
  ]
}
```

#### Capture Frame
```bash
POST /cameras/{camera_id}/capture
Content-Type: application/json

{
  "save_frame": true,
  "run_inference": true
}

Response:
{
  "camera_id": "camera1",
  "timestamp": 1708367890.5,
  "frame": "base64_encoded_jpeg...",
  "detections": [
    {
      "class_name": "person",
      "confidence": 0.92,
      "bbox": [100, 50, 200, 400]
    }
  ],
  "file_path": "/home/admin/videobase-pi/recordings/camera1_capture_20240219_143130.jpg"
}
```

#### Start Recording
```bash
POST /cameras/{camera_id}/record/start
Content-Type: application/json

{
  "duration_seconds": 60,  # null for continuous
  "include_detections": true
}

Response:
{
  "recording_id": 42,
  "camera_id": "camera1",
  "status": "recording",
  "duration_seconds": 60,
  "include_detections": true
}
```

#### Stop Recording
```bash
POST /cameras/{camera_id}/record/stop

Response:
{
  "recording_id": 42,
  "camera_id": "camera1",
  "status": "stopped"
}
```

#### List Recordings
```bash
GET /recordings?camera_id=camera1&limit=50

Response:
{
  "recordings": [
    {
      "id": 42,
      "camera_id": "camera1",
      "start_time": 1708367800.0,
      "end_time": 1708367860.0,
      "file_path": "/home/admin/videobase-pi/recordings/camera1_20240219_143000.mp4",
      "file_size": 15728640,
      "status": "completed",
      "detection_count": 245
    }
  ],
  "count": 1
}
```

#### Query Detections
```bash
POST /detections/query
Content-Type: application/json

{
  "camera_id": "camera1",
  "class_name": "person",
  "start_time": 1708364290.0,
  "end_time": 1708367890.0,
  "min_confidence": 0.5,
  "limit": 100
}

Response:
{
  "detections": [
    {
      "camera_id": "camera1",
      "timestamp": 1708367890.5,
      "class_name": "person",
      "confidence": 0.92,
      "bbox": [100, 50, 200, 400],
      "frame_snapshot": null
    }
  ],
  "count": 1
}
```

#### Detection Statistics
```bash
GET /detections/stats?camera_id=camera1&hours=24

Response:
{
  "total_detections": 1523,
  "class_counts": {
    "person": 842,
    "car": 421,
    "dog": 185,
    "bicycle": 75
  },
  "time_window_hours": 24
}
```

### WebSocket Endpoints

#### Live Stream with Detections
```javascript
// Connect to camera stream
const ws = new WebSocket('ws://localhost:8888/ws/camera1/stream?detections=true');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'frame') {
    // data.frame: base64 JPEG with detection overlays
    // data.detections: array of detection objects
    // data.timestamp: frame timestamp

    const img = document.getElementById('video');
    img.src = 'data:image/jpeg;base64,' + data.frame;

    console.log(`Detections: ${data.detections.length}`);
  }
};
```

## Integration with OpenClaw

### Option 1: Direct Backend URL

Update OpenClaw's environment to proxy to the video skill service:

```bash
# In openclaw-cloudflare/.dev.vars or production secrets
OPENCLAW_BACKEND_URL=http://localhost:8888
```

Then OpenClaw will automatically proxy all requests to the video skill service.

### Option 2: Separate Endpoint

Keep OpenClaw on port 18789 and video skill on 8888, then use nginx or similar to route:

```nginx
# nginx config
location /video/ {
  proxy_pass http://localhost:8888/;
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
}

location / {
  proxy_pass http://localhost:18789;
}
```

### Option 3: Cloudflare Tunnel

Expose the video skill service via cloudflared:

```bash
cloudflared tunnel --url http://localhost:8888
```

Then update OpenClaw's `OPENCLAW_BACKEND_URL` to the tunnel URL.

## Testing

### Run Test Suite
```bash
# Make sure service is running first
python3 test_video_skill.py

# Run specific test
python3 test_video_skill.py capture_frame
python3 test_video_skill.py websocket_stream
```

### Manual Testing with curl

```bash
# Health check
curl http://localhost:8888/health

# List cameras
curl http://localhost:8888/cameras

# Capture frame
curl -X POST http://localhost:8888/cameras/camera1/capture \
  -H "Content-Type: application/json" \
  -d '{"save_frame": true, "run_inference": true}'

# Start recording (60 seconds)
curl -X POST http://localhost:8888/cameras/camera1/record/start \
  -H "Content-Type: application/json" \
  -d '{"duration_seconds": 60, "include_detections": true}'

# Stop recording
curl -X POST http://localhost:8888/cameras/camera1/record/stop

# Query detections
curl -X POST http://localhost:8888/detections/query \
  -H "Content-Type: application/json" \
  -d '{"camera_id": "camera1", "limit": 10}'
```

### WebSocket Testing with websocat

```bash
# Install websocat
# cargo install websocat

# Connect to stream
websocat ws://localhost:8888/ws/camera1/stream?detections=true
```

## Database Schema

### Detections Table
```sql
CREATE TABLE detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    class_name TEXT NOT NULL,
    confidence REAL NOT NULL,
    bbox_x REAL NOT NULL,
    bbox_y REAL NOT NULL,
    bbox_w REAL NOT NULL,
    bbox_h REAL NOT NULL,
    frame_snapshot TEXT  -- base64 thumbnail (optional)
);
```

### Recordings Table
```sql
CREATE TABLE recordings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id TEXT NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    status TEXT DEFAULT 'recording',
    detection_count INTEGER DEFAULT 0
);
```

## Performance Considerations

### Frame Rate
- Default: ~10 FPS for WebSocket streaming
- Adjustable via `asyncio.sleep()` in streaming loop
- Higher FPS = more CPU/bandwidth usage

### Hailo Inference
- Inference time: ~50-100ms per frame on Hailo-8L
- Can process ~10-20 FPS in real-time
- Bottleneck is usually RTSP stream latency

### Storage
- Detections DB grows ~1KB per detection
- 10K detections/day ≈ 10MB/day ≈ 300MB/month
- Recordings: depends on resolution and duration
  - 640x480 @ 10 FPS ≈ 5-10MB/min
  - 1920x1080 @ 10 FPS ≈ 20-30MB/min

### Optimization Tips
1. **Reduce frame rate** for non-critical cameras
2. **Skip inference** on every Nth frame if detection rate is slow
3. **Cleanup old data** with periodic DB vacuuming
4. **Use H.264 hardware encoding** for recordings (if available)

## Troubleshooting

### "Hailo not available"
```bash
# Check Hailo device
ls -l /dev/hailo0

# Check Hailo SDK
python3 -c "import hailo_platform; print('OK')"

# Run Hailo test
python3 test_hailo.py
```

### "Cannot connect to camera"
```bash
# Test RTSP stream with ffplay
ffplay rtsp://admin:admin@192.168.1.136:554/live

# Check camera credentials in video_skill_service.py
# Update CAMERAS dict if needed
```

### "WebSocket disconnects"
- Check firewall rules for port 8888
- Verify network stability between Pi and cameras
- Increase buffer sizes in OpenCV capture

### "Recording fails"
```bash
# Check disk space
df -h /home/admin/videobase-pi/recordings

# Check write permissions
ls -ld /home/admin/videobase-pi/recordings

# Verify codec support
python3 -c "import cv2; print(cv2.VideoWriter_fourcc(*'mp4v'))"
```

## API Client Examples

### Python Client
```python
import requests

# List cameras
cameras = requests.get("http://localhost:8888/cameras").json()

# Capture frame from first camera
camera_id = cameras['cameras'][0]['id']
response = requests.post(
    f"http://localhost:8888/cameras/{camera_id}/capture",
    json={"run_inference": True, "save_frame": False}
)

detections = response.json()['detections']
print(f"Found {len(detections)} objects:")
for det in detections:
    print(f"  - {det['class_name']}: {det['confidence']:.2f}")
```

### JavaScript Client (Browser)
```javascript
// Fetch camera list
const cameras = await fetch('http://localhost:8888/cameras')
  .then(r => r.json());

// Start WebSocket stream
const ws = new WebSocket(`ws://localhost:8888/ws/${cameras.cameras[0].id}/stream?detections=true`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  document.getElementById('video').src =
    'data:image/jpeg;base64,' + data.frame;
};
```

## Future Enhancements

- [ ] Motion detection triggers for recording
- [ ] Alert webhooks for specific object classes
- [ ] Multi-camera mosaic streaming
- [ ] PTZ camera control
- [ ] Face recognition integration
- [ ] License plate recognition
- [ ] Cloud storage integration (S3, Google Drive)
- [ ] Advanced analytics (heatmaps, tracking)

## License

MIT License - Free to use and modify

## Support

For issues or questions:
1. Check logs: `tail -f /home/admin/videobase-pi/video_skill.log`
2. Test individual components: `python3 test_video_skill.py <test_name>`
3. Verify Hailo setup: `python3 test_hailo.py`

---

**Built with ❤️ for OpenClaw**
