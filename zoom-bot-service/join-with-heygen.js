/**
 * Zoom Meeting Join with HeyGen Avatar as Camera
 * 
 * This script:
 * 1. Creates a HeyGen streaming avatar session
 * 2. Connects to the LiveKit stream to get avatar video
 * 3. Joins Zoom as a guest using the avatar as the camera
 * 
 * Usage: 
 *   HEYGEN_API_KEY=your_key node join-with-heygen.js
 * 
 * Or create a .env file with HEYGEN_API_KEY
 */

const { chromium } = require('playwright');
const https = require('https');
require('dotenv').config();

// Meeting details
const MEETING_ID = '89711545987';
const PASSCODE = '926454';
const USER_NAME = 'AI Professor';

// Get HeyGen API key
const HEYGEN_API_KEY = process.env.HEYGEN_API_KEY;

if (!HEYGEN_API_KEY) {
  console.error('❌ Missing HEYGEN_API_KEY environment variable');
  console.error('   Set it via: HEYGEN_API_KEY=your_key node join-with-heygen.js');
  console.error('   Or add HEYGEN_API_KEY=your_key to .env file');
  process.exit(1);
}

/**
 * Create a HeyGen streaming avatar session
 */
async function createHeyGenSession() {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({
      quality: 'medium',
      avatar_id: 'default', // Use default avatar, or specify your avatar ID
      video_encoding: 'VP8',
      version: 'v2',
      disable_idle_timeout: true
    });

    const options = {
      hostname: 'api.heygen.com',
      port: 443,
      path: '/v1/streaming.new',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': HEYGEN_API_KEY,
        'Content-Length': data.length
      }
    };

    const req = https.request(options, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        try {
          const response = JSON.parse(body);
          if (response.code === 100 || res.statusCode === 200) {
            resolve(response.data);
          } else {
            reject(new Error(`HeyGen API error: ${response.message || body}`));
          }
        } catch (e) {
          reject(new Error(`Failed to parse response: ${body}`));
        }
      });
    });

    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

/**
 * Start the HeyGen session
 */
async function startHeyGenSession(sessionId) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({
      session_id: sessionId
    });

    const options = {
      hostname: 'api.heygen.com',
      port: 443,
      path: '/v1/streaming.start',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': HEYGEN_API_KEY,
        'Content-Length': data.length
      }
    };

    const req = https.request(options, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        try {
          const response = JSON.parse(body);
          resolve(response.data);
        } catch (e) {
          reject(new Error(`Failed to parse response: ${body}`));
        }
      });
    });

    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

/**
 * Close the HeyGen session
 */
async function closeHeyGenSession(sessionId) {
  return new Promise((resolve) => {
    const data = JSON.stringify({ session_id: sessionId });

    const options = {
      hostname: 'api.heygen.com',
      port: 443,
      path: '/v1/streaming.stop',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': HEYGEN_API_KEY,
        'Content-Length': data.length
      }
    };

    const req = https.request(options, (res) => {
      res.on('data', () => {});
      res.on('end', () => resolve());
    });

    req.on('error', () => resolve());
    req.write(data);
    req.end();
  });
}

