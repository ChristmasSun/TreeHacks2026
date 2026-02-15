/**
 * Demeanor Panel - Real-time engagement/attention analysis from RTMS video frames
 */
import React, { useState, useEffect } from 'react';

interface DemeanorMetrics {
  user_id: string;
  user_name: string;
  engagement_score: number;
  attention: string;
  expression: string;
  timestamp: string;
}

interface DemeanorPanelProps {
  backendUrl: string;
}

const DemeanorPanel: React.FC<DemeanorPanelProps> = ({ backendUrl }) => {
  const [metrics, setMetrics] = useState<Record<string, DemeanorMetrics>>({});
  const [summary, setSummary] = useState<any>(null);

  // Listen for demeanor updates via WebSocket
  useEffect(() => {
    if (!window.electronAPI) return;

    window.electronAPI.onBackendMessage((msg: any) => {
      if (msg.type === 'DEMEANOR_UPDATE') {
        const data = msg.payload;
        setMetrics(prev => ({
          ...prev,
          [data.user_id]: data,
        }));
      }
    });
  }, []);

  // Poll summary
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/demeanor/summary`);
        if (res.ok) {
          setSummary(await res.json());
        }
      } catch {}
    };
    const interval = setInterval(poll, 15000);
    return () => clearInterval(interval);
  }, [backendUrl]);

  const students = Object.values(metrics);

  const getScoreColor = (score: number) => {
    if (score >= 0.7) return 'bg-green-500';
    if (score >= 0.4) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getScoreLabel = (score: number) => {
    if (score >= 0.7) return 'Engaged';
    if (score >= 0.4) return 'Distracted';
    return 'Disengaged';
  };

  return (
    <section className="bg-white/5 rounded-xl p-5 border border-white/10">
      <h2 className="text-lg font-semibold mb-4">Student Engagement (RTMS Video)</h2>

      {students.length === 0 ? (
        <div className="text-white/40 text-sm">
          <p>No demeanor data yet. Engagement analysis starts when RTMS video frames are received.</p>
          <p className="mt-1 text-xs text-white/30">
            Requires active Zoom meeting with RTMS video enabled.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Per-student cards */}
          <div className="grid grid-cols-2 gap-3">
            {students.map((s) => (
              <div key={s.user_id} className="bg-white/5 rounded-lg p-3 flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${getScoreColor(s.engagement_score)}`} />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm truncate">{s.user_name}</div>
                  <div className="text-white/40 text-xs">
                    {getScoreLabel(s.engagement_score)} · {s.expression || 'neutral'}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-semibold">{Math.round(s.engagement_score * 100)}%</div>
                </div>
              </div>
            ))}
          </div>

          {/* Summary */}
          {summary && summary.total_students > 0 && (
            <div className="bg-white/5 rounded-lg p-3 mt-3">
              <div className="text-white/40 text-xs mb-1">Session Summary</div>
              <div className="flex items-center gap-4 text-sm">
                <span>Avg Engagement: <strong>{Math.round((summary.avg_engagement || 0) * 100)}%</strong></span>
                <span>Students Analyzed: <strong>{summary.total_students}</strong></span>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
};

export default DemeanorPanel;
