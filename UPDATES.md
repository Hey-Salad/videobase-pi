# Recent Dashboard Updates

## ✨ New Features Added

### 1. Device Information Panel
A real-time monitoring panel showing Raspberry Pi system stats at the top of the dashboard.

**Displays:**
- 🌐 IP Address
- 🖥️ Hostname
- 🌡️ CPU Temperature (color-coded: green/yellow/red)
- ⚙️ CPU Load Average
- 💾 Memory Usage (percentage + free memory)
- 📊 Total RAM
- ⏱️ System Uptime
- 🐧 Platform/Architecture

**Auto-refresh:** Every 10 seconds

### 2. Video Feed Toggle
Each camera now has a Hide/Show button to collapse the video while keeping AI stats visible.

**Benefits:**
- Save bandwidth when only monitoring AI detections
- Reduce visual clutter
- Focus on specific cameras

**Location:** Top-right of each camera header (Eye icon button)

### 3. AI Source Toggle
Switch between Hailo-8L and reCamera AI inference sources.

**Two Modes:**
- **Hailo-8L (Blue):** Uses hardware NPU for accelerated detection
- **reCamera (Green):** Uses on-device camera AI

**Location:** Panel between Device Info and camera grid

### 4. Icons Instead of Emojis
Replaced all emojis with professional Lucide React icons for a cleaner look.

**Updated:**
- Eye/EyeOff icons for Hide/Show buttons
- Monitor icon for Device Info
- Cpu icon for Hailo mode
- Camera icon for reCamera mode

## 🔧 Technical Changes

### Backend
- **New Endpoint:** `GET /device-info` returns system stats
  - CPU temperature from `/sys/class/thermal/thermal_zone0/temp`
  - Memory info from `/proc/meminfo`
  - Uptime from `/proc/uptime`
  - CPU load from `uptime` command
  - IP address via socket connection

### Frontend
**New Components:**
- `DeviceInfo.jsx` - System stats display with auto-refresh

**Updated Components:**
- `MultiCameraView.jsx` - Added AI source toggle and DeviceInfo
- `CameraView.jsx` - Added video visibility toggle and AI source indicator
- All components now use Lucide React icons

**New Dependencies:**
- `lucide-react` - Icon library

## 🚀 How to Use

### Restart Backend
```bash
# Stop current server (Ctrl+C)
python3 server_multi_rtsp.py
```

### Restart Frontend
```bash
cd frontend
npm install  # Install lucide-react
npm run dev
```

### Or Hard Refresh Browser
Press `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)

## 📊 Dashboard Layout

```
┌─────────────────────────────────────────────────────┐
│ 🖥️ Device Information                              │
│ ┌──────┬──────┬──────┬──────┬──────┬──────┬──────┐│
│ │  IP  │ Host │ Temp │ Load │Memory│ RAM  │Uptime││
│ └──────┴──────┴──────┴──────┴──────┴──────┴──────┘│
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ ⚙️ AI Inference Source                             │
│                           [Hailo-8L] [reCamera]     │
│ Using Hailo-8L NPU for hardware-accelerated...     │
└─────────────────────────────────────────────────────┘

┌──────────┐ ┌──────────┐ ┌──────────┐
│Camera 1  │ │Camera 2  │ │Camera 3  │
│[👁️ Hide]│ │[👁️ Hide]│ │[👁️ Hide]│
│          │ │          │ │          │
│ [Video]  │ │ [Video]  │ │ [Video]  │
│          │ │          │ │          │
│AI Status │ │AI Status │ │AI Status │
└──────────┘ └──────────┘ └──────────┘
```

## 🎨 Color Coding

**Temperature:**
- 🟢 Green: < 60°C (Safe)
- 🟡 Yellow: 60-75°C (Warm)
- 🔴 Red: > 75°C (Hot)

**Memory:**
- 🟢 Green: < 70% (Healthy)
- 🟡 Yellow: 70-85% (High)
- 🔴 Red: > 85% (Critical)

**AI Source:**
- 🔵 Blue: Hailo-8L mode
- 🟢 Green: reCamera mode

## 🐛 Fixes

### Device Info CORS Issue
Fixed the "Unexpected token '<'" error by properly resolving the backend URL from the WebSocket configuration instead of using `window.location.host`.

**Before:** Tried to fetch from frontend dev server (port 5173)
**After:** Correctly fetches from backend server (port 9200)

## 📝 Configuration

### Change Device Info Refresh Rate
Edit `frontend/src/components/DeviceInfo.jsx`:
```javascript
const interval = setInterval(fetchDeviceInfo, 10000); // milliseconds
```

### Default AI Source
Edit `frontend/src/components/MultiCameraView.jsx`:
```javascript
const [aiSource, setAiSource] = useState('hailo'); // or 'recamera'
```

## 🔗 Related Files

**Backend:**
- [server_multi_rtsp.py](server_multi_rtsp.py#L235-L305) - Device info endpoint

**Frontend:**
- [DeviceInfo.jsx](frontend/src/components/DeviceInfo.jsx) - Device stats component
- [MultiCameraView.jsx](frontend/src/components/MultiCameraView.jsx) - Main dashboard with toggles
- [CameraView.jsx](frontend/src/components/CameraView.jsx) - Individual camera with hide/show

## 📚 Next Steps

1. **Monitor your system** - Watch CPU temp during Hailo inference
2. **Toggle AI sources** - Switch between Hailo and reCamera to compare
3. **Hide videos** - Use hide feature when bandwidth is limited
4. **Check memory** - Verify system has enough RAM for all cameras

## 💡 Tips

- Hide videos during heavy AI workload to reduce browser load
- Monitor CPU temperature when running 3 Hailo clients
- Use reCamera mode when Hailo clients aren't running
- Check uptime to verify system stability

---

Made with ❤️ by HeySalad
