# AI Agent & UI Workflows for OpenClaw

Complete guide for natural language video control with zero-friction UI.

## Overview

This system provides two layers of interaction:

1. **Agent Workflows** - AI-powered natural language processing for video commands
2. **UI Workflows** - Streamlined, minimal-friction interface for users

Both are designed to work seamlessly with OpenClaw AI.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        OpenClaw AI                               │
│                  (Natural Language Interface)                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│              Agent Workflows (Port 8889)                         │
│              - Intent parsing                                    │
│              - Workflow orchestration                            │
│              - Natural language responses                        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│           Video Skill Service (Port 8888)                        │
│           - Camera control                                       │
│           - Hailo inference                                      │
│           - Recording & detection storage                        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                   Cameras
```

## Quick Start

### 1. Start All Services

```bash
# Terminal 1: Video Skill Service
cd /home/admin/videobase-pi
./start-video-skill.sh 8888

# Terminal 2: Agent Workflows
./start-agent-workflows.sh 8889

# Terminal 3: Serve UI (optional, for standalone testing)
python3 -m http.server 8890
# Then visit: http://localhost:8890/ui_workflows.html
```

### 2. Test Natural Language Queries

```bash
# Smart capture
curl -X POST http://localhost:8889/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me camera 1"}'

# Security scan
curl -X POST http://localhost:8889/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Do a security check"}'

# Object search
curl -X POST http://localhost:8889/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Find all people detected in the last hour"}'
```

## Agent Workflows

### Available Workflows

#### 1. Smart Capture
Captures frame with AI analysis and natural language summary.

**Examples:**
- "Show me camera 1"
- "What do you see on camera 2?"
- "Take a picture of the front door"
- "Capture camera 3"

**Returns:**
```json
{
  "workflow_type": "smart_capture",
  "status": "completed",
  "result": {
    "camera_id": "camera1",
    "summary": "Detected 2 persons and 1 car",
    "detections": [...],
    "frame": "base64_image...",
    "timestamp": 1708367890.5
  }
}
```

#### 2. Motion Alert
Monitors camera for motion and sends alerts.

**Examples:**
- "Alert me if someone appears"
- "Watch camera 3 for movement"
- "Notify if you detect a person"
- "Monitor the back door"

**Returns:**
```json
{
  "workflow_type": "motion_alert",
  "result": {
    "camera_id": "camera1",
    "alerts": [
      {
        "timestamp": 1708367890.5,
        "detections": [...],
        "alert": "Detected 2 objects above 70% confidence"
      }
    ],
    "total_alerts": 5
  }
}
```

#### 3. Security Scan
Scans all cameras simultaneously for security concerns.

**Examples:**
- "Do a security check"
- "Scan all cameras"
- "What's the security status?"
- "Check the perimeter"

**Returns:**
```json
{
  "workflow_type": "security_scan",
  "result": {
    "security_status": "alert",
    "cameras_scanned": 3,
    "alerts": [
      {
        "camera_id": "camera1",
        "concerns": ["2 person(s) detected"]
      }
    ],
    "camera_details": [...]
  }
}
```

#### 4. Object Search
Searches detection history for specific objects.

**Examples:**
- "Find all people detected today"
- "When was a car last seen?"
- "Show me dog detections"
- "Has there been any bicycle activity?"

**Returns:**
```json
{
  "workflow_type": "object_search",
  "result": {
    "object_class": "person",
    "total_detections": 42,
    "timeline": "First seen at 08:30:15, last seen at 17:45:22",
    "detections": [...]
  }
}
```

#### 5. Auto Record
Starts recording with automatic stop after duration.

**Examples:**
- "Record camera 1 for 5 minutes"
- "Start recording the back door"
- "Capture video for 30 seconds"
- "Record camera 2 for an hour"

**Returns:**
```json
{
  "workflow_type": "auto_record",
  "result": {
    "recording_id": 42,
    "camera_id": "camera1",
    "status": "completed",
    "duration_seconds": 60,
    "detection_count": 15,
    "file_path": "/path/to/recording.mp4"
  }
}
```

#### 6. Summary Report
Generates comprehensive activity report.

**Examples:**
- "Give me a summary"
- "What happened today?"
- "Show me activity stats"
- "Generate a report"

**Returns:**
```json
{
  "workflow_type": "summary_report",
  "result": {
    "summary": "In the last 24 hours, detected 1523 objects. Most common: 842 person, 421 car, 185 dog.",
    "statistics": {...},
    "recordings": {...}
  }
}
```

### Intent Parsing

The system automatically detects intent from natural language:

```python
# Camera detection
"camera 1" → camera_id: "camera1"
"the front door" → camera_id: "camera1" (if configured)
"all cameras" → camera_id: None (all cameras)

