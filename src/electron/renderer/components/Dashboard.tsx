/**
 * Dashboard component - main control panel
 */
import React, { useState, useEffect } from 'react';

interface DashboardProps {
  isConnected: boolean;
}

interface SessionData {
  session_id?: number;
  meeting_id?: string;
  join_url?: string;
  status?: string;
}

const Dashboard: React.FC<DashboardProps> = ({ isConnected }) => {
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [sessionData, setSessionData] = useState<SessionData | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [zoomValid, setZoomValid] = useState<boolean | null>(null);

  useEffect(() => {
    // Listen for backend messages
    if (window.electronAPI) {
      window.electronAPI.onBackendMessage((message: any) => {
        console.log('Dashboard received:', message);

        if (message.type === 'SESSION_CREATED') {
          setSessionData(message.payload);
          setIsSessionActive(true);
          setIsCreating(false);

          // Show meeting URL if available
          if (message.payload.join_url) {
            console.log('Zoom Meeting URL:', message.payload.join_url);
          }
        } else if (message.type === 'SESSION_ENDED') {
          setIsSessionActive(false);
          setSessionData(null);
        } else if (message.type === 'ZOOM_VALIDATION') {
          setZoomValid(message.payload.valid);
        }
      });

      // Validate Zoom credentials on mount
      window.electronAPI.sendToBackend('VALIDATE_ZOOM', {});
    }
  }, []);

  const handleStartSession = () => {
    if (window.electronAPI && !isCreating) {
      setIsCreating(true);

      window.electronAPI.sendToBackend('CREATE_SESSION', {
        professor_id: 1,
        student_ids: [1, 2, 3, 4, 5],
        topic: 'Introduction to Recursion',
        duration: 20,
        configuration: {
          subject: 'Computer Science',
          difficulty: 'intermediate'
        }
      });
    }
  };

  const handleEndSession = () => {
    if (window.electronAPI && sessionData?.session_id) {
      window.electronAPI.sendToBackend('END_SESSION', {
        session_id: sessionData.session_id
      });
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="flex items-center justify-between">
      {/* Left: Status indicators */}
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

        {zoomValid !== null && (
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                zoomValid ? 'bg-green-400' : 'bg-yellow-400'
              }`}
            />
            <span className="text-white text-xs">
              Zoom {zoomValid ? '✓' : '⚠'}
            </span>
          </div>
        )}

        {isSessionActive && sessionData && (
          <div className="text-white text-xs">
            <span className="text-blue-400">●</span> Session {sessionData.session_id}
            {sessionData.meeting_id && (
              <button
                onClick={() => copyToClipboard(sessionData.join_url || '')}
                className="ml-2 text-blue-300 hover:text-blue-100 underline"
                title="Copy Zoom URL"
              >
                Copy URL
              </button>
            )}
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
            disabled={!isConnected || isCreating || zoomValid === false}
            className="px-4 py-1 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-500 disabled:cursor-not-allowed text-white text-sm rounded-md transition-colors font-medium"
            title={zoomValid === false ? 'Zoom credentials not configured' : 'Start new session'}
          >
            {isCreating ? 'Creating...' : 'Start Session'}
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
