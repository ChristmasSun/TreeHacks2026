/**
 * Electron main process
 * Starts as invisible overlay, expands when breakout room is detected
 */
import { app, BrowserWindow, screen, ipcMain } from 'electron';
import { join } from 'path';
import { WebSocketClient } from './websocket-client';
import { setupIPCHandlers } from './ipc-handlers';

// Prevent uncaught exceptions from crashing the app
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled rejection at:', promise, 'reason:', reason);
});

let mainWindow: BrowserWindow | null = null;
let avatarWindow: BrowserWindow | null = null;
let wsClient: WebSocketClient | null = null;

// Registered student info
let registeredStudent: { name: string; email: string } | null = null;

// Window states
const STATES = {
  HIDDEN: { width: 0, height: 0, opacity: 0 },
  MINIMIZED: { width: 300, height: 50 },  // Small top-bar indicator
  EXPANDED: { width: 800, height: 600 },  // Full HeyGen avatar view
};

let currentState: 'hidden' | 'minimized' | 'expanded' = 'minimized';

function createWindow() {
  const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width: STATES.MINIMIZED.width,
    height: STATES.MINIMIZED.height,
    x: screenWidth - STATES.MINIMIZED.width - 20,
    y: 20,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    movable: true,
    skipTaskbar: false,
    webPreferences: {
      preload: join(__dirname, '../preload/preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Load the app
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Window state management
function setWindowState(state: 'hidden' | 'minimized' | 'expanded') {
  if (!mainWindow) return;
  
  const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;
  currentState = state;

  switch (state) {
    case 'hidden':
      mainWindow.hide();
      break;
      
    case 'minimized':
      mainWindow.setSize(STATES.MINIMIZED.width, STATES.MINIMIZED.height);
      mainWindow.setPosition(screenWidth - STATES.MINIMIZED.width - 20, 20);
      mainWindow.setAlwaysOnTop(true);
      mainWindow.show();
      break;
      
    case 'expanded':
      // Center the expanded window
      const x = Math.floor((screenWidth - STATES.EXPANDED.width) / 2);
      const y = Math.floor((screenHeight - STATES.EXPANDED.height) / 2);
      mainWindow.setSize(STATES.EXPANDED.width, STATES.EXPANDED.height);
      mainWindow.setPosition(x, y);
      mainWindow.setAlwaysOnTop(true);
      mainWindow.show();
      mainWindow.focus();
      break;
  }
  
  // Notify renderer of state change
  mainWindow.webContents.send('window-state-changed', state);
}

// Open avatar window with HeyGen SDK
function openAvatarWindow(studentName: string) {
  if (avatarWindow) {
    avatarWindow.focus();
    return;
  }

  const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;
  
  avatarWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    x: Math.floor((screenWidth - 1000) / 2),
    y: Math.floor((screenHeight - 700) / 2),
    frame: true,
    resizable: true,
    webPreferences: {
      contextIsolation: false,
      nodeIntegration: false,
    },
  });

  // Load the static HTML file with HeyGen SDK
  // In dev: __dirname is out/main, HTML is in src/electron/renderer
  // In prod: __dirname is resources/app/out/main, HTML should be in resources/app/out/renderer
  const htmlPath = process.env.NODE_ENV === 'development'
    ? join(app.getAppPath(), 'src/electron/renderer/heygen-avatar.html')
    : join(__dirname, '../renderer/heygen-avatar.html');
  
  const url = `file://${htmlPath}?name=${encodeURIComponent(studentName)}&backend=http://127.0.0.1:8000`;
  console.log('Loading avatar URL:', url);
  
  avatarWindow.loadURL(url);
  
  if (process.env.NODE_ENV === 'development') {
    avatarWindow.webContents.openDevTools({ mode: 'detach' });
  }

  avatarWindow.on('closed', () => {
    avatarWindow = null;
  });

  // Minimize the main window
  if (mainWindow) {
    setWindowState('minimized');
  }
}

app.whenReady().then(() => {
  createWindow();

  if (!mainWindow) {
    throw new Error('Failed to create main window');
  }

  // Initialize WebSocket connection to Python backend
  // Use 127.0.0.1 explicitly to avoid IPv6 resolution issues
  wsClient = new WebSocketClient('ws://127.0.0.1:8000/ws');
  wsClient.connect();

  // Set up IPC handlers
  setupIPCHandlers(wsClient, mainWindow);

  // Handle window state changes from renderer
  ipcMain.on('set-window-state', (event, state: 'hidden' | 'minimized' | 'expanded') => {
    setWindowState(state);
  });
  
  ipcMain.handle('get-window-state', () => currentState);

  // Forward messages from backend to renderer
  wsClient.on('message', (data) => {
    if (mainWindow) {
      mainWindow.webContents.send('backend-message', data);

      // Auto-expand on breakout room event
      if (data.type === 'BREAKOUT_STARTED' || data.type === 'BREAKOUT_ROOM_ASSIGNED') {
        console.log('📢 Breakout room detected! Opening avatar window...');
        openAvatarWindow(registeredStudent?.name || 'Student');
      }

      // Handle explainer video playback for quiz
      if (data.type === 'PLAY_EXPLAINER_VIDEO') {
        console.log('🎬 Playing explainer video:', data.payload?.concept);
        // Forward to avatar window if it exists
        if (avatarWindow) {
          avatarWindow.webContents.send('play-explainer-video', data.payload);
        } else {
          // Open avatar window first, then play video
          openAvatarWindow(registeredStudent?.name || 'Student');
          // Wait for window to load, then send message
          setTimeout(() => {
            if (avatarWindow) {
              avatarWindow.webContents.send('play-explainer-video', data.payload);
            }
          }, 2000);
        }
      }

      // Store registered student info
      if (data.type === 'REGISTRATION_SUCCESS') {
        // Student info will be stored via IPC
      }
    }
  });
  
  // Handle student registration from renderer
  ipcMain.on('student-registered', (event, student: { name: string; email: string }) => {
    registeredStudent = student;
    console.log('Student registered:', student.name);
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
export { mainWindow, wsClient, setWindowState };
