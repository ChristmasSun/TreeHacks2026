/**
 * Main App component with frosted glass UI
 */
import React, { useState, useEffect } from 'react';
import Dashboard from './components/Dashboard';
import SessionMonitor from './components/SessionMonitor';

interface RoomStatus {
  room_id: number;
  zoom_room_id: string;
  student_id: number;
  student_name: string;
  avatar_session_id: string | null;
  status: string;
}

const App: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [rooms, setRooms] = useState<RoomStatus[]>([]);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    // Listen for backend messages
    if (window.electronAPI) {
      window.electronAPI.onBackendMessage((message: any) => {
        console.log('Received from backend:', message);

        if (message.type === 'PONG') {
          setIsConnected(true);
        } else if (message.type === 'SESSION_CREATED') {
          setActiveSessionId(message.payload.session_id);
          setRooms(message.payload.breakout_rooms || []);
          setIsExpanded(true);
        } else if (message.type === 'SESSION_ENDED') {
          setActiveSessionId(null);
          setRooms([]);
          setIsExpanded(false);
        } else if (message.type === 'SESSION_STATUS') {
          setRooms(message.payload.breakout_rooms || []);
        }
      });
    }
  }, []);

  return (
    <div className="w-full h-screen select-none">
      {/* Frosted glass container */}
      <div className="glass-dark w-full h-full rounded-lg shadow-2xl overflow-hidden flex flex-col">
        {/* Drag region for window movement */}
        <div className="drag-region h-2 w-full flex-shrink-0"></div>

        {/* Main content */}
        <div className="no-drag px-4 pb-2 flex-shrink-0">
          <Dashboard isConnected={isConnected} />
        </div>

        {/* Session Monitor - Expandable */}
        {isExpanded && (
          <div className="no-drag px-4 pb-3 flex-1 overflow-y-auto">
            <SessionMonitor sessionId={activeSessionId} rooms={rooms} />
          </div>
        )}

        {/* Expand/Collapse Button */}
        {activeSessionId && (
          <div className="no-drag px-4 pb-2 flex-shrink-0 flex justify-center">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-white/50 hover:text-white text-xs transition-colors"
            >
              {isExpanded ? '▲ Hide Details' : '▼ Show Details'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default App;
