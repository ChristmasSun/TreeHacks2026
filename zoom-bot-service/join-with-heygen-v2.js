/**
 * Zoom Meeting Join with HeyGen Avatar as Camera
 * 
 * This script uses a two-page approach:
 * 1. Page 1: Connects to HeyGen and captures avatar video
 * 2. Page 2: Joins Zoom with the avatar as the camera stream
 * 
 * Usage: 
 *   HEYGEN_API_KEY=your_key node join-with-heygen-v2.js
 */

const { chromium } = require('playwright');
const http = require('http');
require('dotenv').config();

// Meeting details
const MEETING_ID = '89711545987';
const PASSCODE = '926454';
const USER_NAME = 'AI Professor';

// Get HeyGen API key
const HEYGEN_API_KEY = process.env.HEYGEN_API_KEY;

if (!HEYGEN_API_KEY) {
  console.error('❌ Missing HEYGEN_API_KEY environment variable');
  console.error('   Set it via: HEYGEN_API_KEY=your_key node join-with-heygen-v2.js');
  process.exit(1);
}

/**
 * Make HeyGen API request
 */
async function heygenRequest(path, data) {
  const https = require('https');
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(data);
    const options = {
      hostname: 'api.heygen.com',
      port: 443,
      path: '/v1' + path,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': HEYGEN_API_KEY,
        'Content-Length': body.length
      }
    };

    const req = https.request(options, (res) => {
      let result = '';
      res.on('data', chunk => result += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(result);
          resolve(json.data || json);
        } catch (e) {
          reject(new Error(result));
        }
      });
    });

    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function main() {
  console.log('\n🎭 HeyGen Avatar + Zoom Integration v2');
  console.log('='.repeat(45));
  console.log(`Meeting: ${MEETING_ID}`);
  console.log(`Passcode: ${PASSCODE}`);
  console.log(`Name: ${USER_NAME}`);
  console.log('');

  let heygenSessionId = null;
  let server = null;

  try {
    // Step 1: Create HeyGen session
    console.log('🎭 Creating HeyGen avatar session...');
    const session = await heygenRequest('/streaming.new', {
      quality: 'medium',
      video_encoding: 'VP8',
      version: 'v2',
      disable_idle_timeout: true
    });
    
    heygenSessionId = session.session_id;
    console.log(`✅ Session ID: ${heygenSessionId}`);
    console.log(`   LiveKit URL: ${session.url}`);
    console.log('');

    // Step 2: Start the session
    console.log('▶️  Starting HeyGen session...');
    await heygenRequest('/streaming.start', { session_id: heygenSessionId });
    console.log('✅ Session started');
    console.log('');

    // Step 3: Create local HTTP server to serve our HTML pages
    const PORT = 8765;
    server = http.createServer((req, res) => {
      res.writeHead(200, {
        'Content-Type': 'text/html',
        'Access-Control-Allow-Origin': '*'
      });
      
      if (req.url === '/zoom') {
        res.end(createZoomPage());
      } else {
        res.end(createMainPage(session, heygenSessionId));
      }
    });
    
    await new Promise(r => server.listen(PORT, r));
    console.log(`🌐 Server running at http://localhost:${PORT}`);
    console.log('');

    // Step 4: Launch browser
    console.log('🚀 Launching browser...');
    const browser = await chromium.launch({
      headless: false,
      args: [
        '--use-fake-ui-for-media-stream',
        '--use-fake-device-for-media-stream',
        '--autoplay-policy=no-user-gesture-required',
        '--disable-features=WebRtcHideLocalIpsWithMdns',
        '--enable-features=SharedArrayBuffer'
      ]
    });

    const context = await browser.newContext({
      permissions: ['microphone', 'camera'],
      viewport: { width: 1400, height: 900 }
    });

    // Open main page
    const page = await context.newPage();
    
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('[HeyGen]') || text.includes('[Zoom]') || text.includes('Error')) {
        console.log(`[PAGE] ${text}`);
      }
    });

    console.log('📄 Loading HeyGen + Zoom integration page...');
    await page.goto(`http://localhost:${PORT}`, { waitUntil: 'networkidle' });

    // Wait for avatar to connect
    console.log('⏳ Waiting for avatar connection...');
    try {
      await page.waitForFunction(() => window.avatarReady === true, { timeout: 45000 });
      console.log('✅ Avatar connected and ready!');
    } catch (e) {
      console.log('⚠️  Avatar connection timeout - check the browser window');
    }

    console.log('\n📺 Integration page loaded!');
    console.log('   - You should see the HeyGen avatar video');
    console.log('   - Type text and click "Speak" to make avatar talk');
    console.log('   - Click "Join Zoom" when ready');
    console.log('\n   Browser will stay open for 10 minutes...');
    
    await page.waitForTimeout(600000);

  } catch (error) {
    console.error('\n❌ Error:', error.message);
  } finally {
    // Cleanup
    if (heygenSessionId) {
      console.log('\n🔄 Closing HeyGen session...');
      try {
        await heygenRequest('/streaming.stop', { session_id: heygenSessionId });
        console.log('✅ Session closed');
      } catch (e) {}
    }
    if (server) server.close();
  }

  console.log('🛑 Done.');
}

