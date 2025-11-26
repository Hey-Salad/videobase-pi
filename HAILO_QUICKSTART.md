# Hailo AI Quick Start Guide

Get your Hailo-8L AI accelerator running in 3 steps!

## Prerequisites

✅ Raspberry Pi 5 with Hailo-8L module
✅ Hailo Platform SDK installed
✅ Backend server running (`server_multi_rtsp.py`)

## Step 1: Verify Setup

Run the test script to ensure everything is configured:

```bash
cd /home/admin/videobase-pi
python3 test_hailo.py
```

You should see:
```
🎉 All tests passed! Hailo is ready to use.
```

If any tests fail, see [HAILO_SETUP.md](HAILO_SETUP.md) for troubleshooting.

## Step 2: Start Backend Server

```bash
python3 server_multi_rtsp.py
```

This starts the WebSocket server on port 9200.

## Step 3: Start Hailo Inference

In a new terminal:

```bash
./start-hailo-inference.sh
```

This launches Hailo AI clients for all three cameras. You should see:

```
Starting Hailo inference for camera1...
Started camera1 (PID: 1234)
Starting Hailo inference for camera2...
Started camera2 (PID: 1235)
Starting Hailo inference for camera3...
Started camera3 (PID: 1236)

All Hailo inference clients started!
```

## Step 4: View Dashboard

Open your browser to the frontend (default: `http://localhost:5173`)

You should see:
- ✅ Video streams from all cameras
- ✅ Green bounding boxes around detected objects
- ✅ Labels with object names and confidence percentages
- ✅ AI Status showing "Live" with detection count
- ✅ Hailo performance metrics (e.g., "Hailo: 27ms")

## What You'll See

### Dashboard Display

Each camera view shows:

```
Camera 1                    Live  6 FPS  #15104
[Video with bounding boxes]

AI Status: Live (1)  Hailo: 27ms    00:13:34
{
  "boxes": [[x, y, w, h, class_id, confidence]],
  "labels": ["cell phone"],
  "resolution": [1280, 720],
  "count": 52479
}
```

### Performance Metrics

- **Live (1)** - 1 object detected in current frame
- **Hailo: 27ms** - Inference took 27 milliseconds
- **count: 52479** - Total number of inferences run

## Customization

### Change Inference Speed

Edit `start-hailo-inference.sh`:

```bash
INFERENCE_FPS=5  # Increase for faster, decrease for lower CPU
```

- **2 FPS**: Low CPU, suitable for 3+ cameras
- **5 FPS**: Balanced (default)
- **10 FPS**: High responsiveness, higher CPU usage

### Use Different Model

Edit `start-hailo-inference.sh`:

```bash
# Faster, less accurate
MODEL_PATH="/usr/share/hailo-models/yolov6n_h8l.hef"

# Default - balanced
MODEL_PATH="/usr/share/hailo-models/yolov8s_h8l.hef"

# Person/face only
MODEL_PATH="/usr/share/hailo-models/yolov5s_personface_h8l.hef"
```

### Change Confidence Threshold

Edit `hailo_inference.py` line 66:

```python
confidence_threshold=0.5,  # 0.0 to 1.0
```

Lower = more detections (including false positives)
Higher = fewer, more confident detections

## Monitoring

### Check if Hailo clients are running:

```bash
ps aux | grep hailo_camera_client
```

Should show 3 processes (one per camera).

### View Hailo client logs:

The clients print to stdout. You'll see:

```
[camera1] Hailo stats: avg=27.3ms, fps=36.6, total=150
[camera2] Sent 2 detections (inference: 24.1ms)
```

### Check WebSocket connections:

```bash
# In server output, look for:
[camera1] AI data stream connected
[camera2] AI data stream connected
[camera3] AI data stream connected
```

## Troubleshooting

### No bounding boxes showing

1. Check Hailo clients are running: `ps aux | grep hailo`
2. Check WebSocket connections in server logs
3. Refresh browser (Ctrl+Shift+R)
4. Check browser console for errors (F12)

### High CPU usage

- Lower `INFERENCE_FPS` to 2-3
- Use YOLOv6n model instead of YOLOv8s
- Run inference on fewer cameras

### "Hailo device busy" error

- Only run one model per Hailo device
- Restart Hailo clients: `pkill -f hailo_camera_client`
- Then restart: `./start-hailo-inference.sh`

## Next Steps

- See [HAILO_SETUP.md](HAILO_SETUP.md) for advanced configuration
- Try different models and compare performance
- Adjust confidence threshold for your use case
- Set up as systemd service for auto-start on boot

## Support

- Hailo Documentation: https://hailo.ai/developer-zone/
- Project Issues: Create an issue in your repository
- Community: https://community.hailo.ai/

---

Happy detecting! 🎯
