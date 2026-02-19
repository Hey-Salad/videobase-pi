#!/bin/bash
# Stop all video skill services

echo "🛑 Stopping Video Skill System..."

cd /home/admin/videobase-pi

# Stop using PID files if they exist
if [ -f .video_skill.pid ]; then
    kill $(cat .video_skill.pid) 2>/dev/null && echo "✓ Stopped Video Skill Service"
    rm .video_skill.pid
fi

if [ -f .agent_workflows.pid ]; then
    kill $(cat .agent_workflows.pid) 2>/dev/null && echo "✓ Stopped Agent Workflows"
    rm .agent_workflows.pid
fi

if [ -f .ui_server.pid ]; then
    kill $(cat .ui_server.pid) 2>/dev/null && echo "✓ Stopped UI Server"
    rm .ui_server.pid
fi

# Fallback: kill by process name
pkill -f "video_skill_service.py" 2>/dev/null
pkill -f "agent_workflows.py" 2>/dev/null

echo ""
echo "✅ All services stopped"
