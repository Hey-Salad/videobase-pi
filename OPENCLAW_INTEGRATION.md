# OpenClaw Integration Guide

This guide shows how to integrate the Video Skill Service with your OpenClaw deployment.

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Cloudflare Access                            │
│                  (@heysalad.io auth)                             │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│              OpenClaw Worker (Port 18789)                        │
│              - Authenticates users                               │
│              - Forwards X-Forwarded-User header                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│           Video Skill Service (Port 8888)                        │
│           - Reads X-Forwarded-User header                        │
│           - Provides video API/WebSocket                         │
│           - Runs Hailo inference                                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
┌──────▼─────┐  ┌──────▼─────┐  ┌──────▼─────┐
│  Camera 1  │  │  Camera 2  │  │  Camera 3  │
│   (136)    │  │   (110)    │  │   (106)    │
└────────────┘  └────────────┘  └────────────┘
```

## Option 1: Update OpenClaw Backend URL (Recommended)

This routes ALL OpenClaw traffic to the video skill service. Best if video is your primary use case.

### Step 1: Update OpenClaw Worker

Edit `/home/admin/openclaw-cloudflare/src/index.ts`:

```typescript
// Line 47: Change default backend URL
const backendUrl = c.env.OPENCLAW_BACKEND_URL || 'http://localhost:8888';
```

### Step 2: Test Locally

```bash
cd /home/admin/openclaw-cloudflare

# Start video skill
cd /home/admin/videobase-pi
./start-video-skill.sh 8888 &

# Start OpenClaw worker
cd /home/admin/openclaw-cloudflare
npm run dev
```

### Step 3: Test Integration

```bash
# Via OpenClaw (port 18789)
curl http://localhost:18789/health

# Should return video skill health check
```

### Step 4: Deploy

```bash
cd /home/admin/openclaw-cloudflare
npm run deploy
```

## Option 2: Path-Based Routing

Keep both services separate and route by path. Better for multi-service deployments.

### Step 1: Update OpenClaw Worker

Edit `/home/admin/openclaw-cloudflare/src/index.ts`:

```typescript
// Add after line 40 (after authentication middleware)

// Route video requests to video skill service
app.all('/video/*', async (c) => {
  const email = c.get('userEmail');
  const videoServiceUrl = c.env.VIDEO_SERVICE_URL || 'http://localhost:8888';

  const url = new URL(c.req.url);
  // Remove /video prefix
  const path = url.pathname.replace(/^\/video/, '');
  const backendRequestUrl = `${videoServiceUrl}${path}${url.search}`;

  try {
    const response = await fetch(backendRequestUrl, {
      method: c.req.method,
      headers: {
        ...Object.fromEntries(c.req.raw.headers),
        'X-Forwarded-User': email,
      },
      body: c.req.method !== 'GET' && c.req.method !== 'HEAD' ? c.req.raw.body : undefined,
    });

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  } catch (error) {
    console.error('Error proxying to video service:', error);
    return c.json({
      error: 'Video service unavailable',
      backend: videoServiceUrl,
    }, 503);
  }
});

