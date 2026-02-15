/**
 * Main App - Role Selection + Student/Professor routing
 */
import React, { useState, useEffect, useCallback } from 'react';
import HeyGenAvatar from './components/HeyGenAvatar';
import ProfessorDashboard from './components/ProfessorDashboard';

type Role = '' | 'professor' | 'student';
type StudentPhase = 'connect' | 'register' | 'waiting';

interface AvatarSession {
  sessionId: string;
  livekitUrl: string;
  accessToken: string;
}

const App: React.FC = () => {
  const [role, setRole] = useState<Role>('');
  const [isConnected, setIsConnected] = useState(false);

  // Student state
  const [studentPhase, setStudentPhase] = useState<StudentPhase>('connect');
  const [backendIp, setBackendIp] = useState('');
  const [connectionError, setConnectionError] = useState('');
  const [studentName, setStudentName] = useState('');
  const [studentEmail, setStudentEmail] = useState('');
  const [zoomEmail, setZoomEmail] = useState('');
  const [meetingStatus, setMeetingStatus] = useState('');
  const [isConnecting, setIsConnecting] = useState(false);

  // Choose role
  const selectRole = useCallback((selectedRole: Role) => {
    setRole(selectedRole);
    window.electronAPI?.setRole(selectedRole);

    if (selectedRole === 'professor') {
      // Professor runs backend locally — backend URL stays as default
      window.electronAPI?.setWindowState('expanded');
    }
  }, []);

  const normalizeBackendUrl = (input: string): string => {
    const trimmed = input.trim();
    if (!trimmed) return '';

    // Accept IP, host:port, or full URL
    const withProtocol = /^https?:\/\//i.test(trimmed) ? trimmed : `http://${trimmed}`;
    const parsed = new URL(withProtocol);
    const host = parsed.hostname;
    const port = parsed.port || '8000';
    return `http://${host}:${port}`;
  };

  // Student: connect to professor's backend
  const connectToBackend = useCallback(async () => {
    if (!backendIp.trim()) return;
    setIsConnecting(true);
    setConnectionError('');

    let url = '';
    try {
      url = normalizeBackendUrl(backendIp);
      if (!url) throw new Error('Invalid backend address');

      const resp = await fetch(`${url}/health`, { signal: AbortSignal.timeout(5000) });
      if (!resp.ok) throw new Error('Backend not healthy');

      // Set backend URL and reconnect WebSocket
      window.electronAPI?.setBackendUrl(url);
      setStudentPhase('register');
      setIsConnected(true);
    } catch (e: any) {
      setConnectionError(`Could not connect to ${url}. Check the IP and make sure the backend is running.`);
    } finally {
      setIsConnecting(false);
    }
  }, [backendIp]);

  // Student: register
  const registerStudent = useCallback(() => {
    if (!studentName.trim() || !studentEmail.trim()) return;

    const student = {
      name: studentName.trim(),
      email: studentEmail.trim(),
      zoom_email: zoomEmail.trim() || studentEmail.trim(),
    };

    window.electronAPI?.sendToBackend('REGISTER_STUDENT', student);
    window.electronAPI?.studentRegistered({ name: student.name, email: student.email });
    setStudentPhase('waiting');
  }, [studentName, studentEmail, zoomEmail]);

  // Listen for backend messages
  useEffect(() => {
    if (!window.electronAPI) return;

    window.electronAPI.onBackendMessage((message: any) => {
      switch (message.type) {
        case 'PONG':
          setIsConnected(true);
          break;
        case 'STUDENT_REGISTERED':
          setStudentPhase('waiting');
          break;
        case 'BREAKOUT_STARTED':
        case 'BREAKOUT_ROOM_ASSIGNED':
          setMeetingStatus('AI Tutor session started!');
          break;
        case 'SESSION_ENDED':
          setMeetingStatus('Session ended');
          break;
      }
    });

    // Check initial connection
    window.electronAPI.sendToBackend('PING', {});
  }, []);

  // ==================== Role Selection Screen ====================
  if (role === '') {
    return (
      <div className="w-full h-screen select-none bg-gradient-to-br from-gray-900 via-gray-800 to-black flex items-center justify-center">
        <div className="text-center max-w-lg">
          <h1 className="text-4xl font-bold text-white mb-3">AI Professor</h1>
          <p className="text-white/50 mb-12 text-lg">Scalable Personalized Education</p>

          <div className="flex gap-6 justify-center">
            {/* Professor Button */}
            <button
              onClick={() => selectRole('professor')}
              className="group w-56 h-48 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-800 hover:from-blue-500 hover:to-blue-700 transition-all shadow-lg hover:shadow-blue-500/25 flex flex-col items-center justify-center gap-3 cursor-pointer"
            >
              <div className="text-5xl">🎓</div>
              <div className="text-white font-semibold text-xl">Professor</div>
              <div className="text-blue-200/70 text-sm">Dashboard & Controls</div>
            </button>

            {/* Student Button */}
            <button
              onClick={() => selectRole('student')}
              className="group w-56 h-48 rounded-2xl bg-gradient-to-br from-emerald-600 to-emerald-800 hover:from-emerald-500 hover:to-emerald-700 transition-all shadow-lg hover:shadow-emerald-500/25 flex flex-col items-center justify-center gap-3 cursor-pointer"
            >
              <div className="text-5xl">📚</div>
              <div className="text-white font-semibold text-xl">Student</div>
              <div className="text-emerald-200/70 text-sm">Join AI Tutoring</div>
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ==================== Professor Mode ====================
  if (role === 'professor') {
    return <ProfessorDashboard />;
  }

  // ==================== Student Mode ====================

  // Phase 1: Connect to professor's backend
  if (studentPhase === 'connect') {
    return (
      <div className="w-full h-screen select-none bg-gradient-to-br from-gray-900 to-black flex items-center justify-center">
        <div className="max-w-md w-full px-8">
          <button
            onClick={() => setRole('')}
            className="text-white/40 hover:text-white text-sm mb-6 flex items-center gap-1"
          >
            ← Back
          </button>

          <h2 className="text-2xl font-bold text-white mb-2">Connect to Class</h2>
          <p className="text-white/50 mb-8">Enter your professor's server IP address</p>
          <p className="text-white/40 mb-5 text-xs">
            Host should run <code>bun run dev</code> so backend is available on port 8000.
          </p>

          <div className="space-y-4">
            <div>
              <label className="block text-white/70 text-sm mb-1">Server IP Address</label>
              <input
                type="text"
                value={backendIp}
                onChange={(e) => setBackendIp(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && connectToBackend()}
                placeholder="e.g., 192.168.1.100"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-colors font-mono"
                autoFocus
              />
            </div>

            {connectionError && (
              <div className="text-red-400 text-sm bg-red-400/10 rounded-lg px-4 py-2">
                {connectionError}
              </div>
            )}

            <button
              onClick={connectToBackend}
              disabled={!backendIp.trim() || isConnecting}
              className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium py-3 rounded-lg transition-colors"
            >
              {isConnecting ? 'Connecting...' : 'Connect'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Phase 2: Register
  if (studentPhase === 'register') {
    return (
      <div className="w-full h-screen select-none bg-gradient-to-br from-gray-900 to-black flex items-center justify-center">
        <div className="max-w-md w-full px-8">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-2 h-2 rounded-full bg-green-400"></div>
            <span className="text-green-400 text-sm">Connected to {backendIp}</span>
          </div>

          <h2 className="text-2xl font-bold text-white mb-2">Register</h2>
          <p className="text-white/50 mb-8">Enter your details to join the session</p>

          <div className="space-y-4">
            <div>
              <label className="block text-white/70 text-sm mb-1">Your Name</label>
              <input
                type="text"
                value={studentName}
                onChange={(e) => setStudentName(e.target.value)}
                placeholder="Enter your name"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-colors"
                autoFocus
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
            <div>
              <label className="block text-white/70 text-sm mb-1">Zoom Email (for quiz chat)</label>
              <input
                type="email"
                value={zoomEmail}
                onChange={(e) => setZoomEmail(e.target.value)}
                placeholder="Same as above if identical"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            <button
              onClick={registerStudent}
              disabled={!studentName.trim() || !studentEmail.trim()}
              className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium py-3 rounded-lg transition-colors"
            >
              Join Session
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Phase 3: Waiting for breakout
  return (
    <div className="w-full h-screen select-none bg-gradient-to-br from-gray-900 to-black flex items-center justify-center">
      <div className="max-w-md w-full px-8 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-500/20 mb-4">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-emerald-500 border-t-transparent"></div>
        </div>
        <h3 className="text-white font-medium text-xl mb-2">You're all set, {studentName}!</h3>
        <p className="text-white/60 text-sm mb-2">
          {meetingStatus || 'Waiting for your professor to start the session...'}
        </p>
        <p className="text-white/40 text-xs">
          Connected to {backendIp}
        </p>
        <button
          onClick={() => window.electronAPI?.setWindowState('minimized')}
          className="mt-6 text-white/60 hover:text-white text-sm underline transition-colors"
        >
          Minimize to taskbar
        </button>
      </div>
    </div>
  );
};

export default App;
