import { useState, useEffect, useRef, useMemo } from 'react';
import { Eye, EyeOff } from 'lucide-react';

const DEFAULT_FRAME_DIMENSION = 1;

const inferFrameSize = (source) => {
  // Check for resolution array [width, height]
  if (Array.isArray(source?.resolution) && source.resolution.length >= 2) {
    return {
      width: source.resolution[0],
      height: source.resolution[1],
    };
  }

  return {
    width: source?.frame_width ?? source?.image_width ?? source?.width ?? DEFAULT_FRAME_DIMENSION,
    height: source?.frame_height ?? source?.image_height ?? source?.height ?? DEFAULT_FRAME_DIMENSION,
  };
};

const normalizeValue = (value, dimension) => {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return null;
  }

  const safeDimension = typeof dimension === 'number' && dimension > 0 ? dimension : DEFAULT_FRAME_DIMENSION;

  if (safeDimension > 1) {
    return Math.min(Math.max(value / safeDimension, 0), 1);
  }

  if (value <= 1) {
    return Math.min(Math.max(value, 0), 1);
  }

  return Math.min(Math.max(value, 0), 1);
};

const normalizeBBox = (bbox, frameSize) => {
  if (!bbox) {
    return null;
  }

  const x = normalizeValue(bbox.x, frameSize.width);
  const y = normalizeValue(bbox.y, frameSize.height);
  const width = normalizeValue(Math.max(bbox.width, 0), frameSize.width);
  const height = normalizeValue(Math.max(bbox.height, 0), frameSize.height);

  if ([x, y, width, height].some((value) => value === null)) {
    return null;
  }

  return { x, y, width, height };
};

const extractBoxFromCandidate = (candidate) => {
  if (!candidate) {
    return null;
  }

  const source =
    candidate.bbox ??
    candidate.box ??
    candidate.rect ??
    candidate.region ??
    candidate;

  if (Array.isArray(source)) {
    if (source.length >= 4 && source.slice(0, 4).every((num) => typeof num === 'number')) {
      return {
        x: source[0],
        y: source[1],
        width: source[2],
        height: source[3],
      };
    }

    return null;
  }

  if (typeof source === 'object' && source !== null) {
    const x =
      source.x ??
      source.left ??
      source.x_min ??
      source.x1 ??
      source.cx ??
      source.center_x;
    const y =
      source.y ??
      source.top ??
      source.y_min ??
      source.y1 ??
      source.cy ??
      source.center_y;

    let width = source.width ?? source.w;
    let height = source.height ?? source.h;

    const x2 = source.x2 ?? source.x_max ?? source.right;
    const y2 = source.y2 ?? source.y_max ?? source.bottom;

    if (x != null && width == null && x2 != null) {
      width = x2 - x;
    }
    if (y != null && height == null && y2 != null) {
      height = y2 - y;
    }

    if (
      [x, y, width, height].every(
        (value) => typeof value === 'number' && !Number.isNaN(value)
      )
    ) {
      return { x, y, width, height };
    }
  }

  return null;
};

const buildOpenAIPrompt = ({ cameraId, name, aiSource, detections, aiTimestamp }) => {
  const candidateLabels = detections
    .map((detection) => detection.label || detection?.box?.label || 'object')
    .filter(Boolean);

  const detectionList = candidateLabels.slice(0, 5);
  const detectionText = detectionList.length
    ? `Objects seen: ${detectionList.join(', ')}`
    : 'No clearly labeled objects detected';

  let timestampDescription = 'now';
  if (aiTimestamp) {
    const parsed = new Date(aiTimestamp);
    if (!Number.isNaN(parsed.getTime())) {
      timestampDescription = parsed.toLocaleString();
    }
  }

  return `Camera ${name} (${cameraId}) via ${
    aiSource === 'hailo' ? 'Hailo-8L' : 'reCamera'
  } at ${timestampDescription}. ${detectionText}. Describe what is happening and suggest a short next action.`;
};

