/**
 * Electron main process
 * Supports professor mode (dashboard) and student mode (avatar overlay)
 */
import { app, BrowserWindow, screen, ipcMain, session, systemPreferences, dialog } from 'electron';
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

// App state
let currentRole: 'professor' | 'student' | '' = '';
let backendUrl = 'http://127.0.0.1:8000';
let registeredStudent: { name: string; email: string } | null = null;

// Window states
const STATES = {
  HIDDEN: { width: 0, height: 0, opacity: 0 },
  MINIMIZED: { width: 300, height: 50 },  // Small top-bar indicator
  EXPANDED: { width: 800, height: 600 },  // Full HeyGen avatar view
};

// Professor window size
const PROFESSOR_SIZE = { width: 1200, height: 800 };

let currentState: 'hidden' | 'minimized' | 'expanded' = 'minimized';

function createWindow() {
  const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;

  // Start with expanded size for role selection
  mainWindow = new BrowserWindow({
    width: STATES.EXPANDED.width,
    height: STATES.EXPANDED.height,
    x: Math.floor((screenWidth - STATES.EXPANDED.width) / 2),
    y: Math.floor((screenHeight - STATES.EXPANDED.height) / 2),
    frame: false,
    transparent: true,
    alwaysOnTop: false,
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
      if (currentRole === 'professor') {
        // Professor gets a larger, centered window
        const x = Math.floor((screenWidth - PROFESSOR_SIZE.width) / 2);
        const y = Math.floor((screenHeight - PROFESSOR_SIZE.height) / 2);
        mainWindow.setSize(PROFESSOR_SIZE.width, PROFESSOR_SIZE.height);
        mainWindow.setPosition(x, y);
        mainWindow.setAlwaysOnTop(false);
        mainWindow.setResizable(true);
      } else {
        // Student gets the standard expanded view
        const x = Math.floor((screenWidth - STATES.EXPANDED.width) / 2);
        const y = Math.floor((screenHeight - STATES.EXPANDED.height) / 2);
        mainWindow.setSize(STATES.EXPANDED.width, STATES.EXPANDED.height);
        mainWindow.setPosition(x, y);
        mainWindow.setAlwaysOnTop(true);
      }
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
  const htmlPath = process.env.NODE_ENV === 'development'
    ? join(app.getAppPath(), 'src/electron/renderer/heygen-avatar.html')
    : join(__dirname, '../renderer/heygen-avatar.html');

  // Use configured backendUrl instead of hardcoded localhost
  const url = `file://${htmlPath}?name=${encodeURIComponent(studentName)}&backend=${encodeURIComponent(backendUrl)}`;
  console.log('Loading avatar URL:', url);

  avatarWindow.loadURL(url);

  if (process.env.NODE_ENV === 'development') {
    avatarWindow.webContents.openDevTools({ mode: 'detach' });
  }

  avatarWindow.on('closed', () => {
    avatarWindow = null;
  });

  // Minimize the main window (student mode)
  if (mainWindow && currentRole === 'student') {
    setWindowState('minimized');
  }
}

app.whenReady().then(async () => {
  // Request macOS microphone permission (triggers system prompt)
  if (process.platform === 'darwin') {
    const micStatus = systemPreferences.getMediaAccessStatus('microphone');
    console.log('Microphone permission status:', micStatus);
    if (micStatus !== 'granted') {
      const granted = await systemPreferences.askForMediaAccess('microphone');
      console.log('Microphone access:', granted ? 'granted' : 'denied');
    }
  }

  // Grant web-level media permissions for all origins
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    const allowed = ['media', 'mediaKeySystem', 'audioCapture'];
    callback(allowed.includes(permission));
  });

  session.defaultSession.setPermissionCheckHandler((webContents, permission) => {
    const allowed = ['media', 'mediaKeySystem', 'audioCapture'];
    return allowed.includes(permission);
  });

  createWindow();

  if (!mainWindow) {
    throw new Error('Failed to create main window');
  }

  // Initialize WebSocket connection to Python backend
  const wsUrl = backendUrl.replace('http', 'ws') + '/ws';
  wsClient = new WebSocketClient(wsUrl);
  wsClient.connect();

  // Set up IPC handlers
  setupIPCHandlers(wsClient, mainWindow);

  // ========== Role & Connection IPC ==========

  ipcMain.on('set-role', (event, role: string) => {
    currentRole = role as 'professor' | 'student';
    console.log(`Role set: ${currentRole}`);

    if (currentRole === 'professor') {
      // Switch to professor window mode
      setWindowState('expanded');
    }
  });

  ipcMain.handle('get-role', () => currentRole);

  ipcMain.on('set-backend-url', (event, url: string) => {
    backendUrl = url;
    console.log(`Backend URL set: ${backendUrl}`);

    // Reconnect WebSocket to new backend
    if (wsClient) {
      const newWsUrl = backendUrl.replace('http', 'ws') + '/ws';
      wsClient.reconnect(newWsUrl);
    }
  });

  ipcMain.handle('get-backend-url', () => backendUrl);

  // ========== Directory Picker ==========

  ipcMain.handle('select-directory', async () => {
    if (!mainWindow) return null;
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory'],
      title: 'Select Pipeline Output Directory',
    });
    if (result.canceled || result.filePaths.length === 0) return null;
    return result.filePaths[0];
  });

  // ========== Window State ==========

  ipcMain.on('set-window-state', (event, state: 'hidden' | 'minimized' | 'expanded') => {
    setWindowState(state);
  });

  ipcMain.handle('get-window-state', () => currentState);

  // ========== Backend Message Forwarding ==========

  wsClient.on('message', (data) => {
    if (mainWindow) {
      mainWindow.webContents.send('backend-message', data);

      // Auto-open avatar window on breakout event (student mode)
      if (data.type === 'BREAKOUT_STARTED' || data.type === 'BREAKOUT_ROOM_ASSIGNED') {
        console.log('Breakout room detected! Opening avatar window...');
        openAvatarWindow(registeredStudent?.name || 'Student');
      }

      // Handle explainer video playback for quiz - only if it's for this student
      if (data.type === 'PLAY_EXPLAINER_VIDEO') {
        const targetEmail = data.payload?.student_email;
        const isForMe = !targetEmail || targetEmail === registeredStudent?.email;

        if (isForMe && registeredStudent) {
          console.log('Playing explainer video:', data.payload?.concept);
          if (avatarWindow) {
            avatarWindow.webContents.send('play-explainer-video', data.payload);
          } else {
            openAvatarWindow(registeredStudent?.name || 'Student');
            setTimeout(() => {
              if (avatarWindow) {
                avatarWindow.webContents.send('play-explainer-video', data.payload);
              }
            }, 2000);
          }
        } else if (targetEmail) {
          console.log(`Video is for ${targetEmail}, not me (${registeredStudent?.email})`);
        }
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
