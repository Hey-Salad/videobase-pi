<img src="https://raw.githubusercontent.com/Hey-Salad/.github/refs/heads/main/HeySalad%20Logo%20%2B%20Tagline%20Black.svg" alt="HeySalad Logo" width="400"/>

# reCamera Video Streamer 🎥

## Powered by Seeedstudio's reCamera & Raspberry Pi

A powerful RTSP video streaming solution that combines the capabilities of reCamera with an intuitive web interface. Built on GStreamer and Gradio, this project provides a seamless way to view and manage your reCamera stream.

![ReCamera View](screenshots/Bildschirmfoto%202025-02-05%20um%2005.07.47.png)
![Raspberry Pi Terminal](screenshots/Bildschirmfoto%202025-02-05%20um%2005.00.50.png)
![Raspberry Pi Desktop](screenshots/Bildschirmfoto%202025-02-05%20um%2005.00.17.png)
![Laptop View](screenshots/Bildschirmfoto%202025-02-05%20um%2004.53.26.png)

### ⚡ Key Features

- 🎮 Real-time RTSP streaming
- 🖥️ Clean web interface powered by Gradio
- 📊 Live FPS monitoring
- 🤖 OpenAI GPT-OSS analysis button below each camera stream
- 🧠 Switch between Hailo-8L and reCamera inference sources with the UI dropdown
- 📡 Device info panel is collapsible, surfacing a quick summary and full metrics grid
- 🔄 Automatic reconnection
- 🌐 Network-wide accessibility
- 🚀 Low-latency streaming
- 💻 Cross-platform compatibility

## 🛠️ Prerequisites

- Python 3.7+
- GStreamer and plugins
- Raspberry Pi (recommended)
- reCamera device

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/Hey-Salad/recamera-streamer.git
cd recamera-streamer

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Install GStreamer plugins (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y \\
    gstreamer1.0-tools \\
    gstreamer1.0-plugins-base \\
    gstreamer1.0-plugins-good \\
    gstreamer1.0-plugins-bad \\
    gstreamer1.0-plugins-ugly \\
    gstreamer1.0-libav
```

## 🚀 Quick Start

1. Connect your reCamera to your network
2. Update the RTSP URL if needed in `streamer.py`
3. Run the streamer:
```bash
python streamer.py
```
4. Open your browser and navigate to:
   - Local: `http://localhost:7860`
   - Network: `http://[YOUR_PI_IP]:7860`

## 🔧 Configuration

The default configuration works with reCamera's standard settings:
- RTSP URL: `rtsp://admin:admin@192.168.42.1:554/live`
- Port: 7860
- Video Format: H.264

### Frontend (.env)
```
VITE_WS_URL=ws://localhost:9200/ws
VITE_API_URL=http://localhost:9200
VITE_GPT_BACKEND_URL=http://localhost:5000
```

Leaving these values empty lets the UI derive the backend host from the current page, which is handy when the React app and backend run on the same host (e.g., local dev or Cloudflare Pages).

### GPT Backend (.env)
Use the Hugging Face-powered GPT-OSS service located at `/home/admin/heysalad-gpt-oss-kiosk-backend`. Launch the Flask app before clicking the OpenAI analysis button.
```
cd /home/admin/heysalad-gpt-oss-kiosk-backend
source venv/bin/activate
python heysalad_backend.py
```
Set `VITE_GPT_BACKEND_URL` to wherever `heysalad_backend.py` listens (default `http://localhost:5000`) so the UI can hit `/api/ai/recommendation`.

## 📱 Accessing the Stream

- **Local Network**: `http://[YOUR_PI_IP]:7860`
- **Same Device**: `http://localhost:7860`
- **Public Access**: Use the provided share link (if enabled)

## 🛟 Troubleshooting

1. **No Video Stream**:
   - Verify reCamera is powered on
   - Check network connectivity
   - Confirm RTSP URL and credentials

2. **Performance Issues**:
   - Reduce network latency
   - Check CPU usage
   - Verify GStreamer installation

## 📚 Technical Details

Built using:
- GStreamer: Media pipeline
- Gradio: Web interface
- Python: Core logic
- OpenH264: Video decoding

## 🤝 Contributing

We welcome contributions! Please:
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to your branch
5. Create a Pull Request

## ❤️ Support

If you find this project useful, consider:

<a href="https://www.buymeacoffee.com/heysalad"><img src="https://github.com/Hey-Salad/.github/blob/a4cbf4a12cca3477fdbfe55520b3fdfe0e0f35a4/bmc-button.png" alt="Buy Me A Coffee" width="200"/></a>

## 📫 Contact

- Website: [heysalad.io](https://heysalad.io)
- Email: hello@heysalad.io

## 📄 License

MIT License

Copyright (c) 2024 HeySalad

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---
Made with ❤️ by HeySalad
