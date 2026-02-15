/**
 * Quiz Control - Sub-component for launching quizzes via Zoom Team Chat
 */
import React, { useState, useCallback } from 'react';

interface QuizControlProps {
  backendUrl: string;
  lectureLoaded: boolean;
  studentCount: number;
  onLog: (message: string, type?: 'info' | 'success' | 'error') => void;
}

const QuizControl: React.FC<QuizControlProps> = ({ backendUrl, lectureLoaded, studentCount, onLog }) => {
  const [isLaunching, setIsLaunching] = useState(false);
  const [quizResult, setQuizResult] = useState<any>(null);

  const launchQuiz = useCallback(async () => {
    setIsLaunching(true);
    onLog('Generating and sending quiz to students...', 'info');

    try {
      const res = await fetch(`${backendUrl}/api/quiz/launch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await res.json();

      if (data.success) {
        setQuizResult(data);
        onLog(`Quiz sent to ${data.students_sent} students (${data.question_count} questions)`, 'success');
      } else {
        onLog(`Quiz launch failed: ${data.error || 'Unknown error'}`, 'error');
      }
    } catch (e: any) {
      onLog(`Quiz launch error: ${e.message}`, 'error');
    } finally {
      setIsLaunching(false);
    }
  }, [backendUrl, onLog]);

  return (
    <section className="glass-card p-6">
      <h2 className="text-base font-medium tracking-wide text-white/80 mb-4">Quiz via Zoom Team Chat</h2>

      {!lectureLoaded ? (
        <p className="text-white/30 text-sm font-light">Load lecture content first to enable quizzes.</p>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <button
              onClick={launchQuiz}
              disabled={isLaunching || studentCount === 0}
              className="px-6 py-2.5 bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/20 disabled:bg-white/[0.04] disabled:text-white/30 disabled:border-white/[0.06] disabled:cursor-not-allowed rounded-xl font-medium transition-all"
            >
              {isLaunching ? 'Sending Quiz...' : 'Send Quiz to Students'}
            </button>
            <span className="text-sm text-white/40 font-light">
              via Zoom Team Chat chatbot
            </span>
          </div>

          {quizResult && (
            <div className="glass-card p-4 border-purple-500/20">
              <div className="text-purple-300 font-medium text-sm mb-1">Quiz Sent</div>
              <div className="text-white/50 text-sm font-light">
                {quizResult.students_sent} students, {quizResult.question_count} questions
              </div>
              <div className="text-white/30 text-xs mt-1 font-light">
                Students will see the quiz in Zoom Team Chat. Wrong answers trigger Manim explainer videos.
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
};

export default QuizControl;
