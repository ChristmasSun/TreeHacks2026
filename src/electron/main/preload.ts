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
});

// TypeScript type definitions for window.electronAPI
declare global {
  interface Window {
    electronAPI: {
      sendToBackend: (type: string, payload: any) => void;
      onBackendMessage: (callback: (message: any) => void) => void;
      minimizeWindow: () => void;
      closeWindow: () => void;
    };
  }
}