# Object detection
"person" / "people" / "human" → object_class: "person"
"car" / "vehicle" → object_class: "car"
"dog" / "pet" → object_class: "dog"

# Time ranges
"last hour" → start_time: now - 3600
"today" / "last 24 hours" → start_time: now - 86400
"this morning" → start_time: start_of_day

# Durations
"30 seconds" → duration: 30
"5 minutes" → duration: 300
"1 hour" → duration: 3600
```

### API Endpoints

#### POST /agent/query
Process natural language query.

```bash
curl -X POST http://localhost:8889/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me camera 1",
    "user_email": "user@example.com"
  }'
```

#### POST /agent/workflow
Execute structured workflow.

```bash
curl -X POST http://localhost:8889/agent/workflow \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "smart_capture",
    "parameters": {
      "camera_id": "camera1",
      "with_inference": true,
      "save_frame": true
    }
  }'
```

#### GET /agent/workflows
List all available workflows with examples.

```bash
curl http://localhost:8889/agent/workflows
```

## UI Workflows

### Zero-Friction Interface

The UI is designed for maximum speed and minimal friction:

1. **Single Input Field** - Type anything, get instant results
2. **Quick Actions** - One-click common operations
3. **Live Previews** - See results immediately
4. **Smart Defaults** - No configuration needed
5. **Auto-Reconnect** - WebSocket streams reconnect automatically

### Key Features

#### Natural Language Input
```html
<!-- Large, prominent input field -->
<input placeholder="e.g., 'Show me camera 1'">
```
- Type natural language query
- Press Enter or click "Ask"
- Get instant AI-powered response

#### Quick Actions
Pre-configured common queries:
- 📷 Show Camera 1
- 🔒 Security Scan
- 📊 Activity Summary
- 👤 Find People
- ⏺️ Quick Record

#### Smart Response Display
Automatically formats response based on workflow type:
- **Smart Capture**: Shows image + detection badges
- **Security Scan**: Shows status + camera grid
- **Object Search**: Shows timeline + statistics
- **Summary Report**: Shows charts + breakdown

#### Live Camera Grid
- Auto-connects to first camera (reduce load)
- Shows live feed with detections
- Quick capture/record buttons per camera

### UI Integration with OpenClaw

#### Option 1: Serve via OpenClaw Worker

Copy UI to OpenClaw static directory:
```bash
cp /home/admin/videobase-pi/ui_workflows.html \
   /home/admin/openclaw-cloudflare/static/video.html
```

Update OpenClaw worker to serve static files:
```typescript
// In src/index.ts
app.get('/video', (c) => {
  return c.html(readFileSync('./static/video.html', 'utf-8'));
});
```

#### Option 2: Standalone with Proxy

Serve UI separately and proxy API calls:
```bash
# Serve UI
cd /home/admin/videobase-pi
python3 -m http.server 8890

# Update API_BASE in ui_workflows.html
const API_BASE = "http://localhost:8889";  // Agent workflows
```

#### Option 3: Cloudflare Pages

Deploy UI to Cloudflare Pages:
```bash
# Create pages project
wrangler pages project create video-skill-ui

# Deploy
wrangler pages publish /home/admin/videobase-pi/ui_workflows.html \
  --project-name=video-skill-ui