const OpenAIIcon = ({ className }) => (
  <svg viewBox="0 0 24 24" className={className} role="img" aria-label="OpenAI">
    <path
      d="M12 2 19 5v7l-3 1.5V18l-2 1-2-1v-4.5L5 12V5Z"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinejoin="round"
    />
    <path
      d="M18 6c.4.93.6 1.94.6 2.95 0 3.15-2.5 5.7-5.6 5.7S7.4 12.1 7.4 9c0-.61.11-1.2.34-1.76"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.3"
      strokeLinecap="round"
    />
    <circle cx="12" cy="12" r="5.5" fill="none" stroke="currentColor" strokeWidth="1" />
  </svg>
);

const buildDetectionsFromInference = (inference = {}) => {
  const boxes = Array.isArray(inference.boxes) ? inference.boxes : null;
  if (!boxes || boxes.length === 0) {
    return [];
  }

  const frameSize = inferFrameSize(inference);

  return boxes
    .map((box, index) => {
      let bbox = null;

      if (Array.isArray(box) && box.length >= 4) {
        bbox = {
          x: box[0],
          y: box[1],
          width: box[2],
          height: box[3],
        };
      } else if (typeof box === 'object' && box !== null) {
        bbox = extractBoxFromCandidate(box);
      }

      const normalizedBox = normalizeBBox(bbox, frameSize);
      if (!normalizedBox) {
        return null;
      }

      const label = (inference.labels?.[index]) || box?.label || box?.name || `object-${index + 1}`;
      const confidence = typeof box?.[4] === 'number' ? box[4] : box?.confidence ?? box?.score ?? null;

      return {
        label,
        confidence,
        box: normalizedBox,
      };
    })
    .filter(Boolean);
};

const parseDetections = (inferenceSource) => {
  if (!inferenceSource) {
    return [];
  }

  const inferenceObjects = buildDetectionsFromInference(inferenceSource);
  if (inferenceObjects.length) {
    return inferenceObjects;
  }

  const candidates = Array.isArray(inferenceSource)
    ? inferenceSource
    : Array.isArray(inferenceSource.detections)
    ? inferenceSource.detections
    : Array.isArray(inferenceSource.objects)
    ? inferenceSource.objects
    : [];

  if (!Array.isArray(candidates)) {
    return [];
  }

  const frameSize = inferFrameSize(inferenceSource);

  return candidates
    .map((candidate, index) => {
      const bbox = extractBoxFromCandidate(candidate);
      const normalizedBox = normalizeBBox(bbox, frameSize);
      if (!normalizedBox) {
        return null;
      }

      const label =
        candidate?.label ??
        candidate?.name ??
        candidate?.class ??
        candidate?.category ??
        `object-${index + 1}`;

      const confidence =
        candidate?.confidence ??
        candidate?.score ??
        candidate?.probability ??
        candidate?.confidence_score ??
        null;

      return {
        label,
        confidence,
        box: normalizedBox,
      };
    })
    .filter(Boolean);
};

