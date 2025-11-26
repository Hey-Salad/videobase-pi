#!/bin/bash
# Videobase Pi - Backend Startup Script

echo "🎥 Starting Videobase Pi Backend..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check if dependencies are installed
python -c "import fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "✅ Starting FastAPI server on http://0.0.0.0:8000"
echo "📡 WebSocket endpoint: ws://localhost:8000/ws"
echo "🏥 Health check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python server.py
