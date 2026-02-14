/**
 * Dashboard component - main control panel
 */
import React, { useState } from 'react';

interface DashboardProps {
  isConnected: boolean;
}

const Dashboard: React.FC<DashboardProps> = ({ isConnected }) => {
  const [isSessionActive, setIsSessionActive] = useState(false);

  const handleStartSession = () => {
    if (window.electronAPI) {
      window.electronAPI.sendToBackend('CREATE_SESSION', {
        professor_id: 1,
        meeting_id: 'test-meeting-123',
        student_ids: [1, 2, 3],
        configuration: {
          duration: 20,
          topic: 'Recursion'
        }
      });
      setIsSessionActive(true);
    }
  };

  const handleEndSession = () => {
    if (window.electronAPI) {
      window.electronAPI.sendToBackend('END_SESSION', {
        session_id: 1
      });
      setIsSessionActive(false);
    }
  };

  return (
    <div className="flex items-center justify-between">
      {/* Left: Status indicator */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-400' : 'bg-red-400'
            } animate-pulse`}
          />
          <span className="text-white text-sm font-medium">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>

        {isSessionActive && (
          <div className="text-white text-sm">
            <span className="text-blue-400">●</span> Session Active
          </div>
        )}
      </div>

      {/* Center: App title */}
      <div className="text-white text-sm font-semibold tracking-wide">
        AI Professor Assistant
      </div>

      {/* Right: Action buttons */}
      <div className="flex items-center gap-2">
        {!isSessionActive ? (
          <button
            onClick={handleStartSession}
            disabled={!isConnected}
            className="px-4 py-1 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-500 text-white text-sm rounded-md transition-colors font-medium"
          >
            Start Session
          </button>
        ) : (
          <button
            onClick={handleEndSession}
            className="px-4 py-1 bg-red-500 hover:bg-red-600 text-white text-sm rounded-md transition-colors font-medium"
          >
            End Session
          </button>
        )}

        {/* Window controls */}
        <button
          onClick={() => window.electronAPI?.minimizeWindow()}
          className="w-6 h-6 flex items-center justify-center hover:bg-white/10 rounded text-white/70 hover:text-white transition-colors"
          title="Minimize"
        >
          −
        </button>
        <button
          onClick={() => window.electronAPI?.closeWindow()}
          className="w-6 h-6 flex items-center justify-center hover:bg-red-500 rounded text-white/70 hover:text-white transition-colors"
          title="Close"
        >
          ×
        </button>
      </div>
    </div>
  );
};

export default Dashboard;
