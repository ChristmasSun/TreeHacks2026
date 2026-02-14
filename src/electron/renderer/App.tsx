/**
 * Student App - Breakout Room AI Tutor
 * 
 * Runs invisibly until professor triggers breakout rooms,
 * then expands to show personalized HeyGen avatar tutor.
 */
import React, { useState, useEffect, useCallback } from 'react';
import HeyGenAvatar from './components/HeyGenAvatar';

type WindowState = 'hidden' | 'minimized' | 'expanded';

interface AvatarSession {
  sessionId: string;
  livekitUrl: string;
  accessToken: string;
}

const App: React.FC = () => {
  const [windowState, setWindowState] = useState<WindowState>('minimized');
  const [isConnected, setIsConnected] = useState(false);
  const [studentName, setStudentName] = useState('');
  const [studentEmail, setStudentEmail] = useState('');
  const [isRegistered, setIsRegistered] = useState(false);
  const [isWaiting, setIsWaiting] = useState(false);
  const [avatarSession, setAvatarSession] = useState<AvatarSession | null>(null);
  const [meetingStatus, setMeetingStatus] = useState<string>('');

  // Register student with backend
  const registerStudent = useCallback(() => {
    if (!studentName.trim() || !studentEmail.trim()) return;
    
    const student = {
      name: studentName.trim(),
      email: studentEmail.trim(),
    };
    
    window.electronAPI?.sendToBackend('REGISTER_STUDENT', student);
    
    // Notify main process so it knows the student name for avatar window
    window.electronAPI?.studentRegistered(student);
    
    setIsRegistered(true);
    setIsWaiting(true);
  }, [studentName, studentEmail]);

  // Close avatar view
  const closeAvatar = useCallback(() => {
    setAvatarSession(null);
    window.electronAPI?.setWindowState('minimized');
  }, []);

  useEffect(() => {
    // Listen for backend messages
    if (window.electronAPI) {
      window.electronAPI.onBackendMessage((message: any) => {
        console.log('📨 Backend message:', message);

        switch (message.type) {
          case 'PONG':
            setIsConnected(true);
            break;
            
          case 'STUDENT_REGISTERED':
            setIsRegistered(true);
            setIsWaiting(true);
            break;
            
          case 'MEETING_JOINED':
            setMeetingStatus('In meeting - waiting for breakout...');
            break;
            
          case 'BREAKOUT_STARTED':
          case 'BREAKOUT_ROOM_ASSIGNED':
            // Professor triggered breakout rooms!
            // Avatar window is opened by main process, just update waiting state
            console.log('🚀 Breakout room assigned!', message.payload);
            setIsWaiting(false);
            setMeetingStatus('AI Tutor session started!');
            break;
            
          case 'SESSION_ENDED':
            setAvatarSession(null);
            setIsWaiting(true);
            setMeetingStatus('Session ended');
            window.electronAPI?.setWindowState('minimized');
            break;
            
          case 'AVATAR_CREATED':
            // Backend created avatar session for us
            setAvatarSession({
              sessionId: message.payload.session_id,
              livekitUrl: message.payload.livekit_url,
              accessToken: message.payload.access_token,
            });
            break;
        }
      });

      // Listen for window state changes
      window.electronAPI.onWindowStateChanged((state: string) => {
        setWindowState(state as WindowState);
      });

      // Get initial window state
      window.electronAPI.getWindowState().then((state: string) => {
        setWindowState(state as WindowState);
      });

      // Send PING to check connection (after listener is set up)
      console.log('🔌 Sending PING to backend...');
      window.electronAPI.sendToBackend('PING', {});
    }
  }, []);

  // Avatar window is now handled by main process as separate BrowserWindow

  // Minimized indicator bar
  if (windowState === 'minimized') {
    return (
      <div className="w-full h-full select-none">
        <div className="glass-dark w-full h-full rounded-lg shadow-2xl overflow-hidden flex items-center px-4 drag-region">
          {/* Status indicator */}
          <div className="no-drag flex items-center gap-3 flex-1">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
            <span className="text-white/80 text-sm font-medium">
              {!isRegistered ? 'AI Tutor' : isWaiting ? 'Waiting for breakout...' : 'Ready'}
            </span>
          </div>

          {/* Expand button if not registered */}
          {!isRegistered && (
            <button
              onClick={() => {
                console.log('Setup clicked!');
                window.electronAPI?.setWindowState('expanded');
              }}
              className="no-drag text-white/60 hover:text-white text-xs px-3 py-1 rounded bg-white/10 hover:bg-white/20 transition-colors cursor-pointer z-10"
            >
              Setup
            </button>
          )}

          {/* Close button */}
          <button
            onClick={() => {
              console.log('Close clicked!');
              window.electronAPI?.closeWindow();
            }}
            className="no-drag text-white/40 hover:text-white ml-2 transition-colors cursor-pointer z-10"
          >
            ×
          </button>
        </div>
      </div>
    );
  }

  // Expanded registration/setup view
  return (
    <div className="w-full h-screen select-none bg-gradient-to-br from-gray-900 to-black">
      {/* Drag region */}
      <div className="drag-region h-8 w-full flex items-center justify-between px-4">
        <span className="text-white/60 text-xs">AI Tutor Setup</span>
        <button
          onClick={() => window.electronAPI?.setWindowState('minimized')}
          className="no-drag text-white/40 hover:text-white transition-colors text-lg"
        >
          −
        </button>
      </div>

      <div className="no-drag px-8 py-6">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white mb-2">AI Professor Tutor</h1>
          <p className="text-white/60">
            {isWaiting 
              ? 'Waiting for your professor to start breakout rooms...'
              : 'Register to receive personalized tutoring during class'}
          </p>
        </div>

        {/* Connection status */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
          <span className="text-white/60 text-sm">
            {isConnected ? 'Connected to server' : 'Connecting...'}
          </span>
        </div>

        {!isRegistered ? (
          /* Registration form */
          <div className="max-w-md mx-auto space-y-4">
            <div>
              <label className="block text-white/70 text-sm mb-1">Your Name</label>
              <input
                type="text"
                value={studentName}
                onChange={(e) => setStudentName(e.target.value)}
                placeholder="Enter your name"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-white/70 text-sm mb-1">Email</label>
              <input
                type="email"
                value={studentEmail}
                onChange={(e) => setStudentEmail(e.target.value)}
                placeholder="your@email.com"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
            <button
              onClick={registerStudent}
              disabled={!studentName.trim() || !studentEmail.trim() || !isConnected}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium py-3 rounded-lg transition-colors"
            >
              Register for AI Tutoring
            </button>
          </div>
        ) : (
          /* Waiting state */
          <div className="max-w-md mx-auto text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-500/20 mb-4">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent"></div>
            </div>
            <h3 className="text-white font-medium mb-2">You're all set, {studentName}!</h3>
            <p className="text-white/60 text-sm mb-4">
              {meetingStatus || 'When your professor sends everyone to breakout rooms, your AI tutor will automatically appear.'}
            </p>
            <button
              onClick={() => window.electronAPI?.setWindowState('minimized')}
              className="text-white/60 hover:text-white text-sm underline transition-colors"
            >
              Minimize to taskbar
            </button>
          </div>
        )}

        {/* Footer */}
        <div className="absolute bottom-4 left-0 right-0 text-center">
          <p className="text-white/30 text-xs">
            This app will run in the background until needed
          </p>
        </div>
      </div>
    </div>
  );
};

export default App;
