/**
 * HeyGen Avatar Overlay Component
 * 
 * Displays a personalized HeyGen avatar when breakout rooms are triggered.
 * Uses LiveKit for WebRTC streaming.
 */
import React, { useEffect, useRef, useState, useCallback } from 'react';

interface HeyGenAvatarProps {
  sessionId: string | null;
  livekitUrl: string | null;
  accessToken: string | null;
  studentName: string;
  onClose: () => void;
  onSpeakRequest?: (text: string) => void;
}

interface Message {
  role: 'avatar' | 'student';
  text: string;
  timestamp: Date;
}

export const HeyGenAvatar: React.FC<HeyGenAvatarProps> = ({
  sessionId,
  livekitUrl,
  accessToken,
  studentName,
  onClose,
  onSpeakRequest,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const roomRef = useRef<any>(null);

  // Connect to LiveKit
  const connectToAvatar = useCallback(async () => {
    if (!livekitUrl || !accessToken) {
      setError('Missing LiveKit credentials');
      return;
    }

    setIsConnecting(true);
    setError(null);

    try {
      // Dynamically import LiveKit client
      const LivekitClient = await import('livekit-client');
      
      const room = new LivekitClient.Room({
        adaptiveStream: true,
        dynacast: true,
      });

      room.on(LivekitClient.RoomEvent.TrackSubscribed, (track: any, publication: any, participant: any) => {
        console.log('Track subscribed:', track.kind, participant.identity);
        
        if (track.kind === 'video' && videoRef.current) {
          track.attach(videoRef.current);
          setIsConnected(true);
          setIsConnecting(false);
          
          // Initial greeting
          addMessage('avatar', `Hello ${studentName}! I'm here to help you understand the material. What questions do you have?`);
        }
      });

      room.on(LivekitClient.RoomEvent.Disconnected, () => {
        setIsConnected(false);
        setError('Disconnected from avatar');
      });

      await room.connect(livekitUrl, accessToken);
      roomRef.current = room;
      
      console.log('Connected to LiveKit room');

      // Check for existing tracks
      room.remoteParticipants.forEach((participant: any) => {
        participant.trackPublications.forEach((publication: any) => {
          if (publication.track && publication.track.kind === 'video' && videoRef.current) {
            publication.track.attach(videoRef.current);
            setIsConnected(true);
            setIsConnecting(false);
          }
        });
      });

    } catch (err: any) {
      console.error('LiveKit connection error:', err);
      setError(err.message || 'Failed to connect to avatar');
      setIsConnecting(false);
    }
  }, [livekitUrl, accessToken, studentName]);

  // Add message to chat
  const addMessage = (role: 'avatar' | 'student', text: string) => {
    setMessages(prev => [...prev, { role, text, timestamp: new Date() }]);
  };

  // Send message to avatar
  const sendMessage = async () => {
    if (!inputText.trim() || !sessionId) return;

    const text = inputText.trim();
    setInputText('');
    addMessage('student', text);
    setIsSpeaking(true);

    // Send to backend for avatar response
    if (onSpeakRequest) {
      onSpeakRequest(text);
    }

    // Also send via WebSocket
    window.electronAPI?.sendToBackend('STUDENT_MESSAGE', {
      sessionId,
      studentName,
      message: text,
    });
  };

  // Handle keyboard input
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Connect on mount
  useEffect(() => {
    if (livekitUrl && accessToken && !isConnected && !isConnecting) {
      connectToAvatar();
    }

    return () => {
      if (roomRef.current) {
        roomRef.current.disconnect();
      }
    };
  }, [livekitUrl, accessToken, isConnected, isConnecting, connectToAvatar]);

  // Listen for avatar responses
  useEffect(() => {
    const handleBackendMessage = (message: any) => {
      if (message.type === 'AVATAR_RESPONSE') {
        addMessage('avatar', message.payload.text);
        setIsSpeaking(false);
      }
    };

    window.electronAPI?.onBackendMessage(handleBackendMessage);
  }, []);

  return (
    <div className="fixed inset-0 bg-black/90 flex flex-col items-center justify-center z-50">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 h-12 bg-gradient-to-b from-black/80 to-transparent flex items-center justify-between px-4">
        <div className="text-white/80 text-sm font-medium">
          AI Professor • Session with {studentName}
        </div>
        <button
          onClick={onClose}
          className="text-white/60 hover:text-white transition-colors p-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Main Content */}
      <div className="flex flex-col lg:flex-row w-full max-w-5xl h-full max-h-[80vh] gap-4 p-4 pt-16">
        {/* Avatar Video */}
        <div className="flex-1 relative rounded-2xl overflow-hidden bg-gray-900 min-h-[300px]">
          {isConnecting && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent mx-auto mb-4"></div>
                <p className="text-white/80">Connecting to AI Professor...</p>
              </div>
            </div>
          )}
          
          {error && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center p-4">
                <div className="text-red-400 mb-2">⚠️ Connection Error</div>
                <p className="text-white/60 text-sm">{error}</p>
                <button
                  onClick={connectToAvatar}
                  className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white text-sm transition-colors"
                >
                  Retry Connection
                </button>
              </div>
            </div>
          )}

          <video
            ref={videoRef}
            autoPlay
            playsInline
            className={`w-full h-full object-cover ${isConnected ? 'opacity-100' : 'opacity-0'}`}
          />

          {/* Speaking indicator */}
          {isSpeaking && (
            <div className="absolute bottom-4 left-4 bg-black/60 px-3 py-1.5 rounded-full flex items-center gap-2">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse"></span>
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse delay-75"></span>
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse delay-150"></span>
              </div>
              <span className="text-white/80 text-xs">Processing...</span>
            </div>
          )}
        </div>

        {/* Chat Panel */}
        <div className="w-full lg:w-80 flex flex-col bg-gray-900/50 rounded-2xl overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'student' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] px-3 py-2 rounded-xl text-sm ${
                    msg.role === 'student'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 text-white/90'
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
          </div>

          {/* Input */}
          <div className="p-3 border-t border-white/10">
            <div className="flex gap-2">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask a question..."
                className="flex-1 bg-gray-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 transition-colors"
              />
              <button
                onClick={sendMessage}
                disabled={!inputText.trim() || isSpeaking}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg text-white text-sm transition-colors"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HeyGenAvatar;
