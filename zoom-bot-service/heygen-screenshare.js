/**
 * HeyGen Avatar + Zoom via Screen Share
 * 
 * This bot:
 * 1. Opens HeyGen avatar in one tab
 * 2. Joins Zoom as a guest in another tab
 * 3. Shares the HeyGen tab as screen
 * 
 * Usage: node heygen-screenshare.js
 */

const { chromium } = require('playwright');
const http = require('http');
require('dotenv').config();

const HEYGEN_API_KEY = process.env.HEYGEN_API_KEY;
const MEETING_ID = process.env.ZOOM_MEETING_ID || '89711545987';
const PASSCODE = process.env.ZOOM_PASSCODE || '926454';
const BOT_NAME = process.env.BOT_NAME || 'AI Professor';

if (!HEYGEN_API_KEY) {
  console.error('❌ Add HEYGEN_API_KEY to .env file');
  process.exit(1);
}

async function heygenAPI(endpoint, data) {
  const https = require('https');
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(data);
    const req = https.request({
      hostname: 'api.heygen.com',
      path: '/v1' + endpoint,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': HEYGEN_API_KEY,
        'Content-Length': body.length
      }
    }, res => {
      let result = '';
      res.on('data', c => result += c);
      res.on('end', () => {
        try {
          const j = JSON.parse(result);
          if (j.error) reject(new Error(JSON.stringify(j.error)));
          else resolve(j.data || j);
        } catch { reject(new Error(result)); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function main() {
  console.log('\n🎭 HeyGen Avatar + Zoom Screen Share');
  console.log('═'.repeat(45));

  let sessionId = null;
  let server = null;
  let browser = null;

  try {
    // 1. Create HeyGen session
    console.log('📡 Creating HeyGen session...');
    const session = await heygenAPI('/streaming.new', {
      quality: 'high',
      video_encoding: 'VP8',
      version: 'v2',
      disable_idle_timeout: true
    });
    sessionId = session.session_id;
    console.log('   ✓ Session created');

    await heygenAPI('/streaming.start', { session_id: sessionId });
    console.log('   ✓ Session started');

    // 2. Start server for HeyGen page
    const PORT = 8765;
    server = http.createServer((req, res) => {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(heygenPageHTML(session, sessionId, HEYGEN_API_KEY));
    });
    await new Promise(r => server.listen(PORT, r));
    console.log(`   ✓ HeyGen server at http://localhost:${PORT}`);

    // 3. Launch browser
    console.log('\n🚀 Launching browser...');
    browser = await chromium.launch({
      headless: false,
      args: [
        '--use-fake-ui-for-media-stream',
        '--use-fake-device-for-media-stream',
        '--auto-select-desktop-capture-source=HeyGen Avatar',
        '--enable-usermedia-screen-capturing',
        '--allow-http-screen-capture',
        '--autoplay-policy=no-user-gesture-required'
      ]
    });

    const context = await browser.newContext({
      permissions: ['microphone', 'camera'],
      viewport: { width: 1280, height: 720 }
    });

    // 4. Open HeyGen page first
    console.log('\n📺 Opening HeyGen avatar page...');
    const heygenPage = await context.newPage();
    heygenPage.on('console', msg => {
      if (msg.text().includes('[HeyGen]')) console.log(`   ${msg.text()}`);
    });
    await heygenPage.goto(`http://localhost:${PORT}`, { waitUntil: 'domcontentloaded' });

    // Wait for avatar to connect
    console.log('   Waiting for avatar...');
    try {
      await heygenPage.waitForFunction(() => window.__avatarReady === true, { timeout: 45000 });
      console.log('   ✓ Avatar connected!');
    } catch {
      console.log('   ⚠️ Avatar timeout, continuing anyway...');
    }

    // 5. Open Zoom in new tab
    console.log('\n🔗 Opening Zoom...');
    const zoomPage = await context.newPage();
    zoomPage.on('console', msg => {
      if (msg.type() === 'error') console.log(`   [Zoom] ${msg.text()}`);
    });

    const zoomUrl = `https://zoom.us/wc/join/${MEETING_ID}`;
    await zoomPage.goto(zoomUrl, { waitUntil: 'domcontentloaded' });
    await zoomPage.waitForTimeout(3000);

    // Fill in name
    console.log('   Filling join form...');
    try {
      const nameInput = await zoomPage.waitForSelector('input[name="name"], input#inputname, input[placeholder*="name" i]', { timeout: 10000 });
      await nameInput.fill(BOT_NAME);
      console.log(`   ✓ Name: ${BOT_NAME}`);
    } catch {
      console.log('   ⚠️ Name field not found');
    }

    // Fill passcode
    try {
      const pwdInput = await zoomPage.waitForSelector('input[type="password"], input#inputpasscode', { timeout: 5000 });
      await pwdInput.fill(PASSCODE);
      console.log('   ✓ Passcode entered');
    } catch {}

    // Click join
    try {
      const joinBtn = await zoomPage.waitForSelector('button:has-text("Join"), button[type="submit"]', { timeout: 5000 });
      await joinBtn.click();
      console.log('   ✓ Clicked Join');
    } catch {}

    await zoomPage.waitForTimeout(5000);

    // Look for "join from browser" link
    try {
      const browserLink = await zoomPage.waitForSelector('a:has-text("Join from Your Browser"), a:has-text("join from your browser")', { timeout: 10000 });
      await browserLink.click();
      console.log('   ✓ Clicked "Join from Browser"');
      await zoomPage.waitForTimeout(5000);
    } catch {
      console.log('   Already in web client');
    }

    // 6. Now try to share screen
    console.log('\n📺 Attempting to share screen...');
    console.log('   Looking for share button...');
    
    await zoomPage.waitForTimeout(5000);
    
    // Try to find and click share screen button
    const shareSelectors = [
      'button[aria-label*="Share"]',
      'button[aria-label*="share"]',
      'button:has-text("Share Screen")',
      'button:has-text("Share")',
      '.sharing-entry-button',
      '[data-tooltip*="Share"]'
    ];

    for (const sel of shareSelectors) {
      try {
        const btn = await zoomPage.waitForSelector(sel, { timeout: 3000 });
        if (btn) {
          await btn.click();
          console.log(`   ✓ Clicked share button: ${sel}`);
          break;
        }
      } catch {}
    }

    // Print instructions
    console.log('\n' + '═'.repeat(45));
    console.log('🎬 SETUP COMPLETE!');
    console.log('');
    console.log('To share the HeyGen avatar in Zoom:');
    console.log('  1. In the Zoom tab, click "Share Screen"');
    console.log('  2. Select "Chrome Tab" or "Browser Tab"');
    console.log('  3. Choose the "HeyGen Avatar" tab');
    console.log('  4. Check "Share audio" if you want avatar sound');
    console.log('  5. Click Share');
    console.log('');
    console.log('The HeyGen tab is open - type to make avatar speak!');
    console.log('═'.repeat(45));

    // Bring HeyGen tab to focus so user can interact
    await heygenPage.bringToFront();

    console.log('\nBrowser stays open for 30 minutes...');
    console.log('Press Ctrl+C to stop\n');

    await zoomPage.waitForTimeout(1800000);

  } catch (err) {
    console.error('\n❌ Error:', err.message);
  } finally {
    if (sessionId) {
      console.log('\nClosing HeyGen session...');
      try { await heygenAPI('/streaming.stop', { session_id: sessionId }); } catch {}
    }
    if (browser) await browser.close();
    if (server) server.close();
  }

  console.log('Done.');
}

function heygenPageHTML(session, sessionId, apiKey) {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>HeyGen Avatar</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #000;
      display: flex;
      flex-direction: column;
      height: 100vh;
      font-family: system-ui, sans-serif;
    }
    
    #videoContainer {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    
    #avatarVideo {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
    }
    
    .controls {
      padding: 15px;
      background: #16213e;
      display: flex;
      gap: 10px;
    }
    
    input {
      flex: 1;
      padding: 12px 15px;
      background: #0f3460;
      border: 1px solid #1a3a5c;
      border-radius: 8px;
      color: white;
      font-size: 14px;
    }
    input::placeholder { color: rgba(255,255,255,0.4); }
    
    button {
      padding: 12px 24px;
      background: linear-gradient(135deg, #e94560, #ff6b6b);
      border: none;
      border-radius: 8px;
      color: white;
      font-weight: 600;
      cursor: pointer;
      font-size: 14px;
    }
    button:hover { opacity: 0.9; }
    
    #status {
      position: fixed;
      top: 10px;
      left: 10px;
      padding: 8px 14px;
      background: rgba(0,0,0,0.8);
      color: #0f0;
      font-family: monospace;
      font-size: 12px;
      border-radius: 6px;
    }
  </style>
</head>
<body>
  <div id="status">Connecting...</div>
  <div id="videoContainer">
    <video id="avatarVideo" autoplay playsinline></video>
  </div>
  <div class="controls">
    <input type="text" id="speakInput" placeholder="Type something for the avatar to say..." />
    <button onclick="speak()">🗣️ Speak</button>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
  <script>
    window.__avatarReady = false;
    
    const API_KEY = '${apiKey}';
    const SESSION_ID = '${sessionId}';
    const LK_URL = '${session.url}';
    const LK_TOKEN = '${session.access_token}';
    
    const statusEl = document.getElementById('status');
    const avatarVideo = document.getElementById('avatarVideo');
    
    function setStatus(msg) {
      statusEl.textContent = msg;
      console.log('[HeyGen] ' + msg);
    }
    
    async function connect() {
      try {
        const room = new LivekitClient.Room();
        
        room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, pub, participant) => {
          console.log('[HeyGen] Track:', track.kind);
          if (track.kind === 'video') {
            track.attach(avatarVideo);
            window.__avatarReady = true;
            setStatus('✓ Avatar Ready');
          }
          if (track.kind === 'audio') {
            const audio = track.attach();
            audio.volume = 0.5;
          }
        });
        
        room.on(LivekitClient.RoomEvent.Disconnected, () => setStatus('Disconnected'));
        
        setStatus('Connecting...');
        await room.connect(LK_URL, LK_TOKEN);
        setStatus('Waiting for avatar...');
        
      } catch (err) {
        setStatus('Error: ' + err.message);
      }
    }
    
    async function speak() {
      const text = document.getElementById('speakInput').value.trim();
      if (!text) return;
      
      try {
        setStatus('Speaking...');
        await fetch('https://api.heygen.com/v1/streaming.task', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'x-api-key': API_KEY },
          body: JSON.stringify({ session_id: SESSION_ID, text, task_type: 'talk' })
        });
        document.getElementById('speakInput').value = '';
        setStatus('✓ Speaking');
      } catch (err) {
        setStatus('Error: ' + err.message);
      }
    }
    
    document.getElementById('speakInput').addEventListener('keypress', e => {
      if (e.key === 'Enter') speak();
    });
    
    connect();
  </script>
</body>
</html>`;
}

main();