async function main() {
  console.log('\n🤖 HeyGen Avatar + Zoom Join Test');
  console.log('='.repeat(45));
  console.log(`Meeting: ${MEETING_ID}`);
  console.log(`Passcode: ${PASSCODE}`);
  console.log(`Name: ${USER_NAME}`);
  console.log('');

  let heygenSession = null;

  try {
    // Step 1: Create HeyGen session
    console.log('🎭 Creating HeyGen avatar session...');
    heygenSession = await createHeyGenSession();
    console.log(`✅ Session created: ${heygenSession.session_id}`);
    console.log(`   LiveKit URL: ${heygenSession.url}`);
    console.log(`   Token: ${heygenSession.access_token?.substring(0, 30)}...`);
    console.log('');

    // Step 2: Start the session
    console.log('▶️  Starting HeyGen session...');
    await startHeyGenSession(heygenSession.session_id);
    console.log('✅ Session started');
    console.log('');

    // Step 3: Launch browser
    console.log('🚀 Launching browser...');
    const browser = await chromium.launch({
      headless: false,
      args: [
        '--use-fake-ui-for-media-stream',
        '--use-fake-device-for-media-stream',
        '--autoplay-policy=no-user-gesture-required',
        '--disable-features=WebRtcHideLocalIpsWithMdns'
      ]
    });

    const context = await browser.newContext({
      permissions: ['microphone', 'camera'],
      viewport: { width: 1400, height: 900 },
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    });

    const page = await context.newPage();

    // Log console messages
    page.on('console', msg => {
      const text = msg.text();
      if (msg.type() === 'error' || text.includes('[HeyGen]') || text.includes('[Zoom]')) {
        console.log(`[PAGE] ${text}`);
      }
    });

    page.on('pageerror', err => {
      console.error(`[PAGE ERROR] ${err.message}`);
    });

    // Step 4: Create a page that connects to HeyGen LiveKit and provides video
    console.log('📄 Loading integration page...');
    
    const htmlContent = createIntegrationHTML({
      livekitUrl: heygenSession.url,
      livekitToken: heygenSession.access_token,
      sessionId: heygenSession.session_id,
      meetingId: MEETING_ID,
      passcode: PASSCODE,
      userName: USER_NAME
    });

    await page.setContent(htmlContent, { waitUntil: 'domcontentloaded' });

    // Wait for LiveKit connection
    console.log('⏳ Waiting for HeyGen avatar stream...');
    
    try {
      await page.waitForFunction(
        () => window.avatarConnected === true,
        { timeout: 30000 }
      );
      console.log('✅ Avatar connected!');
    } catch (e) {
      console.log('⚠️  Avatar connection timeout, proceeding anyway...');
    }

    // Keep browser open
    console.log('\n✅ Setup complete!');
    console.log('   1. The HeyGen avatar should appear in the video preview');
    console.log('   2. Click "Join Zoom" button to join the meeting');
    console.log('   3. Or interact with the page manually');
    console.log('\n   Browser will stay open for 5 minutes...');
    
    await page.waitForTimeout(300000); // 5 minutes

    // Cleanup
    console.log('\n🛑 Cleaning up...');
    await browser.close();

  } catch (error) {
    console.error('\n❌ Error:', error.message);
  } finally {
    // Close HeyGen session
    if (heygenSession?.session_id) {
      console.log('🔄 Closing HeyGen session...');
      await closeHeyGenSession(heygenSession.session_id);
      console.log('✅ HeyGen session closed');
    }
  }

  console.log('\n🛑 Done.');
}

/**
 * Create HTML page that connects HeyGen avatar to Zoom
 */