# Configure environment
# Set API_BASE to your worker URL
```

## OpenClaw Integration

### Natural Language Commands via OpenClaw

OpenClaw can send queries directly to the agent workflows:

```typescript
// In OpenClaw AI handler
async function handleVideoQuery(userQuery: string) {
  const response = await fetch('http://localhost:8889/agent/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: userQuery,
      user_email: session.userEmail
    })
  });

  const result = await response.json();

  if (result.status === 'completed') {
    return formatResponseForUser(result);
  } else {
    return `Error: ${result.error}`;
  }
}

function formatResponseForUser(workflow: WorkflowResponse) {
  const result = workflow.result;

  switch (workflow.workflow_type) {
    case 'smart_capture':
      return `${result.summary}\n\n[Image: ${result.frame}]`;

    case 'security_scan':
      return `Security Status: ${result.security_status}\n` +
             `Alerts: ${result.alerts.length}`;

    case 'summary_report':
      return result.summary;

    default:
      return JSON.stringify(result, null, 2);
  }
}
```

### Example Conversation Flow

```
User: Hey OpenClaw, show me what camera 1 sees

OpenClaw: Let me check camera 1 for you...
          [Calls /agent/query with "show me camera 1"]

Agent Workflows:
          [Executes smart_capture workflow]
          [Returns: "Detected 1 person and 2 cars"]

OpenClaw: I can see 1 person and 2 cars on camera 1.
          [Shows image with detection boxes]

User: Has anyone been detected in the last hour?

OpenClaw: Let me search the detection history...
          [Calls /agent/query with "find people detected last hour"]

Agent Workflows:
          [Executes object_search workflow]
          [Returns: "42 person detections"]

OpenClaw: Yes, I found 42 person detections in the last hour.
          First seen at 08:30, last seen at 09:25.

User: Do a security check

OpenClaw: Running a full security scan...
          [Calls /agent/query with "do a security check"]

Agent Workflows:
          [Executes security_scan workflow]
          [Checks all 3 cameras in parallel]

OpenClaw: Security scan complete:
          ✅ Camera 1: Clear
          ⚠️  Camera 2: 2 persons detected
          ✅ Camera 3: Clear
```

## Performance Optimization

### Speed Tips

1. **Parallel Execution**
   - Security scans run all cameras in parallel
   - Use asyncio for concurrent operations

2. **Smart Caching**
   - Cache recent captures (5 second TTL)
   - Reuse detection results for follow-up queries

3. **Reduced Latency**
   - Agent workflows <100ms processing time
   - Direct WebSocket streams (no polling)

4. **Intelligent Defaults**
   - Auto-detect camera from context
   - Use sensible time ranges
   - Optimize image quality vs size

### Friction Reduction

1. **No Authentication Required** (handled by OpenClaw)
2. **No Configuration** (smart defaults)
3. **No Multi-Step Flows** (single query = complete action)
4. **No Page Reloads** (all updates via WebSocket/AJAX)
5. **No Complex Forms** (natural language input)

## Testing

### Test Agent Workflows

```bash
# List available workflows
curl http://localhost:8889/agent/workflows

# Test each workflow type
python3 << 'EOF'
import requests

queries = [
    "Show me camera 1",
    "Do a security check",
    "Find all people detected today",
    "Give me a summary",
    "Record camera 1 for 10 seconds"
]

for query in queries:
    print(f"\nTesting: {query}")
    response = requests.post(
        "http://localhost:8889/agent/query",
        json={"query": query}
    )
    result = response.json()
    print(f"Status: {result['status']}")
    print(f"Time: {result.get('execution_time_ms', 0):.0f}ms")
EOF
```

### Test UI Workflows

1. Open `ui_workflows.html` in browser
2. Try quick actions
3. Type natural language queries
4. Verify responses display correctly
5. Check live camera streams

### Load Testing

```bash
# Install hey
go install github.com/rakyll/hey@latest

# Test agent workflows
hey -n 100 -c 10 -m POST \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me camera 1"}' \
  http://localhost:8889/agent/query
```

## Monitoring

### Logs

```bash
# Agent workflows logs
tail -f /home/admin/videobase-pi/agent_workflows.log

# Video skill logs
tail -f /home/admin/videobase-pi/video_skill.log

