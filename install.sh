#!/bin/bash

###############################################################################
# Videobase Pi - Automated Installation Script
# Created by HeySalad
# This script installs and configures everything needed for the RTSP streamer
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$HOME/videobase-pi"
DOMAIN="recamera.heysalad.app"
RTSP_URL="rtsp://admin:admin@192.168.42.1:554/live"

# Functions
print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_internet() {
    print_info "Checking internet connection..."
    if ping -c 1 google.com &> /dev/null; then
        print_success "Internet connection OK"
        return 0
    else
        print_error "No internet connection. Please check your network."
        exit 1
    fi
}

get_local_ip() {
    hostname -I | awk '{print $1}'
}

prompt_user() {
    echo -e "\n${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║         Videobase Pi Installation Wizard              ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}\n"
    
    echo -e "This script will install:"
    echo -e "  ${GREEN}•${NC} Node.js 18.x"
    echo -e "  ${GREEN}•${NC} FFmpeg"
    echo -e "  ${GREEN}•${NC} Nginx"
    echo -e "  ${GREEN}•${NC} PM2 Process Manager"
    echo -e "  ${GREEN}•${NC} Backend WebSocket Server"
    echo -e "  ${GREEN}•${NC} Frontend React Application"
    echo -e ""
    
    read -p "Continue? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Installation cancelled."
        exit 0
    fi
    
    echo -e "\n${BLUE}Choose installation mode:${NC}"
    echo -e "  ${GREEN}1)${NC} Local Network Only (Recommended for testing)"
    echo -e "  ${GREEN}2)${NC} Public Access with Domain (Requires port forwarding)"
    echo -e "  ${GREEN}3)${NC} Cloudflare Tunnel (Best for production, no port forwarding)"
    echo -e ""
    read -p "Enter choice (1-3): " MODE_CHOICE
    
    case $MODE_CHOICE in
        1)
            INSTALL_MODE="local"
            print_info "Installing for local network access only"
            ;;
        2)
            INSTALL_MODE="public"
            print_warning "You will need to configure port forwarding on your router"
            read -p "Enter your domain (default: recamera.heysalad.app): " DOMAIN_INPUT
            DOMAIN=${DOMAIN_INPUT:-$DOMAIN}
            ;;
        3)
            INSTALL_MODE="cloudflare"
            print_info "Installing with Cloudflare Tunnel"
            read -p "Enter your domain (default: recamera.heysalad.app): " DOMAIN_INPUT
            DOMAIN=${DOMAIN_INPUT:-$DOMAIN}
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
    
    read -p "Enter RTSP URL (default: $RTSP_URL): " RTSP_INPUT
    RTSP_URL=${RTSP_INPUT:-$RTSP_URL}
}

install_system_packages() {
    print_header "Installing System Packages"
    
    print_info "Updating package lists..."
    sudo apt update
    
    print_info "Installing FFmpeg..."
    sudo apt install -y ffmpeg
    
    print_info "Installing Nginx..."
    sudo apt install -y nginx
    
    print_info "Installing curl and other dependencies..."
    sudo apt install -y curl git build-essential
    
    print_success "System packages installed"
}

install_nodejs() {
    print_header "Installing Node.js"
    
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node -v)
        print_warning "Node.js already installed: $NODE_VERSION"
        read -p "Reinstall Node.js? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 0
        fi
    fi
    
    print_info "Adding NodeSource repository..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    
    print_info "Installing Node.js..."
    sudo apt install -y nodejs
    
    NODE_VERSION=$(node -v)
    NPM_VERSION=$(npm -v)
    print_success "Node.js installed: $NODE_VERSION"
    print_success "NPM installed: $NPM_VERSION"
}

install_pm2() {
    print_header "Installing PM2"
    
    print_info "Installing PM2 globally..."
    sudo npm install -g pm2
    
    print_success "PM2 installed: $(pm2 -v)"
}

setup_project_structure() {
    print_header "Setting Up Project Structure"
    
    if [ -d "$PROJECT_DIR" ]; then
        print_warning "Project directory already exists: $PROJECT_DIR"
        read -p "Delete and recreate? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$PROJECT_DIR"
        else
            print_error "Cannot continue with existing directory"
            exit 1
        fi
    fi
    
    print_info "Creating project directories..."
    mkdir -p "$PROJECT_DIR"/{backend,frontend}
    
    print_success "Project structure created at $PROJECT_DIR"
}