function createMainPage(session, sessionId) {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>HeyGen + Zoom</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      background: #0f0f23;
      color: white;
      min-height: 100vh;
      padding: 20px;
    }
    h1 { font-size: 22px; margin-bottom: 15px; color: #00d4ff; }
    
    .status {
      padding: 12px 16px;
      background: rgba(255,255,255,0.05);
      border-radius: 8px;
      margin-bottom: 15px;
      font-family: monospace;
      font-size: 13px;
    }
    .status.ok { border-left: 3px solid #00ff88; }
    .status.err { border-left: 3px solid #ff4444; }
    .status.wait { border-left: 3px solid #ffaa00; }
    
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px; }
    
    .video-box {
      background: #000;
      border-radius: 10px;
      overflow: hidden;
      position: relative;
      aspect-ratio: 16/9;
    }
    .video-box video {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .video-label {
      position: absolute;
      top: 8px;
      left: 8px;
      background: rgba(0,0,0,0.8);
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 11px;
    }
    
    .controls {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }
    
    input[type="text"] {
      flex: 1;
      min-width: 200px;
      padding: 10px 14px;
      background: rgba(255,255,255,0.1);
      border: 1px solid rgba(255,255,255,0.2);
      border-radius: 6px;
      color: white;
      font-size: 14px;
    }
    input::placeholder { color: rgba(255,255,255,0.4); }
    
    button {
      padding: 10px 20px;
      border: none;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
      font-size: 13px;
      transition: transform 0.1s, opacity 0.1s;
    }
    button:hover { transform: translateY(-1px); }
    button:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
    
    .btn-speak { background: #444; color: white; }
    .btn-join { background: linear-gradient(135deg, #2d8cff, #0066ff); color: white; }
    
    #zoomFrame {
      width: 100%;
      height: 500px;
      border: none;
      border-radius: 10px;
      background: #000;
      display: none;
    }
  </style>
</head>
<body>
  <h1>🎭 HeyGen Avatar → 💻 Zoom Meeting</h1>
  
  <div id="status" class="status wait">Connecting to HeyGen...</div>
  
  <div class="grid">
    <div class="video-box">
      <div class="video-label">HeyGen Avatar Stream</div>
      <video id="avatarVideo" autoplay playsinline></video>
    </div>
    <div class="video-box">
      <div class="video-label">Virtual Camera Output</div>
      <canvas id="outputCanvas"></canvas>
      <video id="outputPreview" autoplay playsinline muted style="display:none;"></video>
    </div>
  </div>
  
  <div class="controls">
    <input type="text" id="speakText" placeholder="Type something for avatar to say..." />
    <button class="btn-speak" onclick="speak()">🗣️ Speak</button>
    <button class="btn-join" id="joinBtn" onclick="openZoom()" disabled>🚀 Join Zoom</button>
  </div>
  
  <br>
  <iframe id="zoomFrame" allow="camera; microphone; display-capture"></iframe>

  <script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
  
  <script>
    const HEYGEN_KEY = '${HEYGEN_API_KEY}';
    const SESSION_ID = '${sessionId}';
    const LIVEKIT_URL = '${session.url}';
    const LIVEKIT_TOKEN = '${session.access_token}';
    const MEETING_ID = '${MEETING_ID}';
    const PASSCODE = '${PASSCODE}';
    const USER_NAME = '${USER_NAME}';
    
    window.avatarReady = false;
    let room = null;
    let avatarVideoTrack = null;
    let outputStream = null;
    
    const statusEl = document.getElementById('status');
    const avatarVideo = document.getElementById('avatarVideo');
    const outputCanvas = document.getElementById('outputCanvas');
    const outputPreview = document.getElementById('outputPreview');
    const joinBtn = document.getElementById('joinBtn');
    
    function setStatus(msg, type = 'wait') {
      statusEl.textContent = msg;
      statusEl.className = 'status ' + type;
      console.log('[HeyGen] ' + msg);
    }
    
    async function connectLiveKit() {
      try {
        setStatus('Creating LiveKit room...');
        
        room = new LivekitClient.Room({
          adaptiveStream: true,
          dynacast: true
        });
        
        room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, pub, participant) => {
          console.log('[HeyGen] Track:', track.kind, 'from', participant.identity);
          
          if (track.kind === 'video') {
            avatarVideoTrack = track;
            track.attach(avatarVideo);
            
            // Setup canvas mirroring
            setupCanvasMirror();
            
            window.avatarReady = true;
            joinBtn.disabled = false;
            setStatus('✅ Avatar connected! Click "Join Zoom" to continue.', 'ok');
          }
          
          if (track.kind === 'audio') {
            // Mute audio to prevent echo, but keep track reference
            const audioEl = track.attach();
            audioEl.muted = true;
          }
        });
        
        room.on(LivekitClient.RoomEvent.Disconnected, () => {
          setStatus('Disconnected from HeyGen', 'err');
          window.avatarReady = false;
        });
        
        setStatus('Connecting to LiveKit room...');
        await room.connect(LIVEKIT_URL, LIVEKIT_TOKEN);
        setStatus('Connected! Waiting for avatar video track...', 'wait');
        
      } catch (err) {
        console.error('[HeyGen] Error:', err);
        setStatus('Connection failed: ' + err.message, 'err');
      }
    }
    
    function setupCanvasMirror() {
      const ctx = outputCanvas.getContext('2d');
      
      function draw() {
        if (avatarVideo.videoWidth > 0) {
          outputCanvas.width = avatarVideo.videoWidth;
          outputCanvas.height = avatarVideo.videoHeight;
          ctx.drawImage(avatarVideo, 0, 0);
        }
        requestAnimationFrame(draw);
      }
      draw();
      
      // Create stream from canvas
      outputStream = outputCanvas.captureStream(30);
      outputPreview.srcObject = outputStream;
      
      // Override getUserMedia to return our stream
      const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      navigator.mediaDevices.getUserMedia = async (constraints) => {
        console.log('[HeyGen] getUserMedia intercepted:', constraints);
        
        if (constraints.video && outputStream) {
          // Return avatar video stream
          const tracks = [];
          
          if (constraints.video) {
            tracks.push(...outputStream.getVideoTracks());
          }
          
          if (constraints.audio) {
            // Get real audio from mic
            try {
              const audioStream = await originalGetUserMedia({ audio: true });
              tracks.push(...audioStream.getAudioTracks());
            } catch (e) {
              console.log('[HeyGen] No mic available');
            }
          }
          
          return new MediaStream(tracks);
        }
        
        return originalGetUserMedia(constraints);
      };
      
      console.log('[HeyGen] Canvas mirror and getUserMedia override ready');
    }
    
    async function speak() {
      const text = document.getElementById('speakText').value.trim();
      if (!text) return;
      
      try {
        setStatus('Avatar speaking...', 'wait');
        
        const res = await fetch('https://api.heygen.com/v1/streaming.task', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': HEYGEN_KEY
          },
          body: JSON.stringify({
            session_id: SESSION_ID,
            text: text,
            task_type: 'talk'
          })
        });
        
        const data = await res.json();
        console.log('[HeyGen] Speak response:', data);
        
        document.getElementById('speakText').value = '';
        setStatus('✅ Avatar speaking! Ready for Zoom.', 'ok');
        
      } catch (err) {
        console.error('[HeyGen] Speak error:', err);
        setStatus('Speak failed: ' + err.message, 'err');
      }
    }
    
    function openZoom() {
      setStatus('Opening Zoom web client...', 'wait');
      
      // Open Zoom in iframe (same origin won't work, but we can try)
      // Actually let's open in a new window
      const zoomUrl = 'https://zoom.us/wc/join/' + MEETING_ID;
      
      // Open in new window - the getUserMedia override should work
      window.open(zoomUrl, 'zoom', 'width=1200,height=800');
      
      setStatus('✅ Zoom window opened! Use the avatar as your camera.', 'ok');
    }
    
    // Enter key to speak
    document.getElementById('speakText').addEventListener('keypress', e => {
      if (e.key === 'Enter') speak();
    });
    
    // Start
    connectLiveKit();
  </script>
</body>
</html>`;
}

function createZoomPage() {
  return `<!DOCTYPE html>
<html>
<head><title>Zoom Join</title></head>
<body>
  <script>
    // Redirect to Zoom
    window.location.href = 'https://zoom.us/wc/join/${MEETING_ID}';
  </script>
</body>
</html>`;
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
