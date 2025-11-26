#!/bin/bash
# Install system dependencies for Videobase Pi

echo "📦 Installing system dependencies for GStreamer and PyGObject..."
echo ""

sudo apt-get update
sudo apt-get install -y \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-tools \
    libgirepository1.0-dev \
    libcairo2-dev \
    pkg-config \
    python3-dev

echo ""
echo "✅ System dependencies installed!"
echo ""
echo "Now recreate your virtual environment with:"
echo "  rm -rf venv"
echo "  python3 -m venv venv --system-site-packages"
echo "  source venv/bin/activate"
echo "  pip install -r requirements.txt"
