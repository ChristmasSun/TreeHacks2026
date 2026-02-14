/**
 * Session Monitor Component
 * Displays real-time status of all breakout rooms and avatars
 */
import React, { useState, useEffect } from 'react';

interface RoomStatus {
  room_id: number;
  zoom_room_id: string;
  student_id: number;
  student_name: string;
  avatar_session_id: string | null;
  status: string;
}

interface SessionMonitorProps {
  sessionId: number | null;
  rooms: RoomStatus[];
}

const SessionMonitor: React.FC<SessionMonitorProps> = ({ sessionId, rooms }) => {
  const [expandedRoom, setExpandedRoom] = useState<number | null>(null);

  if (!sessionId || rooms.length === 0) {
    return (
      <div className="text-white/60 text-sm text-center py-4">
        No active session
      </div>
    );
  }

  const getStatusColor = (status: string, hasAvatar: boolean) => {
    if (!hasAvatar) return 'bg-yellow-500';

    switch (status) {
      case 'active':
        return 'bg-green-500';
      case 'pending':
        return 'bg-yellow-500';
      case 'error':
        return 'bg-red-500';
      case 'completed':
        return 'bg-gray-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusText = (status: string, hasAvatar: boolean) => {
    if (!hasAvatar) return 'No Avatar';

    switch (status) {
      case 'active':
        return 'Active';
      case 'pending':
        return 'Starting...';
      case 'error':
        return 'Error';
      case 'completed':
        return 'Ended';
      default:
        return status;
    }
  };

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-white text-sm font-semibold">
          Breakout Rooms ({rooms.length})
        </h3>
        <div className="flex gap-3 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-green-500"></div>
            <span className="text-white/70">Active</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
            <span className="text-white/70">Pending</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-red-500"></div>
            <span className="text-white/70">Error</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
        {rooms.map((room) => {
          const hasAvatar = !!room.avatar_session_id;
          const statusColor = getStatusColor(room.status, hasAvatar);
          const statusText = getStatusText(room.status, hasAvatar);
          const isExpanded = expandedRoom === room.room_id;

          return (
            <div
              key={room.room_id}
              className="glass-dark rounded-lg p-3 cursor-pointer hover:bg-white/5 transition-colors"
              onClick={() => setExpandedRoom(isExpanded ? null : room.room_id)}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-white text-xs font-medium truncate">
                  {room.student_name}
                </span>
                <div
                  className={`w-2 h-2 rounded-full ${statusColor} ${
                    room.status === 'active' ? 'animate-pulse' : ''
                  }`}
                  title={statusText}
                />
              </div>

              <div className="text-white/60 text-xs space-y-1">
                <div>Room {room.zoom_room_id.slice(-4)}</div>
                <div className="flex items-center gap-1">
                  <span className={hasAvatar ? 'text-green-400' : 'text-yellow-400'}>
                    {hasAvatar ? '🤖' : '⚠️'}
                  </span>
                  <span>{statusText}</span>
                </div>
              </div>

              {isExpanded && room.avatar_session_id && (
                <div className="mt-2 pt-2 border-t border-white/10 text-xs text-white/50">
                  Session: {room.avatar_session_id.slice(0, 8)}...
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Summary */}
      <div className="mt-3 flex gap-4 text-xs text-white/60">
        <span>
          Active: {rooms.filter((r) => r.status === 'active').length}
        </span>
        <span>
          Avatars: {rooms.filter((r) => r.avatar_session_id).length}/{rooms.length}
        </span>
      </div>
    </div>
  );
};

export default SessionMonitor;