setup_backend() {
    print_header "Setting Up Backend"
    
    cd "$PROJECT_DIR/backend"
    
    print_info "Creating package.json..."
    cat > package.json << 'EOF'
{
  "name": "videobase-backend",
  "version": "1.0.0",
  "description": "RTSP to WebSocket bridge",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  },
  "dependencies": {
    "ws": "^8.14.2",
    "express": "^4.18.2",
    "cors": "^2.8.5"
  },
  "devDependencies": {
    "nodemon": "^3.0.1"
  }
}
EOF
    
    print_info "Creating server.js..."
    cat > server.js << 'SERVEREOF'
const WebSocket = require('ws');
const { spawn } = require('child_process');
const express = require('express');
const cors = require('cors');

const app = express();
app.use(cors());

const PORT = 8080;
const wss = new WebSocket.Server({ port: PORT });

console.log(`🚀 WebSocket server running on port ${PORT}`);

wss.on('connection', (ws) => {
  console.log('📱 Client connected');
  let ffmpegProcess = null;

  ws.on('message', (message) => {
    const data = JSON.parse(message);

    if (data.type === 'start') {
      const rtspUrl = data.rtspUrl || 'rtsp://admin:admin@192.168.42.1:554/live';
      
      console.log(`🎥 Starting stream from: ${rtspUrl}`);

      ffmpegProcess = spawn('ffmpeg', [
        '-rtsp_transport', 'tcp',
        '-i', rtspUrl,
        '-f', 'image2pipe',
        '-vcodec', 'mjpeg',
        '-q:v', '5',
        '-r', '30',
        '-'
      ]);

      let frameBuffer = Buffer.alloc(0);
      const SOI = Buffer.from([0xFF, 0xD8]);
      const EOI = Buffer.from([0xFF, 0xD9]);

      ffmpegProcess.stdout.on('data', (chunk) => {
        frameBuffer = Buffer.concat([frameBuffer, chunk]);

        let soiIndex = frameBuffer.indexOf(SOI);
        let eoiIndex = frameBuffer.indexOf(EOI);

        while (soiIndex !== -1 && eoiIndex !== -1 && eoiIndex > soiIndex) {
          const frame = frameBuffer.slice(soiIndex, eoiIndex + 2);
          
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(frame);
          }

          frameBuffer = frameBuffer.slice(eoiIndex + 2);
          soiIndex = frameBuffer.indexOf(SOI);
          eoiIndex = frameBuffer.indexOf(EOI);
        }
      });

      ffmpegProcess.stderr.on('data', (data) => {
        const message = data.toString();
        if (message.includes('frame=')) {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'connected' }));
          }
        }
      });

      ffmpegProcess.on('error', (error) => {
        console.error('❌ FFmpeg error:', error);
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ 
            type: 'error', 
            message: 'Failed to start stream. Check RTSP URL and camera connection.' 
          }));
        }
      });

      ffmpegProcess.on('close', (code) => {
        console.log(`⚠️ FFmpeg process exited with code ${code}`);
      });
    }
  });

  ws.on('close', () => {
    console.log('📴 Client disconnected');
    if (ffmpegProcess) {
      ffmpegProcess.kill('SIGTERM');
    }
  });

  ws.on('error', (error) => {
    console.error('❌ WebSocket error:', error);
    if (ffmpegProcess) {
      ffmpegProcess.kill('SIGTERM');
    }
  });
});

console.log('✅ RTSP to WebSocket bridge ready!');
console.log(`🌐 Connect your frontend to ws://localhost:8080`);
SERVEREOF
    
    print_info "Installing backend dependencies..."
    npm install
    
    print_success "Backend setup complete"
}