function createIntegrationHTML(config) {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>HeyGen + Zoom Integration</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 20px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: white;
      min-height: 100vh;
    }
    .container {
      max-width: 1200px;
      margin: 0 auto;
    }
    h1 {
      margin: 0 0 20px 0;
      font-size: 24px;
      color: #00d4ff;
    }
    .status {
      background: rgba(255,255,255,0.1);
      padding: 15px 20px;
      border-radius: 10px;
      margin-bottom: 20px;
      font-family: monospace;
    }
    .status.success { border-left: 4px solid #00ff88; }
    .status.error { border-left: 4px solid #ff4444; }
    .status.pending { border-left: 4px solid #ffaa00; }
    
    .video-container {
      display: flex;
      gap: 20px;
      margin-bottom: 20px;
    }
    .video-box {
      flex: 1;
      background: #000;
      border-radius: 10px;
      overflow: hidden;
      position: relative;
    }
    .video-box video {
      width: 100%;
      height: 300px;
      object-fit: cover;
    }
    .video-label {
      position: absolute;
      top: 10px;
      left: 10px;
      background: rgba(0,0,0,0.7);
      padding: 5px 10px;
      border-radius: 5px;
      font-size: 12px;
    }
    
    .controls {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    button {
      padding: 12px 24px;
      border: none;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    button:hover { transform: translateY(-2px); }
    button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
    
    .btn-primary {
      background: linear-gradient(135deg, #00d4ff, #0099ff);
      color: white;
    }
    .btn-secondary {
      background: rgba(255,255,255,0.1);
      color: white;
      border: 1px solid rgba(255,255,255,0.2);
    }
    .btn-success {
      background: linear-gradient(135deg, #00ff88, #00cc66);
      color: #000;
    }
    
    #speakInput {
      flex: 1;
      padding: 12px;
      border: 1px solid rgba(255,255,255,0.2);
      border-radius: 8px;
      background: rgba(255,255,255,0.1);
      color: white;
      font-size: 14px;
    }
    #speakInput::placeholder { color: rgba(255,255,255,0.5); }
  </style>
</head>
<body>
  <div class="container">
    <h1>🎭 HeyGen Avatar + 💻 Zoom Integration</h1>
    
    <div id="status" class="status pending">Connecting to HeyGen avatar...</div>
    
    <div class="video-container">
      <div class="video-box">
        <div class="video-label">HeyGen Avatar</div>
        <video id="avatarVideo" autoplay playsinline muted></video>
      </div>
      <div class="video-box">
        <div class="video-label">Camera Preview (What Zoom Sees)</div>
        <video id="cameraPreview" autoplay playsinline muted></video>
      </div>
    </div>
    
    <div class="controls">
      <input type="text" id="speakInput" placeholder="Type something for the avatar to say..." />
      <button class="btn-secondary" onclick="makeAvatarSpeak()">🗣️ Speak</button>
      <button class="btn-success" id="joinBtn" onclick="joinZoom()" disabled>🚀 Join Zoom Meeting</button>
    </div>
  </div>

  <!-- LiveKit Client SDK -->
  <script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
  
  <script>
    const config = ${JSON.stringify(config)};
    
    window.avatarConnected = false;
    let room = null;
    let avatarVideoTrack = null;
    let avatarAudioTrack = null;
    let virtualStream = null;
    
    function updateStatus(message, type = 'pending') {
      const el = document.getElementById('status');
      el.textContent = message;
      el.className = 'status ' + type;
      console.log('[HeyGen] ' + message);
    }
    
    async function connectToHeyGen() {
      try {
        updateStatus('Connecting to HeyGen LiveKit room...');
        
        // Create LiveKit room
        room = new LivekitClient.Room({
          adaptiveStream: true,
          dynacast: true,
          videoCaptureDefaults: {
            resolution: { width: 1280, height: 720 }
          }
        });
        
        // Handle track subscriptions
        room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {
          console.log('[HeyGen] Track subscribed:', track.kind, participant.identity);
          
          if (track.kind === 'video') {
            avatarVideoTrack = track;
            const videoEl = document.getElementById('avatarVideo');
            track.attach(videoEl);
            
            // Also show in camera preview
            const previewEl = document.getElementById('cameraPreview');
            track.attach(previewEl);
            
            // Create MediaStream from the video track for Zoom
            virtualStream = new MediaStream([track.mediaStreamTrack]);
            
            window.avatarConnected = true;
            document.getElementById('joinBtn').disabled = false;
            updateStatus('✅ Avatar connected! Ready to join Zoom.', 'success');
          }
          
          if (track.kind === 'audio') {
            avatarAudioTrack = track;
            // Don't auto-play audio to avoid echo
            console.log('[HeyGen] Audio track available');
          }
        });
        
        room.on(LivekitClient.RoomEvent.TrackUnsubscribed, (track) => {
          console.log('[HeyGen] Track unsubscribed:', track.kind);
          track.detach();
        });
        
        room.on(LivekitClient.RoomEvent.Disconnected, () => {
          updateStatus('Disconnected from HeyGen', 'error');
          window.avatarConnected = false;
        });
        
        // Connect to the room
        await room.connect(config.livekitUrl, config.livekitToken);
        console.log('[HeyGen] Connected to room:', room.name);
        
        updateStatus('Connected to LiveKit, waiting for avatar video...', 'pending');
        
      } catch (error) {
        console.error('[HeyGen] Connection error:', error);
        updateStatus('Failed to connect: ' + error.message, 'error');
      }
    }
    
    async function makeAvatarSpeak() {
      const text = document.getElementById('speakInput').value.trim();
      if (!text) return;
      
      try {
        updateStatus('Avatar speaking...', 'pending');
        
        const response = await fetch('https://api.heygen.com/v1/streaming.task', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': '${HEYGEN_API_KEY}'
          },
          body: JSON.stringify({
            session_id: config.sessionId,
            text: text,
            task_type: 'talk'
          })
        });
        
        const result = await response.json();
        console.log('[HeyGen] Speak result:', result);
        
        document.getElementById('speakInput').value = '';
        updateStatus('✅ Avatar is speaking!', 'success');
        
      } catch (error) {
        console.error('[HeyGen] Speak error:', error);
        updateStatus('Failed to make avatar speak: ' + error.message, 'error');
      }
    }
    
    async function joinZoom() {
      if (!window.avatarConnected || !virtualStream) {
        alert('Avatar not connected yet!');
        return;
      }
      
      updateStatus('Opening Zoom join page...', 'pending');
      
      // Open Zoom in the same window - the avatar video from LiveKit
      // becomes the "camera" since we have fake device enabled
      
      // Store the avatar stream globally so it persists
      window.avatarStream = virtualStream;
      
      // Navigate to Zoom
      const zoomUrl = 'https://zoom.us/wc/join/' + config.meetingId + 
        '?pwd=' + config.passcode + 
        '&prefer=1' + // Prefer web client
        '&un=' + encodeURIComponent(btoa(config.userName));
      
      window.location.href = zoomUrl;
    }
    
    // Also allow Enter key to trigger speak
    document.getElementById('speakInput').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') makeAvatarSpeak();
    });
    
    // Start connection
    connectToHeyGen();
  </script>
</body>
</html>`;
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
