# Hailo AI Integration Guide

This guide explains how to use Hailo-8L AI accelerator with your multi-camera RTSP system.

## Overview

The Hailo integration provides:
- **Hardware-accelerated AI inference** using Hailo-8L (26 TOPS)
- **Object detection** with YOLOv8/YOLOv6/YOLOv5 models
- **Real-time bounding boxes** on the web dashboard
- **Performance metrics** showing inference latency

## Architecture

```
RTSP Cameras → Hailo Camera Client → Hailo-8L → WebSocket → Server → Frontend
                 (Python)              (NPU)      (AI data)
```

Each camera has a dedicated client that:
1. Receives RTSP video stream via GStreamer
2. Runs AI inference on Hailo-8L accelerator
3. Sends detections to the server via WebSocket
4. Server broadcasts to frontend for display

## Files

- `hailo_inference.py` - Core Hailo detection module
- `hailo_camera_client.py` - RTSP client with Hailo inference
- `start-hailo-inference.sh` - Startup script for all cameras

## Prerequisites

### 1. Hailo Platform SDK

The Hailo Platform SDK should already be installed on your Raspberry Pi 5.

Verify installation:
```bash
python3 -c "import hailo_platform; print('Hailo SDK OK')"
ls /dev/hailo0  # Should show hailo device
```

### 2. Models

Pre-trained models are available in `/usr/share/hailo-models/`:
- `yolov8s_h8l.hef` - YOLOv8 Small (recommended, balanced speed/accuracy)
- `yolov6n_h8l.hef` - YOLOv6 Nano (faster, less accurate)
- `yolov5s_personface_h8l.hef` - Person/face detection
- `yolov8s_pose_h8l_pi.hef` - Pose estimation

## Quick Start

### 1. Install Python dependencies

```bash
cd /home/admin/videobase-pi
source venv/bin/activate  # If using virtual environment
pip install -r requirements.txt
```

The required packages:
- `hailo_platform` (already installed system-wide)
- `numpy`
- `opencv-python`
- `websockets`
- `pygobject` (for GStreamer)

### 2. Start the backend server

```bash
python3 server_multi_rtsp.py
```

Server runs on `http://localhost:9200`

### 3. Start Hailo inference clients

Start all cameras at once:
```bash
./start-hailo-inference.sh
```

Or start individual cameras:
```bash
python3 hailo_camera_client.py \
    --camera-id camera1 \
    --rtsp-url "rtsp://admin:admin@192.168.1.136:554/live" \
    --server ws://localhost:9200 \
    --model /usr/share/hailo-models/yolov8s_h8l.hef \
    --fps 5
```

### 4. Start the frontend

```bash
cd frontend
npm run dev
```

Open browser to `http://localhost:5173`

## Configuration

### Inference FPS

Control the AI inference rate to balance performance and CPU usage:

```bash
# In start-hailo-inference.sh
INFERENCE_FPS=5  # Lower = less CPU, higher latency
```

Recommended values:
- **5 FPS** - Good balance (default)
- **10 FPS** - More responsive, higher CPU usage
- **2 FPS** - Low CPU usage, slower updates

### Confidence Threshold

Edit `hailo_inference.py`:

```python
detector = HailoDetector(
    hef_path="...",
    confidence_threshold=0.5,  # Adjust 0.0-1.0
    nms_threshold=0.45
)
```

Lower threshold = more detections (including false positives)
Higher threshold = fewer detections (may miss objects)

### Camera Configuration

Edit RTSP URLs in `start-hailo-inference.sh`:

```bash
CAMERA1_RTSP="rtsp://username:password@camera-ip:554/stream"
CAMERA2_RTSP="rtsp://username:password@camera-ip:554/stream"
CAMERA3_RTSP="rtsp://username:password@camera-ip:554/stream"
```

## Using Different Models

### YOLOv6 Nano (Faster)

```bash
python3 hailo_camera_client.py \
    --model /usr/share/hailo-models/yolov6n_h8l.hef \
    ...
```

### Person/Face Detection

```bash
python3 hailo_camera_client.py \
    --model /usr/share/hailo-models/yolov5s_personface_h8l.hef \
    ...
```

**Note:** Different models may require adjustments to the postprocessing code in `hailo_inference.py` based on their output format.

## Performance

### Expected Performance (Hailo-8L on RPi 5)

| Model | Inference Time | FPS | Accuracy |
|-------|---------------|-----|----------|
| YOLOv8s | ~20-30ms | ~33-50 | High |
| YOLOv6n | ~15-20ms | ~50-66 | Medium |
| YOLOv5s | ~25-35ms | ~28-40 | High |

### Optimizing Performance

1. **Reduce inference FPS** if you have multiple cameras
   - 3 cameras × 5 FPS = 15 inferences/sec total

2. **Use smaller models** for faster processing
   - YOLOv6n is faster than YOLOv8s

3. **Lower RTSP resolution** to reduce preprocessing time
   - Edit GStreamer pipeline in `hailo_camera_client.py`

4. **Stagger camera startup** (already done in script)
   - Prevents overwhelming the Hailo device

## Troubleshooting

### "Hailo SDK not found"

Install Hailo Platform SDK:
```bash
# Follow Hailo documentation for RPi 5
sudo apt install hailo-all
```

### No detections appearing

1. Check Hailo client is running:
   ```bash
   ps aux | grep hailo_camera_client
   ```

2. Check WebSocket connection:
   ```bash
   # In hailo_camera_client output, look for:
   # "Connected to server"
   ```

3. Verify model file exists:
   ```bash
   ls -lh /usr/share/hailo-models/yolov8s_h8l.hef
   ```

### High CPU usage

- Reduce `INFERENCE_FPS` in startup script
- Use smaller model (YOLOv6n instead of YOLOv8s)
- Reduce number of cameras running inference

### Bounding boxes not showing

1. Check browser console for errors
2. Verify AI data format in network tab
3. Ensure frontend is updated (refresh browser)

## Frontend Display

The dashboard shows:
- **Green bounding boxes** around detected objects
- **Labels** with object class and confidence %
- **AI Status** showing detection count
- **Hailo metrics** showing inference latency in ms

Example:
```
AI Status: Live (3)  Hailo: 27ms
```

This means:
- 3 objects detected
- Hailo inference took 27ms

## Advanced Usage

### Custom Models

To use your own Hailo models:

1. Convert model to HEF format using Hailo Dataflow Compiler
2. Update `hailo_inference.py` postprocessing for your output format
3. Update `COCO_CLASSES` if using different classes
4. Point `--model` to your `.hef` file

### Multiple Hailo Devices

If you have multiple Hailo devices:

1. Edit `hailo_inference.py` to select device:
   ```python
   device = VDevice(device_id="0000:03:00.0")  # Specify device
   ```

2. Distribute cameras across devices for better performance

## System Service (Optional)

To run Hailo inference as a systemd service:

```bash
sudo nano /etc/systemd/system/hailo-inference.service
```

```ini
[Unit]
Description=Hailo AI Inference Service
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/videobase-pi
ExecStart=/home/admin/videobase-pi/start-hailo-inference.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable hailo-inference
sudo systemctl start hailo-inference
sudo systemctl status hailo-inference
```

## Support

- Hailo Documentation: https://hailo.ai/developer-zone/
- Hailo Community Forum: https://community.hailo.ai/
- GitHub Issues: https://github.com/hailo-ai/

## License

Hailo Platform SDK and models are subject to Hailo's licensing terms.