setup_frontend() {
    print_header "Setting Up Frontend"
    
    cd "$PROJECT_DIR"
    
    print_info "Creating Vite React app..."
    npm create vite@latest frontend -- --template react
    
    cd frontend
    
    print_info "Installing dependencies..."
    npm install
    npm install lucide-react
    npm install -D tailwindcss postcss autoprefixer
    
    print_info "Initializing Tailwind CSS..."
    npx tailwindcss init -p
    
    print_info "Configuring Tailwind..."
    cat > tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
EOF
    
    cat > src/index.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;
EOF
    
    print_info "Creating App.jsx..."
    cat > src/App.jsx << 'APPEOF'
import React, { useState, useEffect, useRef } from 'react';
import { Video, Wifi, WifiOff, Activity, RefreshCw, Settings, Maximize2 } from 'lucide-react';

const RecameraStreamer = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [fps, setFps] = useState(0);
  const [error, setError] = useState(null);
  const [rtspUrl, setRtspUrl] = useState('RTSP_URL_PLACEHOLDER');
  const [showSettings, setShowSettings] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const videoRef = useRef(null);
  const containerRef = useRef(null);
  const wsRef = useRef(null);
  const frameCountRef = useRef(0);
  const lastTimeRef = useRef(Date.now());

  useEffect(() => {
    connectToStream();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [rtspUrl]);

  const connectToStream = () => {
    setIsLoading(true);
    setError(null);

    const wsUrl = `ws://${window.location.hostname}:8080`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      ws.send(JSON.stringify({ type: 'start', rtspUrl }));
    };

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        const data = JSON.parse(event.data);
        if (data.type === 'connected') {
          setIsConnected(true);
          setIsLoading(false);
        } else if (data.type === 'error') {
          setError(data.message);
          setIsLoading(false);
        }
      } else {
        const blob = new Blob([event.data], { type: 'image/jpeg' });
        const url = URL.createObjectURL(blob);
        if (videoRef.current) {
          videoRef.current.src = url;
        }
        
        frameCountRef.current++;
        const now = Date.now();
        if (now - lastTimeRef.current >= 1000) {
          setFps(frameCountRef.current);
          frameCountRef.current = 0;
          lastTimeRef.current = now;
        }
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('Connection failed. Make sure the server is running.');
      setIsLoading(false);
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      setIsConnected(false);
    };
  };

  const handleReconnect = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    connectToStream();
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <header className="bg-slate-800/50 backdrop-blur-sm border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
                  <Video className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-white">Videobase Pi</h1>
                  <p className="text-sm text-slate-400">Powered by HeySalad</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-700/50">
                {isConnected ? (
                  <>
                    <Wifi className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm text-emerald-400 font-medium">Connected</span>
                  </>
                ) : (
                  <>
                    <WifiOff className="w-4 h-4 text-red-400" />
                    <span className="text-sm text-red-400 font-medium">Disconnected</span>
                  </>
                )}
              </div>

              <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-700/50">
                <Activity className="w-4 h-4 text-blue-400" />
                <span className="text-sm text-white font-medium">{fps} FPS</span>
              </div>

              <button
                onClick={() => setShowSettings(!showSettings)}
                className="p-2 rounded-lg bg-slate-700 hover:bg-slate-600 transition-colors"
              >
                <Settings className="w-5 h-5 text-white" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {showSettings && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Stream Settings</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  RTSP URL
                </label>
                <input
                  type="text"
                  value={rtspUrl}
                  onChange={(e) => setRtspUrl(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="rtsp://admin:admin@192.168.42.1:554/live"
                />
              </div>
              <button
                onClick={handleReconnect}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Apply & Reconnect
              </button>
            </div>
          </div>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div 
          ref={containerRef}
          className="relative bg-slate-800 rounded-2xl overflow-hidden shadow-2xl border border-slate-700"
        >
          <div className="relative aspect-video bg-slate-900">
            {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <div className="inline-block w-16 h-16 border-4 border-slate-600 border-t-emerald-500 rounded-full animate-spin mb-4"></div>
                  <p className="text-slate-400">Connecting to stream...</p>
                </div>
              </div>
            )}

            {error && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center max-w-md px-6">
                  <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <WifiOff className="w-8 h-8 text-red-400" />
                  </div>
                  <h3 className="text-xl font-semibold text-white mb-2">Connection Error</h3>
                  <p className="text-slate-400 mb-6">{error}</p>
                  <button
                    onClick={handleReconnect}
                    className="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2 mx-auto"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Retry Connection
                  </button>
                </div>
              </div>
            )}

            <img
              ref={videoRef}
              alt="RTSP Stream"
              className={`w-full h-full object-contain ${!isConnected || error ? 'hidden' : ''}`}
            />

            {isConnected && (
              <div className="absolute bottom-4 right-4">
                <button
                  onClick={toggleFullscreen}
                  className="p-3 bg-slate-900/80 hover:bg-slate-900 rounded-lg backdrop-blur-sm transition-colors"
                >
                  <Maximize2 className="w-5 h-5 text-white" />
                </button>
              </div>
            )}
          </div>

          <div className="bg-slate-900/50 backdrop-blur-sm px-6 py-4 border-t border-slate-700">
            <div className="flex items-center justify-between text-sm">
              <div className="text-slate-400">
                Stream URL: <span className="text-white font-mono text-xs">{rtspUrl}</span>
              </div>
              <div className="text-slate-400">
                Resolution: <span className="text-white">Auto</span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 bg-slate-800/30 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Quick Start Guide</h3>
          <div className="space-y-3 text-slate-300">
            <p>1. Ensure your reCamera is connected to the network</p>
            <p>2. The default RTSP URL should work for most setups</p>
            <p>3. Click settings to customize the RTSP URL if needed</p>
            <p>4. Stream will automatically reconnect if connection is lost</p>
          </div>
        </div>
      </main>

      <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center text-slate-500">
        <p>Made with ❤️ by <span className="text-emerald-400 font-semibold">HeySalad</span></p>
      </footer>
    </div>
  );
};

