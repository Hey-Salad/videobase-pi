import { useState, useEffect, useRef } from 'react';

const VideoStream = () => {
  const [connected, setConnected] = useState(false);
  const [frameCount, setFrameCount] = useState(0);
  const [fps, setFps] = useState(0);
  const [error, setError] = useState(null);
  const imgRef = useRef(null);
  const wsRef = useRef(null);
  const fpsCounterRef = useRef({ count: 0, lastTime: Date.now() });

  useEffect(() => {
    // Get WebSocket URL from environment or default to current host
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = import.meta.env.VITE_WS_URL || `${protocol}//${window.location.host}/ws`;

    console.log('Connecting to WebSocket:', wsUrl);

    const connectWebSocket = () => {
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('WebSocket connected');
          setConnected(true);
          setError(null);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === 'frame' && data.data) {
              // Update image
              if (imgRef.current) {
                imgRef.current.src = `data:image/jpeg;base64,${data.data}`;
              }

              // Update frame count
              setFrameCount(data.frame_count);

              // Calculate FPS
              const now = Date.now();
              fpsCounterRef.current.count++;
              const elapsed = (now - fpsCounterRef.current.lastTime) / 1000;

              if (elapsed >= 1) {
                setFps(Math.round(fpsCounterRef.current.count / elapsed));
                fpsCounterRef.current.count = 0;
                fpsCounterRef.current.lastTime = now;
              }
            }
          } catch (err) {
            console.error('Error processing message:', err);
          }
        };

        ws.onerror = (err) => {
          console.error('WebSocket error:', err);
          setError('Connection error. Please check if the server is running.');
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected');
          setConnected(false);

          // Attempt to reconnect after 3 seconds
          setTimeout(() => {
            console.log('Attempting to reconnect...');
            connectWebSocket();
          }, 3000);
        };
      } catch (err) {
        console.error('Error creating WebSocket:', err);
        setError('Failed to connect to video stream');
      }
    };

    connectWebSocket();

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Status Bar */}
      <div className="mb-4 flex items-center justify-between bg-gray-800/50 backdrop-blur-sm rounded-lg p-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
            <span className="text-white font-medium">
              {connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <div className="text-gray-300">
            <span className="font-mono">FPS: {fps}</span>
          </div>
          <div className="text-gray-300">
            <span className="font-mono">Frames: {frameCount}</span>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 bg-red-500/10 border border-red-500/50 rounded-lg p-4">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Video Display */}
      <div className="relative bg-black rounded-lg overflow-hidden shadow-2xl">
        <img
          ref={imgRef}
          alt="Video Stream"
          className="w-full h-auto"
          style={{ minHeight: '400px', objectFit: 'contain' }}
        />
        {!connected && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
              <p className="text-white">Connecting to stream...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoStream;
