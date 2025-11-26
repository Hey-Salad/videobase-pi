# Troubleshooting Guide

## "Failed to fetch" Error on Device Info

### Symptoms
- Dashboard shows: `Failed to load device info: Failed to fetch`
- Console shows: `Failed to fetch` or CORS error

### Root Cause
The backend server (`server_multi_rtsp.py`) is not running, or the frontend can't connect to it.

### Solution

#### Step 1: Check if backend is running
```bash
ps aux | grep server_multi_rtsp.py
```

If you see nothing, the server is not running.

#### Step 2: Start the backend
```bash
cd /home/admin/videobase-pi
python3 server_multi_rtsp.py
```

You should see:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:9200
```

#### Step 3: Verify backend is accessible
In a new terminal:
```bash
curl http://localhost:9200/device-info
```

You should see JSON output with device info.

#### Step 4: Restart frontend
```bash
cd /home/admin/videobase-pi/frontend

# Stop dev server (Ctrl+C)
# Then restart:
npm run dev
```

#### Step 5: Hard refresh browser
- Windows/Linux: `Ctrl+Shift+R`
- Mac: `Cmd+Shift+R`

### Still Not Working?

#### Check .env file
```bash
cat /home/admin/videobase-pi/frontend/.env
```

Should contain:
```
VITE_WS_URL=ws://localhost:9200/ws
VITE_API_URL=http://localhost:9200
```

#### Check browser console
1. Open browser DevTools (F12)
2. Go to Console tab
3. Look for the log: `Fetching device info from: http://localhost:9200/device-info`
4. If the URL is wrong, check your `.env` file

#### Check CORS
The backend already has CORS enabled for all origins. If you still get CORS errors:

1. Make sure backend is running on port 9200
2. Make sure frontend `.env` has correct `VITE_API_URL`
3. Restart both backend and frontend

## Other Common Issues

### Camera Videos Not Showing

**Symptoms:** Blank black boxes, "Connecting..." message

**Solutions:**
1. Check RTSP cameras are accessible:
   ```bash
   gst-launch-1.0 rtspsrc location=rtsp://admin:admin@192.168.1.136:554/live ! fakesink
   ```

2. Check camera URLs in `server_multi_rtsp.py` (lines 23-36)

3. Verify network connectivity to cameras

### AI Boxes Not Showing

**Symptoms:** Video works but no bounding boxes

**Solutions:**

#### For Hailo:
1. Check Hailo clients are running:
   ```bash
   ps aux | grep hailo_camera_client
   ```

2. If not running, start them:
   ```bash
   ./start-hailo-inference.sh
   ```

3. Check Hailo client logs for "Connected to server"

#### For reCamera:
1. Verify Node-RED flow is sending to `/ws/{camera_id}/ai`
2. Check WebSocket connection in browser console
3. Verify AI data format matches expected structure

### Frontend Won't Start

**Symptoms:** `npm run dev` fails

**Solutions:**
1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. If still fails, check Node.js version:
   ```bash
   node --version  # Should be 18+
   ```

3. Clear npm cache:
   ```bash
   npm cache clean --force
   npm install
   ```

### Hide/Show Button Not Working

**Symptoms:** Clicking button does nothing

**Solutions:**
1. Hard refresh browser (Ctrl+Shift+R)
2. Check browser console for React errors
3. Verify lucide-react is installed:
   ```bash
   cd frontend
   npm list lucide-react
   ```

### AI Source Toggle Not Changing Label

**Symptoms:** Toggle button works but camera labels don't change

**Solutions:**
1. Hard refresh browser
2. Check that `aiSource` prop is being passed to CameraView
3. Verify you're running the latest code

## Port Conflicts

### Backend Port 9200 Already in Use

**Error:** `Address already in use`

**Solutions:**
1. Find what's using the port:
   ```bash
   sudo lsof -i :9200
   ```

2. Kill the process:
   ```bash
   sudo kill <PID>
   ```

3. Or change the port in `server_multi_rtsp.py` (line 319)

### Frontend Port 5173 Already in Use

**Error:** `Port 5173 is in use`

**Solutions:**
1. Stop other Vite instances
2. Or specify different port:
   ```bash
   npm run dev -- --port 5174
   ```

## Performance Issues

### High CPU Usage

**Causes:**
- Running too many Hailo clients
- High inference FPS
- Too many cameras

**Solutions:**
1. Reduce Hailo FPS in `start-hailo-inference.sh`:
   ```bash
   INFERENCE_FPS=2  # Lower is better
   ```

2. Run Hailo on fewer cameras
3. Hide video feeds you're not watching

### High Memory Usage

**Solutions:**
1. Check available memory:
   ```bash
   free -h
   ```

2. Reduce number of active cameras
3. Lower video resolution in GStreamer pipeline

### Browser Lag

**Solutions:**
1. Hide videos you're not watching
2. Close other browser tabs
3. Use a more powerful computer for viewing
4. Reduce number of cameras displayed

## Hailo-Specific Issues

### Hailo Device Not Found

**Error:** `/dev/hailo0` not found

**Solutions:**
1. Check Hailo device:
   ```bash
   ls -la /dev/hailo*
   ```

2. Reinstall Hailo drivers:
   ```bash
   sudo apt install hailo-all
   ```

3. Reboot if needed

### Hailo Inference Failed

**Error:** Hailo inference errors in logs

**Solutions:**
1. Run test script:
   ```bash
   python3 test_hailo.py
   ```

2. Check model file exists:
   ```bash
   ls -lh /usr/share/hailo-models/yolov8s_h8l.hef
   ```

3. Verify Hailo SDK is installed:
   ```bash
   python3 -c "import hailo_platform; print('OK')"
   ```

## Getting Help

### Useful Commands

**Check all services:**
```bash
# Backend
ps aux | grep server_multi_rtsp.py

# Hailo clients
ps aux | grep hailo_camera_client

# Frontend (if running in background)
ps aux | grep vite
```

**View logs:**
```bash
# Backend logs (if running in foreground, just check terminal)

# System logs
journalctl -f

# Check for errors
dmesg | tail -50
```

**Test endpoints:**
```bash
# Health check
curl http://localhost:9200/health

# Device info
curl http://localhost:9200/device-info

# API root
curl http://localhost:9200/
```

### Still Stuck?

1. Check all logs for error messages
2. Verify all prerequisites are installed
3. Review [HAILO_SETUP.md](HAILO_SETUP.md) for Hailo issues
4. Review [README.md](README.md) for general setup
5. Create an issue with:
   - Error messages
   - Output of `curl http://localhost:9200/device-info`
   - Browser console logs
   - Backend terminal output

---

Need more help? Contact hello@heysalad.io