export default RecameraStreamer;
APPEOF
    
    # Replace RTSP URL placeholder
    sed -i "s|RTSP_URL_PLACEHOLDER|$RTSP_URL|g" src/App.jsx
    
    print_info "Updating main.jsx..."
    cat > src/main.jsx << 'EOF'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
EOF
    
    print_info "Updating vite.config.js..."
    cat > vite.config.js << 'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
  },
  build: {
    outDir: 'dist',
  }
})
EOF
    
    print_info "Building frontend..."
    npm run build
    
    print_success "Frontend setup complete"
}

setup_nginx() {
    print_header "Setting Up Nginx"
    
    LOCAL_IP=$(get_local_ip)
    
    if [ "$INSTALL_MODE" = "local" ]; then
        print_info "Configuring Nginx for local access..."
        NGINX_CONFIG="/etc/nginx/sites-available/videobase-local"
        
        sudo tee "$NGINX_CONFIG" > /dev/null << EOF
server {
    listen 80 default_server;
    server_name _;

    location / {
        root $PROJECT_DIR/frontend/dist;
        try_files \$uri \$uri/ /index.html;
        
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    location /ws {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400;
    }
}
EOF
    else
        print_info "Configuring Nginx for domain access..."
        NGINX_CONFIG="/etc/nginx/sites-available/$DOMAIN"
        
        sudo tee "$NGINX_CONFIG" > /dev/null << EOF
upstream websocket_backend {
    server localhost:8080;
}

server {
    listen 80;
    server_name $DOMAIN;

    location / {
        root $PROJECT_DIR/frontend/dist;
        try_files \$uri \$uri/ /index.html;
        
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    location /ws {
        proxy_pass http://websocket_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF
    fi
    
    print_info "Removing default Nginx site..."
    sudo rm -f /etc/nginx/sites-enabled/default
    
    print_info "Enabling site..."
    if [ "$INSTALL_MODE" = "local" ]; then
        sudo ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/
    else
        sudo ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/
    fi
    
    print_info "Testing Nginx configuration..."
    if sudo nginx -t; then
        print_success "Nginx configuration valid"
        sudo systemctl restart nginx
        print_success "Nginx restarted"
    else
        print_error "Nginx configuration invalid"
        exit 1
    fi
}

setup_pm2() {
    print_header "Setting Up PM2"
    
    cd "$PROJECT_DIR/backend"
    
    print_info "Stopping any existing PM2 processes..."
    pm2 delete videobase-backend 2>/dev/null || true
    
    print_info "Starting backend with PM2..."
    pm2 start server.js --name videobase-backend
    
    print_info "Saving PM2 configuration..."
    pm2 save
    
    print_info "Setting up PM2 startup..."
    pm2 startup systemd -u $USER --hp $HOME
    
    print_success "PM2 configured"
}

setup_cloudflare_tunnel() {
    print_header "Setting Up Cloudflare Tunnel"
    
    print_info "Downloading cloudflared..."
    cd /tmp
    wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
    sudo dpkg -i cloudflared-linux-arm64.deb
    
    print_warning "Please complete these steps manually:"
    echo -e "\n1. Run: ${GREEN}cloudflared tunnel login${NC}"
    echo -e "2. Create tunnel: ${GREEN}cloudflared tunnel create recamera-pi${NC}"
    echo -e "3. Configure ~/.cloudflared/config.yml with:"
    echo -e "${BLUE}"
    cat << 'EOF'
tunnel: YOUR_TUNNEL_ID
credentials-file: /home/pi/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: recamera.heysalad.app
    service: http://localhost:80
  - hostname: recamera.heysalad.app
    path: /ws
    service: http://localhost:8080
  - service: http_status:404
EOF
    echo -e "${NC}"
    echo -e "4. Run tunnel: ${GREEN}cloudflared tunnel run recamera-pi${NC}"
    echo -e "5. Install as service: ${GREEN}sudo cloudflared service install${NC}"
    echo -e "\nPress Enter when done..."
    read
}

print_summary() {
    print_header "Installation Complete! 🎉"
    
    LOCAL_IP=$(get_local_ip)
    
    echo -e "${GREEN}✓ System packages installed${NC}"
    echo -e "${GREEN}✓ Node.js and NPM installed${NC}"
    echo -e "${GREEN}✓ Backend server configured${NC}"
    echo -e "${GREEN}✓ Frontend built and deployed${NC}"
