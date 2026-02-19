#!/bin/bash
# Startup script for Video Skill Service

PORT=${1:-8888}
LOG_FILE="/home/admin/videobase-pi/video_skill.log"

echo "Starting Video Skill Service on port $PORT..."

cd /home/admin/videobase-pi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start the service
python3 video_skill_service.py $PORT 2>&1 | tee -a "$LOG_FILE"
