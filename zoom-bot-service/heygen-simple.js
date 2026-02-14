/**
 * HeyGen Avatar + Zoom - Simple Single Window Version
 * 
 * Opens ONE browser window with:
 * - HeyGen avatar on the left
 * - Zoom join on the right  
 * - You control everything manually
 * 
 * Usage: node heygen-simple.js
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
  console.log('\n🎭 HeyGen + Zoom (Simple Version)');
  console.log('═'.repeat(40));

  let sessionId = null;
  let server = null;
  let browser = null;

  try {
    // 1. Create HeyGen session
    console.log('Creating HeyGen session...');
    const session = await heygenAPI('/streaming.new', {
      quality: 'medium',
      video_encoding: 'VP8',
      version: 'v2',
      disable_idle_timeout: true
    });
    sessionId = session.session_id;
    console.log('✅ HeyGen session created');

    // 2. Start session
    await heygenAPI('/streaming.start', { session_id: sessionId });
    console.log('✅ HeyGen session started');

    // 3. Start local server
    const PORT = 8888;
    server = http.createServer((req, res) => {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(createHTML(session, sessionId, MEETING_ID, PASSCODE, BOT_NAME, HEYGEN_API_KEY));
    });
    await new Promise(r => server.listen(PORT, r));
    console.log(`✅ Server at http://localhost:${PORT}`);

    // 4. Open browser
    console.log('Opening browser...');
    browser = await chromium.launch({
      headless: false,
      args: [
        '--use-fake-ui-for-media-stream',
        '--use-fake-device-for-media-stream',
        '--autoplay-policy=no-user-gesture-required'  
      ]
    });

    const context = await browser.newContext({
      permissions: ['microphone', 'camera'],
      viewport: { width: 1400, height: 900 }
    });

    const page = await context.newPage();
    
    page.on('console', msg => {
      const t = msg.text();
      if (t.includes('[') || msg.type() === 'error') {
        console.log(`[Browser] ${t}`);
      }
    });

    await page.goto(`http://localhost:${PORT}`);
    
    console.log('\n' + '═'.repeat(40));
    console.log('🎬 BROWSER OPEN!');
    console.log('');
    console.log('What you see:');
    console.log('  LEFT: HeyGen avatar (should appear shortly)');
    console.log('  RIGHT: Zoom join (in iframe)');
    console.log('');
    console.log('Try:');
    console.log('  - Type text and click "Speak" to make avatar talk');
    console.log('  - Use Zoom controls on the right to join meeting');
    console.log('═'.repeat(40));
    console.log('\nPress Ctrl+C to stop\n');

    // Keep running
    await page.waitForTimeout(1800000); // 30 min

  } catch (err) {
    console.error('❌ Error:', err.message);
  } finally {
    if (sessionId) {
      console.log('Closing HeyGen session...');
      try { await heygenAPI('/streaming.stop', { session_id: sessionId }); } catch {}
    }
    if (browser) await browser.close();
    if (server) server.close();
  }
}

function createHTML(session, sessionId, meetingId, passcode, botName, apiKey) {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>HeyGen + Zoom</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { 
      font-family: system-ui, sans-serif; 
      background: #1a1a2e; 
      color: white; 
      height: 100vh;
      display: flex;
      flex-direction: column;
    }
    
    .header {
      padding: 12px 20px;
      background: #16213e;
      border-bottom: 1px solid #0f3460;
      display: flex;
      align-items: center;
      gap: 15px;
    }
    .header h1 { font-size: 18px; color: #00d9ff; }
    .header .status { 
      font-size: 12px; 
      padding: 4px 10px; 
      background: #0f3460; 
      border-radius: 4px;
      font-family: monospace;
    }
    .header .status.ok { background: #0a4d32; }
    .header .status.err { background: #4d1a1a; }
    
    .main {
      flex: 1;
      display: flex;
      overflow: hidden;
    }
    
    .panel {
      flex: 1;
      display: flex;
      flex-direction: column;
      border-right: 1px solid #0f3460;
    }
    .panel:last-child { border-right: none; }
    
    .panel-header {
      padding: 10px 15px;
      background: #0f3460;
      font-size: 13px;
      font-weight: 600;
    }
    
    .panel-content {
      flex: 1;
      display: flex;
      flex-direction: column;
    }
    
    /* HeyGen Panel */
    #avatarVideo {
      flex: 1;
      background: #000;
      object-fit: contain;
    }
    
    .speak-controls {
      padding: 10px;
      background: #16213e;
      display: flex;
      gap: 8px;
    }
    .speak-controls input {
      flex: 1;
      padding: 10px 12px;
      background: #0f3460;
      border: 1px solid #1a3a5c;
      border-radius: 6px;
      color: white;
      font-size: 13px;
    }
    .speak-controls button {
      padding: 10px 16px;
      background: #e94560;
      border: none;
      border-radius: 6px;
      color: white;
      font-weight: 600;
      cursor: pointer;
    }
    .speak-controls button:hover { background: #ff6b6b; }
    
    /* Zoom Panel */
    #zoomFrame {
      flex: 1;
      border: none;
      background: #000;
    }
    
    .zoom-info {
      padding: 10px 15px;
      background: #16213e;
      font-size: 12px;
      font-family: monospace;
    }
    .zoom-info strong { color: #00d9ff; }
  </style>
</head>
<body>
  <div class="header">
    <h1>🎭 HeyGen + 💻 Zoom</h1>
    <div id="status" class="status">Connecting to HeyGen...</div>
  </div>
  
  <div class="main">
    <!-- HeyGen Panel -->
    <div class="panel">
      <div class="panel-header">🎭 HeyGen Avatar</div>
      <div class="panel-content">
        <video id="avatarVideo" autoplay playsinline></video>
        <div class="speak-controls">
          <input type="text" id="speakInput" placeholder="Type something for avatar to say..." />
          <button onclick="speak()">🗣 Speak</button>
        </div>
      </div>
    </div>
    
    <!-- Zoom Panel -->
    <div class="panel">
      <div class="panel-header">💻 Zoom Meeting</div>
      <div class="panel-content">
        <div class="zoom-info">
          <strong>Meeting:</strong> ${meetingId} &nbsp;|&nbsp; 
          <strong>Passcode:</strong> ${passcode} &nbsp;|&nbsp;
          <strong>Name:</strong> ${botName}
        </div>
        <iframe id="zoomFrame" 
                src="https://zoom.us/wc/join/${meetingId}?pwd=${passcode}" 
                allow="camera; microphone; display-capture; autoplay; clipboard-write">
        </iframe>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
  <script>
    const API_KEY = '${apiKey}';
    const SESSION_ID = '${sessionId}';
    const LK_URL = '${session.url}';
    const LK_TOKEN = '${session.access_token}';
    
    const statusEl = document.getElementById('status');
    const avatarVideo = document.getElementById('avatarVideo');
    
    function setStatus(msg, ok = false) {
      statusEl.textContent = msg;
      statusEl.className = 'status' + (ok ? ' ok' : '');
      console.log('[Status] ' + msg);
    }
    
    async function connectHeyGen() {
      try {
        const room = new LivekitClient.Room();
        
        room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, pub, participant) => {
          console.log('[HeyGen] Track:', track.kind, 'from', participant.identity);
          if (track.kind === 'video') {
            track.attach(avatarVideo);
            setStatus('✅ Avatar connected!', true);
          }
          if (track.kind === 'audio') {
            // Attach audio but muted initially to prevent feedback
            const audioEl = track.attach();
            audioEl.volume = 0.3; // Lower volume
          }
        });
        
        room.on(LivekitClient.RoomEvent.Disconnected, () => {
          setStatus('❌ HeyGen disconnected');
        });
        
        setStatus('Connecting to LiveKit...');
        await room.connect(LK_URL, LK_TOKEN);
        setStatus('Connected, waiting for avatar...');
        
      } catch (err) {
        console.error('[HeyGen] Error:', err);
        setStatus('❌ ' + err.message);
      }
    }
    
    async function speak() {
      const text = document.getElementById('speakInput').value.trim();
      if (!text) return;
      
      try {
        setStatus('Speaking...');
        const res = await fetch('https://api.heygen.com/v1/streaming.task', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'x-api-key': API_KEY },
          body: JSON.stringify({ session_id: SESSION_ID, text, task_type: 'talk' })
        });
        const data = await res.json();
        console.log('[Speak]', data);
        document.getElementById('speakInput').value = '';
        setStatus('✅ Avatar speaking!', true);
      } catch (err) {
        setStatus('❌ Speak failed: ' + err.message);
      }
    }
    
    // Enter to speak
    document.getElementById('speakInput').addEventListener('keypress', e => {
      if (e.key === 'Enter') speak();
    });
    
    // Start
    connectHeyGen();
  </script>
</body>
</html>`;
}

main();
