/**
 * Electron main process
 * Creates minimal top-bar window (Cluely-style)
 */
import { app, BrowserWindow, screen } from 'electron';
import { join } from 'path';
import { WebSocketClient } from './websocket-client';
import { setupIPCHandlers } from './ipc-handlers';

let mainWindow: BrowserWindow | null = null;
let wsClient: WebSocketClient | null = null;

function createWindow() {
  const { width: screenWidth } = screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width: 800,
    height: 60,
    x: (screenWidth - 800) / 2,
    y: 0,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    movable: true,
    webPreferences: {
      preload: join(__dirname, '../preload/preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Load the app
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173');
    // mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  createWindow();

  if (!mainWindow) {
    throw new Error('Failed to create main window');
  }

  // Initialize WebSocket connection to Python backend
  wsClient = new WebSocketClient('ws://localhost:8000/ws');
  wsClient.connect();

  // Set up IPC handlers
  setupIPCHandlers(wsClient, mainWindow);

  // Forward messages from backend to renderer
  wsClient.on('message', (data) => {
    if (mainWindow) {
      mainWindow.webContents.send('backend-message', data);
    }
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (wsClient) {
    wsClient.disconnect();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Export for IPC handlers
export { mainWindow, wsClient };
