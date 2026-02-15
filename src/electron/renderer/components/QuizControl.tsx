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

      setQuizResult(data);
      const msg = data.message || `Quiz ready! ${data.students_sent || 0} students notified. Others can type /makequiz in Zoom Team Chat.`;
      onLog(msg, 'success');
    } catch (e: any) {
      onLog(`Quiz launch error: ${e.message}`, 'error');
    } finally {
      setIsLaunching(false);
    }
  }, [backendUrl, onLog]);

  return (
    <section className="bg-white/5 rounded-xl p-5 border border-white/10">
      <h2 className="text-lg font-semibold mb-4">Quiz via Zoom Team Chat</h2>

      {!lectureLoaded ? (
        <p className="text-white/40 text-sm">Load lecture content first to enable quizzes.</p>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <button
              onClick={launchQuiz}
              disabled={isLaunching || studentCount === 0}
              className="px-6 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
            >
              {isLaunching ? 'Sending Quiz...' : 'Send Quiz to Students'}
            </button>
            <span className="text-sm text-white/40">
              via Zoom Team Chat chatbot
            </span>
          </div>

          {quizResult && (
            <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-3 text-sm">
              <div className="text-purple-300 font-medium mb-1">Quiz Sent</div>
              <div className="text-white/60">
                {quizResult.students_sent} students, {quizResult.question_count} questions
              </div>
              <div className="text-white/40 text-xs mt-1">
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
