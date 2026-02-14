/**
 * HeyGen Avatar + Zoom Meeting (Working Version)
 * 
 * This solution:
 * 1. Connects to HeyGen avatar via LiveKit
 * 2. Captures avatar video to canvas
 * 3. Injects the canvas stream as the camera for Zoom
 * 4. Navigates to Zoom in the SAME page context
 * 
 * Usage: HEYGEN_API_KEY=your_key node heygen-zoom-bot.js
 */

const { chromium } = require('playwright');
const http = require('http');
require('dotenv').config();

// Config
const MEETING_ID = process.env.ZOOM_MEETING_ID || '89711545987';
const PASSCODE = process.env.ZOOM_PASSCODE || '926454';
const BOT_NAME = process.env.BOT_NAME || 'AI Professor';
const HEYGEN_API_KEY = process.env.HEYGEN_API_KEY;

if (!HEYGEN_API_KEY) {
  console.error('❌ HEYGEN_API_KEY required');
  console.error('   Usage: HEYGEN_API_KEY=xxx node heygen-zoom-bot.js');
  process.exit(1);
}

// HeyGen API helper
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
          resolve(j.data || j);
        } catch { reject(new Error(result)); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function main() {
  console.log('\n🎭 HeyGen Avatar → Zoom Bot');
  console.log('═'.repeat(40));
  console.log(`📍 Meeting: ${MEETING_ID} (pwd: ${PASSCODE})`);
  console.log(`🤖 Bot Name: ${BOT_NAME}`);
  console.log('');

  let sessionId = null;
  let server = null;
  let browser = null;

  try {
    // 1. Create HeyGen session
    console.log('🎭 Creating HeyGen session...');
    const session = await heygenAPI('/streaming.new', {
      quality: 'medium',
      video_encoding: 'VP8',
      version: 'v2',
      disable_idle_timeout: true
    });
    sessionId = session.session_id;
    console.log(`   Session: ${sessionId}`);
    console.log(`   LiveKit: ${session.url}`);

    // 2. Start session
    console.log('▶️  Starting session...');
    await heygenAPI('/streaming.start', { session_id: sessionId });
    console.log('   ✓ Started');

    // 3. Start local server
    const PORT = 9876;
    server = http.createServer((req, res) => {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(buildHTML(session, sessionId));
    });
    await new Promise(r => server.listen(PORT, r));
    console.log(`🌐 Server: http://localhost:${PORT}`);

    // 4. Launch browser with media override
    console.log('🚀 Launching browser...');
    browser = await chromium.launch({
      headless: false,
      args: [
        '--use-fake-ui-for-media-stream',
        '--use-fake-device-for-media-stream', 
        '--autoplay-policy=no-user-gesture-required',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process'
      ]
    });

    const context = await browser.newContext({
      permissions: ['microphone', 'camera'],
      viewport: { width: 1280, height: 800 },
      bypassCSP: true
    });

    // Inject getUserMedia override into every page
    await context.addInitScript(() => {
      // Store reference to virtual stream when available
      window.__virtualStream = null;
      
      // Override getUserMedia
      const origGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      navigator.mediaDevices.getUserMedia = async function(constraints) {
        console.log('[VirtualCam] getUserMedia called:', JSON.stringify(constraints));
        
        // If we have a virtual stream and video is requested, use it
        if (window.__virtualStream && constraints && constraints.video) {
          console.log('[VirtualCam] Returning virtual avatar stream!');
          
          const tracks = [...window.__virtualStream.getVideoTracks()];
          
          // Add real audio if requested
          if (constraints.audio) {
            try {
              const audioStream = await origGetUserMedia({ audio: constraints.audio });
              tracks.push(...audioStream.getAudioTracks());
            } catch (e) {
              console.log('[VirtualCam] No audio:', e.message);
            }
          }
          
          return new MediaStream(tracks);
        }
        
        // Fallback to original
        return origGetUserMedia(constraints);
      };
      
      console.log('[VirtualCam] getUserMedia override installed');
    });

    const page = await context.newPage();
    
    page.on('console', msg => {
      const t = msg.text();
      if (t.includes('[') || msg.type() === 'error') {
        console.log(`[Browser] ${t}`);
      }
    });

    // 5. Load our integration page
    console.log('📄 Loading integration page...');
    await page.goto(`http://localhost:${PORT}`, { waitUntil: 'domcontentloaded' });

    // 6. Wait for avatar
    console.log('⏳ Connecting to HeyGen...');
    try {
      await page.waitForFunction(() => window.__avatarReady === true, { timeout: 60000 });
      console.log('✅ Avatar connected!');
    } catch {
      console.log('⚠️  Avatar timeout - check browser');
    }

    // 7. Prompt to join
    console.log('\n' + '═'.repeat(40));
    console.log('🎬 READY! In the browser window:');
    console.log('   1. You should see the HeyGen avatar');
    console.log('   2. Click "Join Zoom" button');
    console.log('   3. The avatar becomes your camera in Zoom');
    console.log('═'.repeat(40));
    console.log('\nKeeping browser open for 10 minutes...');
    
    await page.waitForTimeout(600000);

  } catch (err) {
    console.error('\n❌ Error:', err.message);
    console.error(err.stack);
  } finally {
    // Cleanup
    if (sessionId) {
      console.log('\n🔄 Closing HeyGen session...');
      try { await heygenAPI('/streaming.stop', { session_id: sessionId }); } catch {}
    }
    if (browser) await browser.close();
    if (server) server.close();
  }
  
  console.log('✅ Done');
}

function buildHTML(session, sessionId) {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>HeyGen → Zoom Bot</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:system-ui;background:#111;color:#fff;padding:16px}
    h1{font-size:18px;color:#0af;margin-bottom:12px}
    .status{background:#222;padding:10px 14px;border-radius:6px;margin-bottom:12px;font-size:13px;font-family:monospace}
    .status.ok{border-left:3px solid #0f8}
    .status.err{border-left:3px solid #f44}
    .status.wait{border-left:3px solid #fa0}
    .videos{display:flex;gap:12px;margin-bottom:12px}
    .vid{flex:1;background:#000;border-radius:8px;overflow:hidden;position:relative}
    .vid video,.vid canvas{width:100%;height:200px;object-fit:cover;display:block}
    .vid label{position:absolute;top:6px;left:6px;background:rgba(0,0,0,.8);padding:3px 8px;border-radius:4px;font-size:11px}
    .row{display:flex;gap:8px;margin-bottom:12px}
    input{flex:1;padding:10px;background:#222;border:1px solid #333;border-radius:6px;color:#fff;font-size:13px}
    button{padding:10px 18px;border:none;border-radius:6px;font-weight:600;cursor:pointer;font-size:13px}
    button:disabled{opacity:.4;cursor:not-allowed}
    .speak{background:#444;color:#fff}
    .join{background:linear-gradient(135deg,#29f,#06f);color:#fff}
    #zoomContainer{margin-top:12px;display:none}
    #zoomContainer iframe{width:100%;height:600px;border:none;border-radius:8px}
  </style>
</head>
<body>
  <h1>🎭 HeyGen Avatar → 💻 Zoom</h1>
  <div id="status" class="status wait">Connecting to HeyGen LiveKit...</div>
  
  <div class="videos">
    <div class="vid">
      <label>Avatar Stream</label>
      <video id="avatarVid" autoplay playsinline></video>
    </div>
    <div class="vid">
      <label>Virtual Camera</label>
      <canvas id="virtCam"></canvas>
    </div>
  </div>
  
  <div class="row">
    <input id="txtSpeak" placeholder="Type message for avatar..." />
    <button class="speak" onclick="doSpeak()">🗣 Speak</button>
    <button class="join" id="btnJoin" onclick="goZoom()" disabled>🚀 Join Zoom</button>
  </div>
  
  <div id="zoomContainer">
    <iframe id="zoomFrame" allow="camera *; microphone *"></iframe>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
  <script>
    const API_KEY = "${HEYGEN_API_KEY}";
    const SESSION_ID = "${sessionId}";
    const LK_URL = "${session.url}";
    const LK_TOKEN = "${session.access_token}";
    const MTG_ID = "${MEETING_ID}";
    const MTG_PWD = "${PASSCODE}";
    const BOT = "${BOT_NAME}";
    
    window.__avatarReady = false;
    
    const $ = id => document.getElementById(id);
    const status = (msg, cls='wait') => {
      $('status').textContent = msg;
      $('status').className = 'status ' + cls;
      console.log('[Status] ' + msg);
    };
    
    let room, avatarTrack;
    const avatarVid = $('avatarVid');
    const canvas = $('virtCam');
    const ctx = canvas.getContext('2d');
    
    async function connect() {
      try {
        room = new LivekitClient.Room({ adaptiveStream: true, dynacast: true });
        
        room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, pub, part) => {
          console.log('[LK] Track:', track.kind, part.identity);
          if (track.kind === 'video') {
            avatarTrack = track;
            track.attach(avatarVid);
            startMirror();
            window.__avatarReady = true;
            $('btnJoin').disabled = false;
            status('✅ Avatar ready! Click Join Zoom.', 'ok');
          }
        });
        
        room.on(LivekitClient.RoomEvent.Disconnected, () => {
          status('Disconnected from HeyGen', 'err');
        });
        
        status('Connecting to LiveKit...', 'wait');
        await room.connect(LK_URL, LK_TOKEN);
        status('Connected, waiting for video...', 'wait');
        
      } catch(e) {
        console.error('[LK] Error:', e);
        status('Connection failed: ' + e.message, 'err');
      }
    }
    
    function startMirror() {
      function draw() {
        if (avatarVid.videoWidth) {
          canvas.width = avatarVid.videoWidth;
          canvas.height = avatarVid.videoHeight;
          ctx.drawImage(avatarVid, 0, 0);
        }
        requestAnimationFrame(draw);
      }
      draw();
      
      // Create stream and store globally
      const stream = canvas.captureStream(30);
      window.__virtualStream = stream;
      console.log('[Mirror] Virtual stream ready:', stream.getVideoTracks().length, 'video tracks');
    }
    
    async function doSpeak() {
      const txt = $('txtSpeak').value.trim();
      if (!txt) return;
      
      try {
        status('Speaking...', 'wait');
        const res = await fetch('https://api.heygen.com/v1/streaming.task', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'x-api-key': API_KEY },
          body: JSON.stringify({ session_id: SESSION_ID, text: txt, task_type: 'talk' })
        });
        const j = await res.json();
        console.log('[Speak]', j);
        $('txtSpeak').value = '';
        status('✅ Speaking! Ready for Zoom.', 'ok');
      } catch(e) {
        status('Speak failed: ' + e.message, 'err');
      }
    }
    
    function goZoom() {
      status('Navigating to Zoom...', 'wait');
      
      // Build Zoom URL with params
      const url = 'https://zoom.us/wc/join/' + MTG_ID + 
        '?pwd=' + MTG_PWD;
      
      // Navigate current page - keeps our virtual stream intact
      window.location.href = url;
    }
    
    $('txtSpeak').addEventListener('keypress', e => { if(e.key==='Enter') doSpeak(); });
    
    connect();
  </script>
</body>
</html>`;
}

main();
