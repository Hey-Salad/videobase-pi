# Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Step 1: Install Dependencies (One-time)

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### Step 2: Start Backend

```bash
# Option 1: Use the helper script
./start-backend.sh

# Option 2: Manual start
source venv/bin/activate
python server.py
```

Backend will be running on `http://localhost:8000`

### Step 3: Start Frontend (Development)

```bash
cd frontend
npm run dev
```

Frontend will be running on `http://localhost:3000`

### Step 4: Access the Application

Open your browser to: **http://localhost:3000**

You should see the video stream from your reCamera!

---

## 🌐 Deploy to Cloudflare (Production)

### Backend: Cloudflare Tunnel

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

# Login and create tunnel
cloudflared tunnel login
cloudflared tunnel create videobase-pi

# Configure tunnel (edit ~/.cloudflared/config.yml)
# See DEPLOYMENT.md for details

# Run tunnel
cloudflared tunnel run videobase-pi
```

### Frontend: Cloudflare Pages

1. Push to GitHub
2. Go to [Cloudflare Pages](https://pages.cloudflare.com/)
3. Connect repository
4. Build settings:
   - Build command: `npm run build`
   - Output directory: `dist`
   - Root directory: `frontend`
5. Set env var: `VITE_WS_URL=wss://your-tunnel.com/ws`
6. Deploy!

---

## 📖 Full Documentation

- **[README.md](README.md)** - Complete documentation
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Detailed deployment guide
- **[frontend/README.md](frontend/README.md)** - Frontend-specific docs

## 🆘 Common Issues

**No video showing?**
- Check if reCamera is powered on
- Verify RTSP URL in `server.py` line 14

**WebSocket not connecting?**
- Ensure backend is running on port 8000
- Check browser console for errors
- Verify `VITE_WS_URL` in frontend/.env

**Need help?**
- Email: hello@heysalad.io
- GitHub Issues: [Create an issue](https://github.com/Hey-Salad/videobase-pi/issues)
