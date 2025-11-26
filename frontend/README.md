# Videobase Pi Frontend

React.js frontend for the Videobase Pi streaming application.

## Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```

The dev server will start on `http://localhost:3000`

## Building for Production

```bash
npm run build
```

The build output will be in the `dist/` directory.

## Environment Variables

Copy `.env.example` to `.env` and configure:

- `VITE_WS_URL` - WebSocket URL for the backend (e.g., `wss://your-tunnel.trycloudflare.com/ws`)

## Deployment to Cloudflare Pages

### Via Git Integration (Recommended)

1. Push your code to GitHub
2. Go to [Cloudflare Pages](https://pages.cloudflare.com/)
3. Create a new project
4. Connect your GitHub repository
5. Configure build settings:
   - **Build command**: `npm run build`
   - **Build output directory**: `dist`
   - **Root directory**: `frontend`
6. Add environment variable:
   - `VITE_WS_URL`: Your Cloudflare Tunnel WebSocket URL

### Via Wrangler CLI

```bash
# Install Wrangler
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Deploy
npm run build
wrangler pages deploy dist --project-name=videobase-pi
```

## Configuration

The app automatically detects the WebSocket URL:
- In development: Uses `ws://localhost:8000/ws` or value from `VITE_WS_URL`
- In production: Uses `wss://` with the current hostname or `VITE_WS_URL`

Make sure to set `VITE_WS_URL` to your Cloudflare Tunnel URL in production.
