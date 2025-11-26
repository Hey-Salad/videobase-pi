# Deployment Guide - Cloudflare Setup

This guide will walk you through deploying your Videobase Pi application using Cloudflare Tunnel and Cloudflare Pages.

## Prerequisites
- Cloudflare account (free tier works)
- Raspberry Pi with the backend running
- GitHub account (for automatic deployments)

## Part 1: Set Up Cloudflare Tunnel (Backend)

### 1. Install cloudflared on Raspberry Pi

```bash
# Download and install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

# Verify installation
cloudflared --version
```

### 2. Authenticate with Cloudflare

```bash
cloudflared tunnel login
```

This will open a browser window. Log in to your Cloudflare account and select the domain you want to use.

### 3. Create a Tunnel

```bash
cloudflared tunnel create videobase-pi
```

Save the **Tunnel ID** shown in the output. You'll need it for the next steps.

### 4. Create Tunnel Configuration

Create the file `~/.cloudflared/config.yml`:

```yaml
tunnel: YOUR-TUNNEL-ID-HERE
credentials-file: /home/admin/.cloudflared/YOUR-TUNNEL-ID-HERE.json

ingress:
  # Replace with your actual domain/subdomain
  - hostname: videobase.yourdomain.com
    service: http://localhost:8000

  # Catch-all rule (required)
  - service: http_status:404
```

Replace:
- `YOUR-TUNNEL-ID-HERE` with your actual tunnel ID
- `videobase.yourdomain.com` with your desired hostname

### 5. Create DNS Record

```bash
cloudflared tunnel route dns videobase-pi videobase.yourdomain.com
```

This creates a CNAME record pointing to your tunnel.

### 6. Test the Tunnel

```bash
# Start your backend
python server.py

# In another terminal, run the tunnel
cloudflared tunnel run videobase-pi
```

Test by visiting: `https://videobase.yourdomain.com/health`

You should see: `{"status":"healthy","frame_count":0}`

### 7. Run Tunnel as a Service (Production)

```bash
# Install as system service
sudo cloudflared service install

# Start the service
sudo systemctl start cloudflared

# Enable on boot
sudo systemctl enable cloudflared

# Check status
sudo systemctl status cloudflared

# View logs
sudo journalctl -u cloudflared -f
```

## Part 2: Deploy Frontend to Cloudflare Pages

### Option A: GitHub Integration (Recommended)

1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Add React frontend with Cloudflare support"
   git push origin main
   ```

2. **Create Cloudflare Pages Project**
   - Go to [Cloudflare Dashboard](https://dash.cloudflare.com/)
   - Navigate to **Pages** in the sidebar
   - Click **Create a project** → **Connect to Git**
   - Select your repository
   - Click **Begin setup**

3. **Configure Build Settings**
   ```
   Project name: videobase-pi
   Production branch: main
   Build command: npm run build
   Build output directory: dist
   Root directory: frontend
   ```

4. **Set Environment Variable**
   - Click **Environment variables**
   - Add variable:
     - **Variable name**: `VITE_WS_URL`
     - **Value**: `wss://videobase.yourdomain.com/ws`
   - Click **Save**

5. **Deploy**
   - Click **Save and Deploy**
   - Wait for build to complete (~2-3 minutes)
   - Your site will be available at: `https://videobase-pi.pages.dev`

6. **Add Custom Domain (Optional)**
   - Go to your Pages project → **Custom domains**
   - Click **Set up a custom domain**
   - Enter your domain (e.g., `app.yourdomain.com`)
   - Follow DNS configuration instructions

### Option B: Wrangler CLI

1. **Install Wrangler**
   ```bash
   npm install -g wrangler
   ```

2. **Login to Cloudflare**
   ```bash
   wrangler login
   ```

3. **Build and Deploy**
   ```bash
   cd frontend

   # Build the project
   npm run build

   # Deploy to Cloudflare Pages
   wrangler pages deploy dist --project-name=videobase-pi
   ```

4. **Set Environment Variable**
   ```bash
   wrangler pages secret put VITE_WS_URL
   # When prompted, enter: wss://videobase.yourdomain.com/ws
   ```

## Part 3: Testing Everything Together

1. **Backend**: Ensure backend is running on Raspberry Pi
   ```bash
   curl https://videobase.yourdomain.com/health
   ```

2. **Tunnel**: Check tunnel status
   ```bash
   sudo systemctl status cloudflared
   ```

3. **Frontend**: Visit your Cloudflare Pages URL
   - You should see the video stream interface
   - Check browser console for WebSocket connection
   - Verify video stream is displaying

## Updating Your Deployment

### Update Backend
```bash
# SSH to Raspberry Pi
ssh admin@raspberry-pi

# Pull latest code
cd videobase-pi
git pull

# Restart server (if running as service)
sudo systemctl restart videobase-server
```

### Update Frontend
- **With GitHub**: Just push to your repository
  ```bash
  git push origin main
  ```
  Cloudflare Pages will automatically rebuild and deploy.

- **With Wrangler**: Build and deploy again
  ```bash
  cd frontend
  npm run build
  wrangler pages deploy dist --project-name=videobase-pi
  ```

## Troubleshooting

### Tunnel not connecting
```bash
# Check tunnel status
cloudflared tunnel info videobase-pi

# View logs
sudo journalctl -u cloudflared -f

# Restart tunnel
sudo systemctl restart cloudflared
```

### WebSocket connection failing
1. Ensure `VITE_WS_URL` matches your tunnel URL exactly
2. Check browser console for errors
3. Verify backend `/ws` endpoint is accessible: `wscat -c wss://videobase.yourdomain.com/ws`

### Build failing on Cloudflare Pages
1. Check build logs in Cloudflare dashboard
2. Ensure Node version is 18+ (set in `.node-version` file)
3. Verify all dependencies are in `package.json`

## Security Recommendations

1. **Change default RTSP credentials** in `server.py`
2. **Enable Cloudflare Access** to restrict who can view the stream
3. **Use strong passwords** for all services
4. **Enable HTTPS only** (Cloudflare does this by default)
5. **Regularly update** all dependencies

## Cost Estimate

- **Cloudflare Tunnel**: FREE
- **Cloudflare Pages**: FREE (500 builds/month)
- **Cloudflare CDN**: FREE
- **Total**: $0/month 🎉

## Support

If you encounter issues:
1. Check the main [README.md](README.md) troubleshooting section
2. Review Cloudflare Tunnel logs
3. Open an issue on GitHub
4. Contact hello@heysalad.io