const CameraView = ({ cameraId, name, aiSource = 'hailo' }) => {
  const [connected, setConnected] = useState(false);
  const [frameCount, setFrameCount] = useState(0);
  const [fps, setFps] = useState(0);
  const [error, setError] = useState(null);
  const [aiData, setAiData] = useState(null);
  const [isVideoVisible, setIsVideoVisible] = useState(true);
  const imgRef = useRef(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisStatus, setAnalysisStatus] = useState('idle');
  const [analysisError, setAnalysisError] = useState(null);
  const wsRef = useRef(null);
  const canvasRef = useRef(null);
  const [canvasSize, setCanvasSize] = useState({ width: 0, height: 0 });
  const fpsCounterRef = useRef({ count: 0, lastTime: Date.now() });
  const gptBackendUrl = import.meta.env.VITE_GPT_BACKEND_URL || 'http://localhost:5000';

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${cameraId}`;

    const connectWebSocket = () => {
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          setConnected(true);
          setError(null);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === 'frame' && data.data) {
              if (imgRef.current) {
                imgRef.current.src = `data:image/jpeg;base64,${data.data}`;
              }

              setFrameCount(data.frame_count);

              const now = Date.now();
              fpsCounterRef.current.count++;
              const elapsed = (now - fpsCounterRef.current.lastTime) / 1000;

              if (elapsed >= 1) {
                setFps(Math.round(fpsCounterRef.current.count / elapsed));
                fpsCounterRef.current.count = 0;
                fpsCounterRef.current.lastTime = now;
              }

              setAiData(data.ai_data || null);
            }
          } catch (err) {
            console.error(`[${cameraId}] Error processing message:`, err);
          }
        };

        ws.onerror = (err) => {
          console.error(`[${cameraId}] WebSocket error:`, err);
          setError('Connection error');
        };

        ws.onclose = () => {
          setConnected(false);
          setTimeout(() => connectWebSocket(), 3000);
        };
      } catch (err) {
        console.error(`[${cameraId}] Error creating WebSocket:`, err);
        setError('Failed to connect');
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [cameraId]);

  useEffect(() => {
    setAnalysisResult(null);
    setAnalysisStatus('idle');
    setAnalysisError(null);
  }, [cameraId, aiSource]);

  const inferenceSource = useMemo(() => {
    if (!aiData?.payload) {
      return null;
    }

    if (aiData.payload.inference) {
      return aiData.payload.inference;
    }

    if (aiData.payload.data) {
      return aiData.payload.data;
    }

    return aiData.payload;
  }, [aiData]);
  const detections = useMemo(
    () => parseDetections(inferenceSource),
    [inferenceSource]
  );

  const handleOpenAIAnalysis = async () => {
    if (analysisStatus === 'loading') {
      return;
    }

    setAnalysisStatus('loading');
    setAnalysisError(null);
    setAnalysisResult(null);

    const prompt = buildOpenAIPrompt({
      cameraId,
      name,
      aiSource,
      detections,
      aiTimestamp: aiData?.timestamp,
    });

    try {
      const response = await fetch(`${gptBackendUrl}/api/ai/recommendation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt,
          reasoning_level: 'medium',
        }),
      });

      if (!response.ok) {
        throw new Error(`Status ${response.status}`);
      }

      const data = await response.json();
      setAnalysisResult(data);
      setAnalysisStatus('done');
    } catch (err) {
      console.error(`[${cameraId}] OpenAI analysis failed`, err);
      setAnalysisError(err?.message || 'Unknown error');
      setAnalysisStatus('error');
    }
  };

  const aiSummary = useMemo(() => {
    if (!aiData) {
      return null;
    }

    const previewSource = inferenceSource ?? aiData.payload;
    const preview =
      typeof previewSource === 'object' && previewSource !== null
        ? JSON.stringify(previewSource, null, 2)
        : String(previewSource ?? '');

    return {
      timestamp: aiData.timestamp,
      count: detections.length,
      preview,
    };
  }, [aiData, detections, inferenceSource]);

  useEffect(() => {
    const img = imgRef.current;
    if (!img) {
      return undefined;
    }

    const updateSize = () => {
      const rect = img.getBoundingClientRect();
      if (rect.width && rect.height) {
        setCanvasSize({ width: rect.width, height: rect.height });
      }
    };

    updateSize();

    if (typeof window === 'undefined') {
      return undefined;
    }

    if (typeof ResizeObserver !== 'undefined') {
      const observer = new ResizeObserver(updateSize);
      observer.observe(img);
      return () => observer.disconnect();
    }

    const handleResize = () => updateSize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [connected]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return;
    }

    const { width, height } = canvasSize;
    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);

    if (!width || !height) {
      return;
    }

    detections.forEach((detection) => {
      const { box } = detection;
      const x = box.x * width;
      const y = box.y * height;
      const w = box.width * width;
      const h = box.height * height;

      ctx.strokeStyle = 'rgba(16,185,129,0.95)';
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, w, h);

      const confidence =
        typeof detection.confidence === 'number'
          ? ` ${(detection.confidence * 100).toFixed(0)}%`
          : '';
      const text = `${detection.label || 'object'}${confidence}`.trim();
      ctx.fillStyle = 'rgba(16,185,129,0.95)';
      ctx.font = '11px "IBM Plex Mono", Menlo, monospace';
      const textX = Math.min(Math.max(x, 4), width - 4);
      const textY = y > 12 ? y - 6 : Math.min(y + 12, height - 4);
      ctx.fillText(text, textX, textY);
    });
  }, [detections, canvasSize]);

  useEffect(() => {
    if (aiData) {
      console.debug(`[${cameraId}] aiData`, aiData);
    }
  }, [aiData, cameraId]);

  useEffect(() => {
    if (detections.length) {
      console.debug(`[${cameraId}] drawing ${detections.length} box(es)`);
    }
  }, [detections, cameraId]);

  return (
    <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg overflow-hidden">
      {/* Camera Header */}
      <div className="p-3 bg-gray-900/50 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <h3 className="text-white font-semibold">{name}</h3>
          <div className="flex items-center gap-3 text-sm">
            <button
              onClick={() => setIsVideoVisible(!isVideoVisible)}
              className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-white rounded text-xs transition-colors flex items-center gap-1"
              title={isVideoVisible ? 'Hide video' : 'Show video'}
            >
              {isVideoVisible ? (
                <>
                  <EyeOff className="w-3 h-3" />
                  <span>Hide</span>
                </>
              ) : (
                <>
                  <Eye className="w-3 h-3" />
                  <span>Show</span>
                </>
              )}
            </button>
            <div className="flex items-center gap-1">
              <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
              <span className="text-gray-300">{connected ? 'Live' : 'Offline'}</span>
            </div>
            <span className="text-gray-400 font-mono">{fps} FPS</span>
            <span className="text-gray-400 font-mono text-xs">#{frameCount}</span>
          </div>
        </div>
      </div>

      {/* Video Display */}
      {isVideoVisible && (
        <div className="relative bg-black aspect-video">
          <img
            ref={imgRef}
            alt={`${name} Stream`}
            className="w-full h-full object-contain"
          />
          <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none z-10" />
          {!connected && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 z-20">
              <div className="text-center">
                {error ? (
                  <div className="text-red-400">{error}</div>
                ) : (
                  <>
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-2"></div>
                    <p className="text-white text-sm">Connecting...</p>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="mt-2 space-y-2">
        <button
          type="button"
          onClick={handleOpenAIAnalysis}
          disabled={analysisStatus === 'loading'}
          className={`w-full flex items-center justify-center gap-2 text-sm font-semibold rounded-lg px-3 py-2 transition ${
            analysisStatus === 'loading'
              ? 'bg-blue-500/60 text-white cursor-wait'
              : 'bg-blue-600 text-white hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-400'
          }`}
        >
          <OpenAIIcon className="w-4 h-4" />
          <span>{analysisStatus === 'loading' ? 'Analyzing…' : 'OpenAI Analysis'}</span>
        </button>
        {analysisStatus === 'loading' && (
          <p className="text-xs text-gray-400">Requesting insight from GPT-OSS…</p>
        )}
        {analysisStatus === 'error' && analysisError && (
          <p className="text-xs text-red-400">Failed: {analysisError}</p>
        )}
        {analysisResult && (
          <div className="space-y-1 text-sm">
            <p className="text-gray-200">{analysisResult.recommendation}</p>
            <p className="text-xs text-gray-400">
              Source: {analysisResult.source || 'unknown'} · Model: {analysisResult.model || 'unknown'}
            </p>
          </div>
        )}
      </div>

      <div className="mt-3 bg-gray-900/60 border border-gray-800 p-3 rounded-lg text-xs text-gray-300 font-mono">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <span>
              AI Status:{' '}
              {aiSummary ? (
                <span className="text-emerald-400">Live ({aiSummary.count})</span>
              ) : (
                <span className="text-yellow-400">Waiting</span>
              )}
            </span>
            {aiSummary && inferenceSource?.perf && inferenceSource.perf[0] && (
              <span className={aiSource === 'hailo' ? 'text-blue-400' : 'text-green-400'}>
                {aiSource === 'hailo' ? 'Hailo' : 'reCamera'}: {inferenceSource.perf[0][1]}ms
              </span>
            )}
          </div>
          <span>
            {aiSummary ? new Date(aiSummary.timestamp).toLocaleTimeString() : '--:--:--'}
          </span>
        </div>
        {aiSummary ? (
          <pre className="max-h-32 overflow-auto whitespace-pre-wrap">{aiSummary.preview}</pre>
        ) : (
          <p>No AI payload received yet.</p>
        )}
      </div>
    </div>
  );
};

export default CameraView;
