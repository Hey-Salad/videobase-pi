#!/bin/bash
# Startup script for Agent Workflows Service

PORT=${1:-8889}
LOG_FILE="/home/admin/videobase-pi/agent_workflows.log"

echo "Starting Agent Workflows Service on port $PORT..."

cd /home/admin/videobase-pi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start the service
python3 agent_workflows.py $PORT 2>&1 | tee -a "$LOG_FILE"
