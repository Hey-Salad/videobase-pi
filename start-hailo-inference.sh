#!/bin/bash
# Start Hailo AI Inference for all cameras
# This script launches Hailo AI inference clients for each camera

# Camera configurations
CAMERA1_RTSP="rtsp://admin:admin@192.168.1.136:554/live"
CAMERA2_RTSP="rtsp://admin:admin@192.168.1.110:554/live"
CAMERA3_RTSP="rtsp://admin:admin@192.168.1.106:554/live"

SERVER_URL="ws://localhost:9200"
MODEL_PATH="/usr/share/hailo-models/yolov8s_h8l.hef"
INFERENCE_FPS=5

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Function to start camera inference
start_camera() {
    local CAMERA_ID=$1
    local RTSP_URL=$2

    echo "Starting Hailo inference for $CAMERA_ID..."
    python3 hailo_camera_client.py \
        --camera-id "$CAMERA_ID" \
        --rtsp-url "$RTSP_URL" \
        --server "$SERVER_URL" \
        --model "$MODEL_PATH" \
        --fps $INFERENCE_FPS &

    echo "Started $CAMERA_ID (PID: $!)"
}

# Start inference for each camera
start_camera "camera1" "$CAMERA1_RTSP"
sleep 2  # Stagger startup to avoid overwhelming the Hailo device

start_camera "camera2" "$CAMERA2_RTSP"
sleep 2

start_camera "camera3" "$CAMERA3_RTSP"

echo ""
echo "All Hailo inference clients started!"
echo "Press Ctrl+C to stop all clients"
echo ""

# Wait for all background processes
wait
