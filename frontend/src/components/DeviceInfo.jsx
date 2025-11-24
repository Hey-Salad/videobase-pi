import { useState, useEffect } from 'react';
import { Monitor, Thermometer, Cpu, HardDrive, Clock, Server, ChevronDown, ChevronUp } from 'lucide-react';

const DeviceInfo = () => {
  const [deviceInfo, setDeviceInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    const fetchDeviceInfo = async () => {
      try {
        // Get API URL from environment or derive from WebSocket URL
        let baseUrl = import.meta.env.VITE_API_URL;

        if (!baseUrl) {
          const wsUrl = import.meta.env.VITE_WS_URL || `ws://${window.location.host}/ws`;
          // Convert ws:// to http:// and wss:// to https://
          if (wsUrl.startsWith('ws://')) {
            baseUrl = wsUrl.replace('ws://', 'http://').split('/ws')[0];
          } else if (wsUrl.startsWith('wss://')) {
            baseUrl = wsUrl.replace('wss://', 'https://').split('/ws')[0];
          } else {
            baseUrl = `http://${window.location.host}`;
          }
        }

        const url = `${baseUrl}/device-info`;
        console.log('Fetching device info from:', url);

        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setDeviceInfo(data);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch device info:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    // Fetch immediately
    fetchDeviceInfo();

    // Refresh every 10 seconds
    const interval = setInterval(fetchDeviceInfo, 10000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
          <span className="ml-3 text-gray-300">Loading device info...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4">
        <div className="text-red-400 text-sm">
          Failed to load device info: {error}
        </div>
      </div>
    );
  }

  if (!deviceInfo) {
    return null;
  }

  const getTempColor = (temp) => {
    if (!temp) return 'text-gray-400';
    if (temp < 60) return 'text-green-400';
    if (temp < 75) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getMemoryColor = (percent) => {
    if (!percent) return 'text-gray-400';
    if (percent < 70) return 'text-green-400';
    if (percent < 85) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-white font-semibold flex items-center gap-2">
          <Monitor className="w-5 h-5" />
          <span>Device Information</span>
        </h3>
        <button
          onClick={() => setExpanded((prev) => !prev)}
          className="flex items-center gap-1 text-xs font-semibold text-gray-300 hover:text-white transition-colors"
          aria-expanded={expanded}
        >
          <span>{expanded ? 'Collapse' : 'Expand'}</span>
          {expanded ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>
      </div>

      <div className="mt-2 text-xs text-gray-400 flex flex-wrap gap-4">
        <div className="font-mono">
          IP: <span className="text-white">{deviceInfo.ip_address || 'N/A'}</span>
        </div>
        <div className="font-mono">
          Hostname:{' '}
          <span className="text-white">{deviceInfo.hostname || 'N/A'}</span>
        </div>
        <div className="font-mono">
          CPU Temp:{' '}
          <span className="text-white">
            {deviceInfo.cpu_temp_c !== null ? `${deviceInfo.cpu_temp_c}°C` : 'N/A'}
          </span>
        </div>
      </div>

      {expanded && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mt-4">
          {/* IP Address */}
          <div className="bg-gray-900/60 rounded-lg p-3">
            <div className="text-gray-400 text-xs mb-1">IP Address</div>
            <div className="text-white font-mono font-semibold">
              {deviceInfo.ip_address || 'N/A'}
            </div>
          </div>

          {/* Hostname */}
          <div className="bg-gray-900/60 rounded-lg p-3">
            <div className="text-gray-400 text-xs mb-1">Hostname</div>
            <div className="text-white font-mono font-semibold">
              {deviceInfo.hostname || 'N/A'}
            </div>
          </div>

          {/* CPU Temperature */}
          <div className="bg-gray-900/60 rounded-lg p-3">
            <div className="text-gray-400 text-xs mb-1">CPU Temp</div>
            <div
              className={`font-mono font-semibold ${getTempColor(deviceInfo.cpu_temp_c)}`}
            >
              {deviceInfo.cpu_temp_c !== null ? (
                <>
                  {deviceInfo.cpu_temp_c}°C
                  <span className="text-xs ml-1">({deviceInfo.cpu_temp_f}°F)</span>
                </>
              ) : (
                'N/A'
              )}
            </div>
          </div>

          {/* CPU Load */}
          <div className="bg-gray-900/60 rounded-lg p-3">
            <div className="text-gray-400 text-xs mb-1">CPU Load</div>
            <div className="text-white font-mono font-semibold">
              {deviceInfo.cpu_load !== null ? deviceInfo.cpu_load.toFixed(2) : 'N/A'}
            </div>
          </div>

          {/* Memory Usage */}
          <div className="bg-gray-900/60 rounded-lg p-3">
            <div className="text-gray-400 text-xs mb-1">Memory</div>
            <div
              className={`font-mono font-semibold ${getMemoryColor(
                deviceInfo.memory_used_percent
              )}`}
            >
              {deviceInfo.memory_used_percent !== null ? (
                <>
                  {deviceInfo.memory_used_percent}%
                  <div className="text-xs text-gray-400 mt-1">
                    {deviceInfo.memory_available_mb}MB free
                  </div>
                </>
              ) : (
                'N/A'
              )}
            </div>
          </div>

          {/* Total Memory */}
          <div className="bg-gray-900/60 rounded-lg p-3">
            <div className="text-gray-400 text-xs mb-1">Total RAM</div>
            <div className="text-white font-mono font-semibold">
              {deviceInfo.memory_total_mb !== null ? (
                `${deviceInfo.memory_total_mb} MB`
              ) : (
                'N/A'
              )}
            </div>
          </div>

          {/* Uptime */}
          <div className="bg-gray-900/60 rounded-lg p-3">
            <div className="text-gray-400 text-xs mb-1">Uptime</div>
            <div className="text-white font-mono font-semibold">
              {deviceInfo.uptime || 'N/A'}
            </div>
          </div>

          {/* Platform */}
          <div className="bg-gray-900/60 rounded-lg p-3">
            <div className="text-gray-400 text-xs mb-1">Platform</div>
            <div className="text-white font-mono font-semibold text-xs">
              {deviceInfo.platform} {deviceInfo.machine}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DeviceInfo;
