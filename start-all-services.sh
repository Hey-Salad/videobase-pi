#!/bin/bash
# Start all video skill services together

echo "🚀 Starting Video Skill System..."
echo ""

cd /home/admin/videobase-pi

# Check if virtual environment exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
fi

# Start Video Skill Service
echo ""
echo "📹 Starting Video Skill Service (port 8888)..."
python3 video_skill_service.py 8888 > video_skill.log 2>&1 &
VIDEO_PID=$!
echo "✓ Video Skill Service started (PID: $VIDEO_PID)"

# Wait for video skill to be ready
sleep 2

# Start Agent Workflows
echo ""
echo "🤖 Starting Agent Workflows (port 8889)..."
python3 agent_workflows.py 8889 > agent_workflows.log 2>&1 &
AGENT_PID=$!
echo "✓ Agent Workflows started (PID: $AGENT_PID)"

# Wait for agent workflows to be ready
sleep 2

# Start UI Server (optional)
if [ "$1" == "--with-ui" ]; then
    echo ""
    echo "🌐 Starting UI Server (port 8890)..."
    python3 -m http.server 8890 > ui_server.log 2>&1 &
    UI_PID=$!
    echo "✓ UI Server started (PID: $UI_PID)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ All services started successfully!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Service URLs:"
echo "  • Video Skill API:    http://localhost:8888"
echo "  • Agent Workflows:    http://localhost:8889"
if [ "$1" == "--with-ui" ]; then
    echo "  • UI:                 http://localhost:8890/ui_workflows.html"
fi
echo ""
echo "Quick Test:"
echo '  curl -X POST http://localhost:8889/agent/query \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '\''{"query": "Show me camera 1"}'\'
echo ""
echo "View Logs:"
echo "  tail -f video_skill.log agent_workflows.log"
echo ""
echo "Stop Services:"
echo "  kill $VIDEO_PID $AGENT_PID"
if [ "$1" == "--with-ui" ]; then
    echo "  kill $UI_PID"
fi
echo ""
echo "Or use: pkill -f 'video_skill_service\\|agent_workflows'"
echo ""
echo "═══════════════════════════════════════════════════════════"

# Save PIDs to file for easy cleanup
echo "$VIDEO_PID" > .video_skill.pid
echo "$AGENT_PID" > .agent_workflows.pid
if [ "$1" == "--with-ui" ]; then
    echo "$UI_PID" > .ui_server.pid
fi

# Wait for services (Ctrl+C to stop)
echo ""
echo "Press Ctrl+C to stop all services..."
trap "echo ''; echo 'Stopping services...'; kill $VIDEO_PID $AGENT_PID 2>/dev/null; [ -n '$UI_PID' ] && kill $UI_PID 2>/dev/null; rm -f .*.pid; echo 'All services stopped.'; exit" INT

wait
