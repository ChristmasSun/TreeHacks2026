/**
 * Standalone launcher for the avatar page.
 * Usage: bun run avatar [name] [backendUrl]
 * Opens the avatar window directly, skipping student registration.
 */
const { app, BrowserWindow, session, systemPreferences } = require('electron');
const { join } = require('path');

const studentName = process.argv.find((a, i) => i > 1 && !a.startsWith('-')) || 'Dev';
const backendUrl = process.argv.find((a, i) => i > 2 && a.startsWith('http')) || 'http://127.0.0.1:8000';

app.whenReady().then(async () => {
  // Request macOS microphone permission
  if (process.platform === 'darwin') {
    const status = systemPreferences.getMediaAccessStatus('microphone');
    console.log('Mic status:', status);
    if (status !== 'granted') {
      const granted = await systemPreferences.askForMediaAccess('microphone');
      console.log('Mic granted:', granted);
    }
  }

  // Grant web-level media permissions
  session.defaultSession.setPermissionRequestHandler((_wc, permission, callback) => {
    callback(['media', 'mediaKeySystem', 'audioCapture'].includes(permission));
  });
  session.defaultSession.setPermissionCheckHandler((_wc, permission) => {
    return ['media', 'mediaKeySystem', 'audioCapture'].includes(permission);
  });

  const win = new BrowserWindow({
    width: 1000,
    height: 700,
    frame: true,
    resizable: true,
    webPreferences: {
      contextIsolation: false,
      nodeIntegration: false,
    },
  });

  const htmlPath = join(__dirname, '..', 'src', 'electron', 'renderer', 'heygen-avatar.html');
  const url = `file://${htmlPath}?name=${encodeURIComponent(studentName)}&backend=${encodeURIComponent(backendUrl)}`;
  console.log('Loading:', url);

  win.loadURL(url);
  win.webContents.openDevTools({ mode: 'detach' });

  win.on('closed', () => app.quit());
});

app.on('window-all-closed', () => app.quit());
