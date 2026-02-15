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

  // Role selection (professor / student)
  setRole: (role: string) => ipcRenderer.send('set-role', role),
  getRole: () => ipcRenderer.invoke('get-role'),

  // Backend URL configuration (for LAN connection)
  setBackendUrl: (url: string) => ipcRenderer.send('set-backend-url', url),
  getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),

  // Directory picker (for professor to select pipeline output)
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
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
      setRole: (role: string) => void;
      getRole: () => Promise<string>;
      setBackendUrl: (url: string) => void;
      getBackendUrl: () => Promise<string>;
      selectDirectory: () => Promise<string | null>;
    };
  }
}
