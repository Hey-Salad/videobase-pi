#!/bin/bash
# Quick start script for the backend server

cd /home/admin/videobase-pi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if dependencies are installed
python3 -c "import fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: Required dependencies not found!"
    echo "Please run: pip install -r requirements.txt"
    exit 1
fi

# Start the server
echo "Starting backend server on port 9200..."
echo "Press Ctrl+C to stop"
echo ""
python3 server_multi_rtsp.py
