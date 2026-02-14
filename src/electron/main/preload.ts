/**
 * Preload script - context bridge for secure IPC
 */
import { contextBridge, ipcRenderer } from 'electron';

// Expose protected methods that allow the renderer to use IPC
contextBridge.exposeInMainWorld('electronAPI', {
  // Send message to backend via main process
  sendToBackend: (type: string, payload: any) => {
    ipcRenderer.send('send-to-backend', { type, payload });
  },

  // Listen for messages from backend
  onBackendMessage: (callback: (message: any) => void) => {
    ipcRenderer.on('backend-message', (_event, message) => {
      callback(message);
    });
  },

  // Window controls
  minimizeWindow: () => ipcRenderer.send('minimize-window'),
  closeWindow: () => ipcRenderer.send('close-window'),
  
  // Window state management
  setWindowState: (state: 'hidden' | 'minimized' | 'expanded') => {
    ipcRenderer.send('set-window-state', state);
  },
  getWindowState: () => ipcRenderer.invoke('get-window-state'),
  onWindowStateChanged: (callback: (state: string) => void) => {
    ipcRenderer.on('window-state-changed', (_event, state) => {
      callback(state);
    });
  },
  
  // Student registration (notify main process)
  studentRegistered: (student: { name: string; email: string }) => {
    ipcRenderer.send('student-registered', student);
  },
});

// TypeScript type definitions for window.electronAPI
declare global {
  interface Window {
    electronAPI: {
      sendToBackend: (type: string, payload: any) => void;
      onBackendMessage: (callback: (message: any) => void) => void;
      minimizeWindow: () => void;
      closeWindow: () => void;
      setWindowState: (state: 'hidden' | 'minimized' | 'expanded') => void;
      getWindowState: () => Promise<string>;
      onWindowStateChanged: (callback: (state: string) => void) => void;
      studentRegistered: (student: { name: string; email: string }) => void;
    };
  }
}
