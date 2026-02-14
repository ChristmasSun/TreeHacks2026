/**
 * Main App component with frosted glass UI
 */
import React, { useState, useEffect } from 'react';
import Dashboard from './components/Dashboard';

const App: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Listen for backend messages
    if (window.electronAPI) {
      window.electronAPI.onBackendMessage((message: any) => {
        console.log('Received from backend:', message);

        if (message.type === 'PONG') {
          setIsConnected(true);
        }
      });
    }
  }, []);

  return (
    <div className="w-full h-screen select-none">
      {/* Frosted glass container */}
      <div className="glass-dark w-full h-full rounded-lg shadow-2xl overflow-hidden">
        {/* Drag region for window movement */}
        <div className="drag-region h-2 w-full"></div>

        {/* Main content */}
        <div className="no-drag px-4 pb-2">
          <Dashboard isConnected={isConnected} />
        </div>
      </div>
    </div>
  );
};

export default App;
