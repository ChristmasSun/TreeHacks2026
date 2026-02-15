/**
 * Main App - Role Selection + Student/Professor routing
 */
import React, { useState, useEffect, useCallback } from 'react';
import ProfessorDashboard from './components/ProfessorDashboard';

type Role = '' | 'professor' | 'student';
type StudentPhase = 'connect' | 'register' | 'waiting';

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

  // Student: connect to professor's backend
  const connectToBackend = useCallback(async () => {
    if (!backendIp.trim()) return;
    setIsConnecting(true);
    setConnectionError('');

    const url = `http://${backendIp.trim()}:8000`;
    try {
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
      <div className="w-full h-screen select-none bg-gradient-to-br from-gray-900 via-gray-800 to-black flex items-center justify-center relative overflow-hidden">
        {/* Subtle radial blue glow */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-[600px] h-[600px] rounded-full bg-blue-500/[0.07] blur-[120px]" />
        </div>

        <div className="text-center max-w-lg relative z-10">
          <h1 className="text-5xl font-light tracking-tight gradient-text mb-4">AI Professor</h1>
          <p className="text-white/40 mb-14 text-lg font-light tracking-wider">Scalable Personalized Education</p>

          <div className="flex gap-6 justify-center">
            {/* Professor Button */}
            <button
              onClick={() => selectRole('professor')}
              className="group w-56 h-48 rounded-2xl bg-white/[0.06] backdrop-blur-xl border border-white/10 hover:bg-white/[0.1] hover:shadow-lg hover:shadow-blue-500/10 hover:border-blue-400/30 transition-all flex flex-col items-center justify-center gap-3 cursor-pointer"
            >
              <div className="text-4xl opacity-80 group-hover:opacity-100 transition-opacity">
                <svg className="w-10 h-10 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342M6.75 15a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm0 0v-3.675A55.378 55.378 0 0 1 12 8.443m-7.007 11.55A5.981 5.981 0 0 0 6.75 15.75v-1.5" />
                </svg>
              </div>
              <div className="text-white font-medium text-xl">Professor</div>
              <div className="text-white/30 text-sm font-light">Dashboard & Controls</div>
            </button>

            {/* Student Button */}
            <button
              onClick={() => selectRole('student')}
              className="group w-56 h-48 rounded-2xl bg-white/[0.06] backdrop-blur-xl border border-white/10 hover:bg-white/[0.1] hover:shadow-lg hover:shadow-blue-500/10 hover:border-blue-400/30 transition-all flex flex-col items-center justify-center gap-3 cursor-pointer"
            >
              <div className="text-4xl opacity-80 group-hover:opacity-100 transition-opacity">
                <svg className="w-10 h-10 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
                </svg>
              </div>
              <div className="text-white font-medium text-xl">Student</div>
              <div className="text-white/30 text-sm font-light">Join AI Tutoring</div>
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
      <div className="w-full h-screen select-none bg-gradient-to-br from-gray-900 via-gray-800 to-black flex items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-[500px] h-[500px] rounded-full bg-blue-500/[0.05] blur-[100px]" />
        </div>

        <div className="max-w-md w-full px-8 relative z-10">
          <button
            onClick={() => setRole('')}
            className="text-white/30 hover:text-white/60 text-sm mb-8 flex items-center gap-1 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
            Back
          </button>

          <div className="glass-card p-8">
            <h2 className="text-2xl font-light text-white mb-2 tracking-tight">Connect to Class</h2>
            <p className="text-white/40 mb-8 font-light">Enter your professor's server IP address</p>

            <div className="space-y-4">
              <div>
                <label className="block text-white/50 text-sm mb-1.5 font-medium tracking-wide">Server IP Address</label>
                <input
                  type="text"
                  value={backendIp}
                  onChange={(e) => setBackendIp(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && connectToBackend()}
                  placeholder="e.g., 192.168.1.100"
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-400/60 focus:ring-1 focus:ring-blue-400/20 transition-all font-mono"
                  autoFocus
                />
              </div>

              {connectionError && (
                <div className="text-red-400/80 text-sm bg-red-400/10 rounded-xl px-4 py-2 border border-red-400/10">
                  {connectionError}
                </div>
              )}

              <button
                onClick={connectToBackend}
                disabled={!backendIp.trim() || isConnecting}
                className="w-full bg-blue-500/80 hover:bg-blue-500 disabled:bg-white/[0.06] disabled:text-white/30 disabled:cursor-not-allowed backdrop-blur text-white font-medium py-3 rounded-xl transition-all"
              >
                {isConnecting ? 'Connecting...' : 'Connect'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Phase 2: Register
  if (studentPhase === 'register') {
    return (
      <div className="w-full h-screen select-none bg-gradient-to-br from-gray-900 via-gray-800 to-black flex items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-[500px] h-[500px] rounded-full bg-blue-500/[0.05] blur-[100px]" />
        </div>

        <div className="max-w-md w-full px-8 relative z-10">
          <div className="glass-card p-8">
            <div className="flex items-center gap-2 mb-6">
              <div className="w-2 h-2 rounded-full bg-blue-400"></div>
              <span className="text-blue-400 text-sm font-light">Connected to {backendIp}</span>
            </div>

            <h2 className="text-2xl font-light text-white mb-2 tracking-tight">Register</h2>
            <p className="text-white/40 mb-8 font-light">Enter your details to join the session</p>

            <div className="space-y-4">
              <div>
                <label className="block text-white/50 text-sm mb-1.5 font-medium tracking-wide">Your Name</label>
                <input
                  type="text"
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  placeholder="Enter your name"
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-400/60 focus:ring-1 focus:ring-blue-400/20 transition-all"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-white/50 text-sm mb-1.5 font-medium tracking-wide">Email</label>
                <input
                  type="email"
                  value={studentEmail}
                  onChange={(e) => setStudentEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-400/60 focus:ring-1 focus:ring-blue-400/20 transition-all"
                />
              </div>
              <div>
                <label className="block text-white/50 text-sm mb-1.5 font-medium tracking-wide">Zoom Email (for quiz chat)</label>
                <input
                  type="email"
                  value={zoomEmail}
                  onChange={(e) => setZoomEmail(e.target.value)}
                  placeholder="Same as above if identical"
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-400/60 focus:ring-1 focus:ring-blue-400/20 transition-all"
                />
              </div>

              <button
                onClick={registerStudent}
                disabled={!studentName.trim() || !studentEmail.trim()}
                className="w-full bg-blue-500/80 hover:bg-blue-500 disabled:bg-white/[0.06] disabled:text-white/30 disabled:cursor-not-allowed backdrop-blur text-white font-medium py-3 rounded-xl transition-all"
              >
                Join Session
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Phase 3: Waiting for breakout
  return (
    <div className="w-full h-screen select-none bg-gradient-to-br from-gray-900 via-gray-800 to-black flex items-center justify-center relative overflow-hidden">
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-[500px] h-[500px] rounded-full bg-blue-500/[0.05] blur-[100px]" />
      </div>

      <div className="max-w-md w-full px-8 text-center relative z-10">
        <div className="glass-card p-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-500/10 border border-blue-400/20 mb-6">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-400 border-t-transparent"></div>
          </div>
          <h3 className="text-white font-light text-xl mb-2 tracking-tight">You're all set, {studentName}!</h3>
          <p className="text-white/50 text-sm mb-2 font-light">
            {meetingStatus || 'Waiting for your professor to start the session...'}
          </p>
          <p className="text-white/30 text-xs font-light">
            Connected to {backendIp}
          </p>
          <button
            onClick={() => window.electronAPI?.setWindowState('minimized')}
            className="mt-8 text-white/40 hover:text-white/70 text-sm transition-colors font-light"
          >
            Minimize to taskbar
          </button>
        </div>
      </div>
    </div>
  );
};

export default App;
