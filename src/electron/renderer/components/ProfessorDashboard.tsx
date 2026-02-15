/**
 * Professor Dashboard - Main control panel for the demo
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import QuizControl from './QuizControl';
import DemeanorPanel from './DemeanorPanel';

interface Student {
  email: string;
  name: string;
  registered_at: string;
  has_avatar: boolean;
  zoom_email?: string;
}

interface LectureStatus {
  transcript_loaded: boolean;
  transcript_length: number;
  concepts_count: number;
  videos_count: number;
  output_dir: string;
  context: { topic: string; key_points: string };
}

interface LogEntry {
  time: string;
  message: string;
  type: 'info' | 'success' | 'error';
}

const BACKEND_URL = 'http://127.0.0.1:8000';

const ProfessorDashboard: React.FC = () => {
  const [isHealthy, setIsHealthy] = useState(false);
  const [serverIp, setServerIp] = useState('');
  const [students, setStudents] = useState<Student[]>([]);
  const [lectureStatus, setLectureStatus] = useState<LectureStatus | null>(null);
  const [isLoadingLecture, setIsLoadingLecture] = useState(false);
  const [isBreakoutActive, setIsBreakoutActive] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const addLog = useCallback((message: string, type: LogEntry['type'] = 'info') => {
    const time = new Date().toLocaleTimeString();
    setLogs(prev => [...prev.slice(-50), { time, message, type }]);
  }, []);

  // Health check
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/health`);
        const data = await res.json();
        setIsHealthy(data.status === 'healthy');
      } catch {
        setIsHealthy(false);
      }
    };
    check();
    const interval = setInterval(check, 10000);
    return () => clearInterval(interval);
  }, []);

  // Get server IP
  useEffect(() => {
    fetch(`${BACKEND_URL}/api/server-info`)
      .then(r => r.json())
      .then(data => setServerIp(data.server_ip))
      .catch(() => {});
  }, []);

  // Poll students
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/registered-students`);
        const data = await res.json();
        setStudents(data.students || []);
      } catch {}
    };
    poll();
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, []);

  // Poll lecture status
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/lecture/status`);
        const data = await res.json();
        setLectureStatus(data);
      } catch {}
    };
    poll();
    const interval = setInterval(poll, 10000);
    return () => clearInterval(interval);
  }, []);

  // Listen for backend messages
  useEffect(() => {
    if (!window.electronAPI) return;
    window.electronAPI.onBackendMessage((msg: any) => {
      if (msg.type === 'BREAKOUT_TRIGGERED') {
        addLog(`Breakout triggered for ${msg.payload?.count} students`, 'success');
        setIsBreakoutActive(true);
      } else if (msg.type === 'STUDENT_REGISTERED') {
        addLog(`Student registered: ${msg.payload?.name}`, 'info');
      } else if (msg.type === 'PLAY_EXPLAINER_VIDEO') {
        addLog(`Video playing: ${msg.payload?.concept}`, 'info');
      } else if (msg.type === 'DEMEANOR_UPDATE') {
        // Handled by DemeanorPanel
      }
    });
    window.electronAPI.sendToBackend('PING', {});
  }, [addLog]);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Load lecture content
  const loadLecture = useCallback(async () => {
    const dir = await window.electronAPI?.selectDirectory();
    if (!dir) return;

    setIsLoadingLecture(true);
    addLog(`Loading lecture from: ${dir}`, 'info');

    try {
      const res = await fetch(`${BACKEND_URL}/api/lecture/load`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ output_dir: dir }),
      });
      const data = await res.json();

      if (data.success) {
        addLog(`Loaded: ${data.topic} (${data.concepts_count} concepts, ${data.videos_count} videos)`, 'success');
        // Refresh lecture status
        const statusRes = await fetch(`${BACKEND_URL}/api/lecture/status`);
        setLectureStatus(await statusRes.json());
      } else {
        addLog(`Failed to load lecture: ${JSON.stringify(data)}`, 'error');
      }
    } catch (e: any) {
      addLog(`Error loading lecture: ${e.message}`, 'error');
    } finally {
      setIsLoadingLecture(false);
    }
  }, [addLog]);

  // Trigger breakout rooms
  const triggerBreakout = useCallback(async () => {
    addLog('Triggering AI tutoring sessions...', 'info');
    try {
      const res = await fetch(`${BACKEND_URL}/api/trigger-breakout`, { method: 'POST' });
      const data = await res.json();
      addLog(`Breakout result: ${JSON.stringify(data)}`, data.count > 0 ? 'success' : 'error');
      setIsBreakoutActive(true);
    } catch (e: any) {
      addLog(`Breakout error: ${e.message}`, 'error');
    }
  }, [addLog]);

  return (
    <div className="w-full h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white overflow-hidden flex flex-col">
      {/* Header */}
      <div className="drag-region h-14 flex items-center justify-between px-6 bg-white/[0.04] backdrop-blur-xl border-b border-white/[0.08] shrink-0">
        <div className="no-drag flex items-center gap-4">
          <h1 className="font-medium text-lg gradient-text">AI Professor Dashboard</h1>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-blue-400' : 'bg-red-400'} ${isHealthy ? 'shadow-lg shadow-blue-400/30' : ''}`} style={isHealthy ? { animation: 'pulse 2s ease-in-out infinite' } : {}} />
            <span className="text-sm text-white/50 font-light">{isHealthy ? 'Backend OK' : 'Disconnected'}</span>
          </div>
          {serverIp && (
            <div className="text-sm text-white/30 font-mono bg-white/[0.04] px-2.5 py-0.5 rounded-lg border border-white/[0.06]">
              {serverIp}:8000
            </div>
          )}
        </div>
        <div className="no-drag flex items-center gap-2">
          <span className="text-sm text-white/30 font-light">{students.length} student{students.length !== 1 ? 's' : ''}</span>
          <button onClick={() => window.electronAPI?.minimizeWindow()} className="w-6 h-6 flex items-center justify-center hover:bg-white/10 rounded-lg text-white/50 transition-colors">−</button>
          <button onClick={() => window.electronAPI?.closeWindow()} className="w-6 h-6 flex items-center justify-center hover:bg-red-500/80 rounded-lg text-white/50 transition-colors">×</button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="grid grid-cols-12 gap-6 max-w-[1400px] mx-auto">

          {/* Left Column: Controls */}
          <div className="col-span-8 space-y-6">

            {/* Lecture Loader */}
            <section className="glass-card p-6">
              <h2 className="text-base font-medium tracking-wide text-white/80 mb-4">Lecture Content</h2>
              {lectureStatus?.transcript_loaded ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-blue-400">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                    </svg>
                    <span className="font-medium">{lectureStatus.context?.topic || 'Loaded'}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div className="glass-card p-4">
                      <div className="text-white/40 text-xs font-medium tracking-wide">Transcript</div>
                      <div className="text-xl font-light mt-1">{(lectureStatus.transcript_length / 1000).toFixed(1)}k</div>
                      <div className="text-white/30 text-xs">characters</div>
                    </div>
                    <div className="glass-card p-4">
                      <div className="text-white/40 text-xs font-medium tracking-wide">Concepts</div>
                      <div className="text-xl font-light mt-1">{lectureStatus.concepts_count}</div>
                      <div className="text-white/30 text-xs">scenes</div>
                    </div>
                    <div className="glass-card p-4">
                      <div className="text-white/40 text-xs font-medium tracking-wide">Videos</div>
                      <div className="text-xl font-light mt-1">{lectureStatus.videos_count}</div>
                      <div className="text-white/30 text-xs">explainers</div>
                    </div>
                  </div>
                  <button
                    onClick={loadLecture}
                    className="text-sm text-white/30 hover:text-white/60 transition-colors"
                  >
                    Load different lecture
                  </button>
                </div>
              ) : (
                <div>
                  <p className="text-white/40 text-sm mb-4 font-light">
                    Select a pipeline output directory to load lecture content.
                  </p>
                  <button
                    onClick={loadLecture}
                    disabled={isLoadingLecture}
                    className="px-6 py-2.5 bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 border border-blue-500/20 disabled:bg-white/[0.04] disabled:text-white/30 disabled:border-white/[0.06] rounded-xl font-medium transition-all"
                  >
                    {isLoadingLecture ? 'Loading...' : 'Select Output Directory'}
                  </button>
                </div>
              )}
            </section>

            {/* Breakout Control */}
            <section className="glass-card p-6">
              <h2 className="text-base font-medium tracking-wide text-white/80 mb-4">AI Tutoring (Breakout)</h2>
              <div className="flex items-center gap-4">
                <button
                  onClick={triggerBreakout}
                  disabled={students.length === 0 || isBreakoutActive}
                  className="px-6 py-2.5 bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 border border-blue-500/20 disabled:bg-white/[0.04] disabled:text-white/30 disabled:border-white/[0.06] disabled:cursor-not-allowed rounded-xl font-medium transition-all"
                >
                  {isBreakoutActive ? 'Sessions Active' : 'Launch AI Tutoring'}
                </button>
                <span className="text-sm text-white/40 font-light">
                  {students.length === 0
                    ? 'Waiting for students to connect...'
                    : `${students.length} student${students.length !== 1 ? 's' : ''} ready`}
                </span>
                {isBreakoutActive && (
                  <button
                    onClick={() => setIsBreakoutActive(false)}
                    className="text-sm text-red-400/80 hover:text-red-400 transition-colors"
                  >
                    Reset
                  </button>
                )}
              </div>
            </section>

            {/* Quiz Control */}
            <QuizControl
              backendUrl={BACKEND_URL}
              lectureLoaded={lectureStatus?.transcript_loaded ?? false}
              studentCount={students.length}
              onLog={addLog}
            />

            {/* Demeanor Panel */}
            <DemeanorPanel backendUrl={BACKEND_URL} />
          </div>

          {/* Right Column: Students + Logs */}
          <div className="col-span-4 space-y-6">

            {/* Students List */}
            <section className="glass-card p-6">
              <h2 className="text-base font-medium tracking-wide text-white/80 mb-3">Connected Students</h2>
              {students.length === 0 ? (
                <p className="text-white/30 text-sm font-light">No students connected yet.</p>
              ) : (
                <div className="space-y-2">
                  {students.map((s) => (
                    <div key={s.email} className="flex items-center justify-between bg-white/[0.04] hover:bg-white/[0.07] rounded-xl px-4 py-2.5 border border-white/[0.06] transition-colors">
                      <div>
                        <div className="font-medium text-sm">{s.name}</div>
                        <div className="text-white/30 text-xs">{s.email}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        {s.has_avatar && <span className="text-xs text-blue-400/80">Avatar</span>}
                        <div className="w-2 h-2 rounded-full bg-blue-400" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* Activity Log */}
            <section className="glass-card p-6">
              <h2 className="text-base font-medium tracking-wide text-white/80 mb-3">Activity Log</h2>
              <div className="h-64 overflow-y-auto text-xs font-mono space-y-1">
                {logs.length === 0 && <p className="text-white/20 font-light">No activity yet...</p>}
                {logs.map((log, i) => (
                  <div key={i} className={`${
                    log.type === 'error' ? 'text-red-400/80' :
                    log.type === 'success' ? 'text-green-400/80' : 'text-white/50'
                  }`}>
                    <span className="text-white/20">[{log.time}]</span> {log.message}
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfessorDashboard;
