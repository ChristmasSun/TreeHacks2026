/**
 * IPC handlers for communication between renderer and main process
 */
import { ipcMain, BrowserWindow } from 'electron';
import { WebSocketClient } from './websocket-client';

export function setupIPCHandlers(wsClient: WebSocketClient, mainWindow: BrowserWindow) {
  // Handle messages from renderer to send to backend
  ipcMain.on('send-to-backend', (_event, { type, payload }) => {
    console.log(`IPC: Forwarding to backend - ${type}`);
    wsClient.send(type, payload);
  });

  // Handle window controls
  ipcMain.on('minimize-window', () => {
    mainWindow.minimize();
  });

  ipcMain.on('close-window', () => {
    mainWindow.close();
  });

  // Handle maximize/restore (for future expandable UI)
  ipcMain.on('maximize-window', () => {
    if (mainWindow.isMaximized()) {
      mainWindow.restore();
    } else {
      mainWindow.maximize();
    }
  });

  console.log('IPC handlers registered');
}
