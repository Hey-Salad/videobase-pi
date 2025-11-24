import { useState } from 'react';
import { Cpu } from 'lucide-react';
import CameraView from './CameraView';
import DeviceInfo from './DeviceInfo';

const MultiCameraView = () => {
  const [aiSource, setAiSource] = useState('hailo'); // 'hailo' or 'recamera'

  const cameras = [
    { id: 'camera1', name: 'Camera 1' },
    { id: 'camera2', name: 'Camera 2' },
    { id: 'camera3', name: 'Camera 3' },
  ];

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6">
      {/* Device Information */}
      <DeviceInfo />

      {/* AI Source Toggle */}
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-white font-semibold flex items-center gap-2">
            <Cpu className="w-5 h-5" />
            <span>AI Inference Source</span>
          </h3>
          <select
            value={aiSource}
            onChange={(event) => setAiSource(event.target.value)}
            className="bg-gray-900/70 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-400"
          >
            <option value="hailo">Hailo-8L</option>
            <option value="recamera">reCamera</option>
          </select>
        </div>
        <div className="text-sm text-gray-400">
          {aiSource === 'hailo' ? (
            <p>
              Using <span className="text-blue-400 font-semibold">Hailo-8L NPU</span> for hardware-accelerated
              object detection. Make sure Hailo inference clients are running.
            </p>
          ) : (
            <p>
              Using <span className="text-green-400 font-semibold">reCamera</span> on-device AI.
              Connect your reCamera/Node-RED flow to the AI WebSocket endpoint.
            </p>
          )}
        </div>
      </div>

      {/* Grid Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cameras.map((camera) => (
          <CameraView
            key={camera.id}
            cameraId={camera.id}
            name={camera.name}
            aiSource={aiSource}
          />
        ))}
      </div>
    </div>
  );
};

export default MultiCameraView;