// Continue with existing proxy for other paths...
```

### Step 2: Update WebSocket Handling

Edit `/home/admin/openclaw-cloudflare/src/index.ts` to handle WebSocket upgrades:

```typescript
// Add WebSocket proxy for video streams
app.get('/video/ws/:camera_id/stream', async (c) => {
  const email = c.get('userEmail');
  const videoServiceUrl = c.env.VIDEO_SERVICE_URL || 'http://localhost:8888';

  // Check if it's a WebSocket upgrade request
  const upgradeHeader = c.req.header('Upgrade');
  if (upgradeHeader?.toLowerCase() === 'websocket') {
    // Proxy WebSocket connection
    const wsUrl = videoServiceUrl.replace('http', 'ws') +
                  `/ws/${c.req.param('camera_id')}/stream` +
                  (c.req.url.includes('?') ? c.req.url.split('?')[1] : '');

    // Note: Cloudflare Workers automatically handle WebSocket proxying
    // Just return the backend response
    return fetch(wsUrl, {
      headers: {
        ...Object.fromEntries(c.req.raw.headers),
        'X-Forwarded-User': email,
      },
    });
  }

  return c.text('WebSocket upgrade required', 426);
});
```

### Step 3: API Routes

With path-based routing, access video skill via `/video/*` prefix:

```bash
# Health check
curl http://localhost:18789/video/health

# List cameras
curl http://localhost:18789/video/cameras

# Capture frame
curl -X POST http://localhost:18789/video/cameras/camera1/capture \
  -H "Content-Type: application/json" \
  -d '{"run_inference": true}'

# WebSocket stream
ws://localhost:18789/video/ws/camera1/stream?detections=true
```

## Option 3: Cloudflare Tunnel (Production)

Expose both services via separate Cloudflare Tunnels for production deployment.

### Step 1: Create Tunnel for Video Skill

```bash
# Install cloudflared (if not already)
# wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
# sudo mv cloudflared-linux-arm64 /usr/local/bin/cloudflared
# sudo chmod +x /usr/local/bin/cloudflared

# Create tunnel
cloudflared tunnel create video-skill

# Get tunnel ID
cloudflared tunnel list
```

### Step 2: Configure Tunnel

Create `/home/admin/.cloudflared/video-skill-config.yml`:

```yaml
tunnel: <TUNNEL_ID>
credentials-file: /home/admin/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: video.heysalad.app
    service: http://localhost:8888
  - service: http_status:404
```

### Step 3: Start Tunnel

```bash
cloudflared tunnel --config /home/admin/.cloudflared/video-skill-config.yml run video-skill
```

### Step 4: Update OpenClaw Worker

```bash
# Set environment variable
cd /home/admin/openclaw-cloudflare
wrangler secret put VIDEO_SERVICE_URL
# Enter: https://video.heysalad.app
```

### Step 5: Update DNS

In Cloudflare Dashboard:
1. Go to DNS settings for heysalad.app
2. Add CNAME record:
   - Name: `video`
   - Target: `<TUNNEL_ID>.cfargotunnel.com`
   - Proxied: Yes

## Testing the Integration

### 1. Start Services

```bash
# Terminal 1: Start video skill
cd /home/admin/videobase-pi
./start-video-skill.sh 8888

# Terminal 2: Start OpenClaw worker (dev mode)
cd /home/admin/openclaw-cloudflare
npm run dev
```

### 2. Test Without Auth (Dev Mode)

```bash
# Direct to video skill
curl http://localhost:8888/health

# Via OpenClaw proxy
curl http://localhost:18789/health
# or
curl http://localhost:18789/video/health  # if using path-based routing
```

### 3. Test With Auth (Production)

```bash
# Get Cloudflare Access JWT token from browser
# - Open DevTools → Network
# - Visit OpenClaw URL
# - Look for Cf-Access-Jwt-Assertion header
# - Copy the token

TOKEN="<your_jwt_token>"

# Test API via OpenClaw
curl https://openclaw-team.heysalad.app/health \
  -H "Cf-Access-Jwt-Assertion: $TOKEN"

# Test WebSocket (use browser or websocat)
websocat wss://openclaw-team.heysalad.app/ws/camera1/stream?detections=true \
  -H "Cf-Access-Jwt-Assertion: $TOKEN"
```

## Frontend Integration Example

### HTML/JavaScript Client

```html
<!DOCTYPE html>
<html>
<head>
  <title>Video Skill - OpenClaw</title>
  <style>
    body {
      font-family: sans-serif;
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
    }
    .camera-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
      gap: 20px;
    }
    .camera-card {
      border: 2px solid #ddd;
      border-radius: 8px;
      padding: 16px;
    }
    .camera-video {
      width: 100%;
      height: auto;
      border-radius: 4px;
      background: #000;
    }
    .detection-list {
      font-size: 14px;
      margin-top: 8px;
    }
    .detection-item {
      display: inline-block;
      padding: 4px 8px;
      margin: 2px;
      background: #e3f2fd;
      border-radius: 4px;
    }
  </style>
</head>
<body>
  <h1>Video Skill - OpenClaw</h1>

  <div id="camera-grid" class="camera-grid"></div>

  <script>
    const API_BASE = window.location.origin;  // OpenClaw URL
    const WS_BASE = API_BASE.replace('http', 'ws');

    async function loadCameras() {
      const response = await fetch(`${API_BASE}/cameras`);
      const data = await response.json();

      const grid = document.getElementById('camera-grid');

      data.cameras.forEach(camera => {
        const card = document.createElement('div');
        card.className = 'camera-card';
        card.innerHTML = `
          <h2>${camera.name}</h2>
          <img id="video-${camera.id}" class="camera-video" alt="${camera.name}">
          <div id="detections-${camera.id}" class="detection-list"></div>
          <button onclick="captureFrame('${camera.id}')">Capture Frame</button>
          <button onclick="startRecording('${camera.id}')">Start Recording</button>
          <button onclick="stopRecording('${camera.id}')">Stop Recording</button>
        `;
        grid.appendChild(card);

        // Start WebSocket stream
        connectStream(camera.id);
      });
    }

    function connectStream(cameraId) {
      const ws = new WebSocket(`${WS_BASE}/ws/${cameraId}/stream?detections=true`);

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'frame') {
          // Update video
          document.getElementById(`video-${cameraId}`).src =
            'data:image/jpeg;base64,' + data.frame;

          // Update detections
          const detectionsDiv = document.getElementById(`detections-${cameraId}`);
          detectionsDiv.innerHTML = data.detections
            .map(d => `<span class="detection-item">${d.class_name} ${(d.confidence * 100).toFixed(0)}%</span>`)
            .join('');
        }
      };

      ws.onerror = (error) => {
        console.error(`WebSocket error for ${cameraId}:`, error);
      };

      ws.onclose = () => {
        console.log(`WebSocket closed for ${cameraId}, reconnecting...`);
        setTimeout(() => connectStream(cameraId), 3000);
      };
    }

    async function captureFrame(cameraId) {
      const response = await fetch(`${API_BASE}/cameras/${cameraId}/capture`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ save_frame: true, run_inference: true })
      });

      const data = await response.json();
      alert(`Captured frame with ${data.detections.length} detections!\nSaved to: ${data.file_path}`);
    }

    async function startRecording(cameraId) {
      const duration = prompt('Recording duration (seconds):', '60');
      if (!duration) return;

      const response = await fetch(`${API_BASE}/cameras/${cameraId}/record/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          duration_seconds: parseInt(duration),
          include_detections: true
        })
      });

      const data = await response.json();
      alert(`Recording started! ID: ${data.recording_id}`);
    }

    async function stopRecording(cameraId) {
      const response = await fetch(`${API_BASE}/cameras/${cameraId}/record/stop`, {
        method: 'POST'
      });

      if (response.status === 404) {
        alert('No active recording for this camera');
      } else {
        const data = await response.json();
        alert(`Recording stopped! ID: ${data.recording_id}`);
      }
    }

    // Load cameras on page load
    loadCameras();
  </script>
</body>
</html>
```

Save this as `/home/admin/openclaw-cloudflare/static/video-skill.html` and serve it via OpenClaw.

## Monitoring & Logs

### Video Skill Logs
```bash
tail -f /home/admin/videobase-pi/video_skill.log
```

### OpenClaw Worker Logs
```bash
cd /home/admin/openclaw-cloudflare
npm run tail
```

### Database Inspection
```bash
sqlite3 /home/admin/videobase-pi/detections.db

# Query recent detections
SELECT camera_id, datetime(timestamp, 'unixepoch', 'localtime') as time,
       class_name, confidence
FROM detections
ORDER BY timestamp DESC
LIMIT 10;

# Query detection counts by camera
SELECT camera_id, COUNT(*) as count
FROM detections
GROUP BY camera_id;
```

## Security Considerations

1. **Authentication**: OpenClaw handles auth via Cloudflare Access
2. **User Identification**: Video skill receives `X-Forwarded-User` header
3. **RTSP Credentials**: Store in environment variables, not in code
4. **API Rate Limiting**: Consider adding rate limits for capture/recording endpoints
5. **File Access**: Restrict recording directory permissions

## Performance Tuning

### For Low Bandwidth
```typescript
// Reduce frame quality in WebSocket stream
// Edit video_skill_service.py line ~850
frame_base64 = self.camera_manager.encode_frame_base64(frame, quality=50)  // Lower = smaller
```

### For High Detection Rate
```python
# Process every Nth frame instead of every frame
# Edit video_skill_service.py in stream_camera method
if frame_count % 3 == 0:  # Process every 3rd frame
    detections = self.camera_manager.run_inference(frame)
```

### For Faster Response
```python
# Use lower resolution for inference
# Edit hailo_inference.py
input_size: Tuple[int, int] = (320, 320)  # Instead of (640, 640)
```

## Troubleshooting

### "Cannot connect to video service"
```bash
# Check if video skill is running
curl http://localhost:8888/health

# Check OpenClaw worker proxy
curl http://localhost:18789/health
```

### "WebSocket upgrade failed"
- Ensure Cloudflare Worker properly handles WebSocket upgrade
- Check browser console for errors
- Verify WebSocket URL is correct

### "No detections appearing"
```bash
# Test Hailo directly
cd /home/admin/videobase-pi
python3 test_hailo.py

# Test video skill inference
python3 test_video_skill.py capture_frame
```

## Next Steps

1. **Deploy to Production**: Follow deployment guides for both services
2. **Add Custom UI**: Build React/Vue frontend using the API
3. **Setup Alerts**: Configure webhooks for specific detections
4. **Optimize Performance**: Tune FPS, quality, and inference frequency
5. **Add Features**: Motion detection triggers, face recognition, etc.

---

**Ready to test?** Run:
```bash
./start-video-skill.sh 8888
cd ../openclaw-cloudflare && npm run dev
```

Then visit http://localhost:18789/health