# Combined view
tail -f /home/admin/videobase-pi/*.log
```

### Metrics

```bash
# Query response times
grep "execution_time_ms" /home/admin/videobase-pi/agent_workflows.log | \
  awk '{print $NF}' | \
  awk '{sum+=$1; count++} END {print "Avg:", sum/count, "ms"}'

# Workflow type distribution
grep "workflow_type" /home/admin/videobase-pi/agent_workflows.log | \
  awk -F'"' '{print $4}' | \
  sort | uniq -c | sort -nr
```

## Troubleshooting

### "Agent workflows not responding"
```bash
# Check if service is running
curl http://localhost:8889/health

# Restart service
pkill -f agent_workflows.py
./start-agent-workflows.sh 8889
```

### "Cannot parse query"
- Check intent patterns in `agent_workflows.py`
- Add new patterns if needed
- Test with structured workflow API instead

### "Video skill API errors"
```bash
# Verify video skill is running
curl http://localhost:8888/health

# Check connectivity
nc -zv localhost 8888
```

### "UI not updating"
- Check browser console for errors
- Verify WebSocket connection
- Check CORS settings
- Try hard refresh (Ctrl+Shift+R)

## Advanced Customization

### Add New Workflow

1. **Define Workflow Type**
```python
class WorkflowType(str, Enum):
    # ... existing workflows ...
    MY_WORKFLOW = "my_workflow"
```

2. **Add Intent Patterns**
```python
INTENT_PATTERNS = {
    # ... existing patterns ...
    "my_workflow": ["my trigger", "another trigger"]
}
```

3. **Implement Workflow**
```python
async def _my_workflow(self, params: Dict) -> Dict:
    # Your workflow logic
    return {
        "result": "data",
        "summary": "Natural language summary"
    }
```

4. **Add UI Handler**
```javascript
function displayMyWorkflow(result, summary, details) {
    summary.textContent = result.summary;
    // Custom display logic
}
```

### Extend Intent Parser

Add domain-specific patterns:
```python
# In IntentParser class
CUSTOM_PATTERNS = {
    "locations": {
        "front_door": "camera1",
        "back_yard": "camera2",
        "garage": "camera3"
    }
}

def _extract_location(self, query: str) -> Optional[str]:
    for location, camera_id in self.CUSTOM_PATTERNS["locations"].items():
        if location.replace("_", " ") in query:
            return camera_id
    return None
```

## Production Deployment

### Systemd Services

Create `/etc/systemd/system/video-skill-agent.service`:
```ini
[Unit]
Description=Video Skill Agent Workflows
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/videobase-pi
ExecStart=/home/admin/videobase-pi/start-agent-workflows.sh 8889
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable video-skill-agent
sudo systemctl start video-skill-agent
sudo systemctl status video-skill-agent
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name video.example.com;

    # Agent workflows API
    location /api/ {
        proxy_pass http://localhost:8889/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Video skill API
    location /video/ {
        proxy_pass http://localhost:8888/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # UI
    location / {
        root /home/admin/videobase-pi;
        index ui_workflows.html;
    }
}
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY agent_workflows.py .
COPY video_skill_service.py .

EXPOSE 8888 8889

CMD ["sh", "-c", "python video_skill_service.py 8888 & python agent_workflows.py 8889"]
```

## Next Steps

1. **Enhance Intent Parser** - Add more natural language patterns
2. **Add Voice Control** - Integrate speech-to-text
3. **Multi-Language Support** - i18n for agent responses
4. **Custom Alerts** - Webhook notifications
5. **Mobile App** - Native iOS/Android clients
6. **Analytics Dashboard** - Usage metrics and trends

---

**Ready to use?**

```bash
# Start everything
./start-video-skill.sh 8888
./start-agent-workflows.sh 8889

# Open UI
open http://localhost:8890/ui_workflows.html

# Or integrate with OpenClaw
cd ../openclaw-cloudflare
npm run dev
```

**Test natural language:**
```bash
curl -X POST http://localhost:8889/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me camera 1"}'
```

🚀 **Speed + AI + Zero Friction = Perfect UX**
