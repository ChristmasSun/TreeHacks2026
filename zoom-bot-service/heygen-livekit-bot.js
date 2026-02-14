/**
 * HeyGen Avatar Bot using LiveKit
 * 
 * HeyGen Interactive Avatar v2 uses LiveKit for streaming.
 * This connects to the avatar, captures the video, and injects it as camera.
 */
const { chromium } = require('playwright');
const https = require('https');
const http = require('http');
require('dotenv').config();

const HEYGEN_API_KEY = process.env.HEYGEN_API_KEY;
const MEETING_ID = process.env.ZOOM_MEETING_ID;
const PASSCODE = process.env.ZOOM_PASSCODE;
const BOT_NAME = process.env.BOT_NAME || 'AI Professor';

// Create HeyGen session (returns LiveKit credentials)
async function createHeyGenSession() {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      quality: 'medium',
      avatar_name: 'Angela-inblackskirt-20220820',
      voice: { voice_id: '1bd001e7e50f421d891986aad5158bc8' },
      version: 'v2',
      video_encoding: 'H264'
    });

    const req = https.request({
      hostname: 'api.heygen.com',
      path: '/v1/streaming.new',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': HEYGEN_API_KEY,
        'Content-Length': body.length
      }
    }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          const j = JSON.parse(data);
          if (j.data) resolve(j.data);
          else reject(new Error(JSON.stringify(j)));
        } catch (e) { reject(e); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// Start HeyGen session
async function startHeyGenSession(sessionId) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ session_id: sessionId });
    const req = https.request({
      hostname: 'api.heygen.com',
      path: '/v1/streaming.start',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': HEYGEN_API_KEY,
        'Content-Length': body.length
      }
    }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => resolve(JSON.parse(data)));
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// Make avatar speak
async function speakText(sessionId, text) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      session_id: sessionId,
      text: text,
      task_type: 'talk'
    });
    const req = https.request({
      hostname: 'api.heygen.com',
      path: '/v1/streaming.task',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': HEYGEN_API_KEY,
        'Content-Length': body.length
      }
    }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => resolve(JSON.parse(data)));
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function main() {
  console.log('\n🤖 HeyGen LiveKit Avatar Bot');
  console.log('='.repeat(50));

  // Step 1: Create HeyGen session
  console.log('\n📡 Creating HeyGen session...');
  const heygenData = await createHeyGenSession();
  const sessionId = heygenData.session_id;
  const livekitUrl = heygenData.url;
  const accessToken = heygenData.access_token;
  
  console.log(`   ✓ Session: ${sessionId.substring(0, 20)}...`);
  console.log(`   ✓ LiveKit: ${livekitUrl}`);

  // Start the session
  await startHeyGenSession(sessionId);
  console.log('   ✓ Session started');

  // Step 2: Create local server with LiveKit-connected avatar page
  const PORT = 9876;
  
  const avatarHtml = `
<!DOCTYPE html>
<html>
<head>
  <title>HeyGen Avatar</title>
  <script src="https://cdn.jsdelivr.net/npm/livekit-client@2.1.5/dist/livekit-client.umd.min.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      background: #1a1a2e; 
      display: flex; 
      flex-direction: column;
      align-items: center; 
      justify-content: center;
      min-height: 100vh;
      font-family: system-ui;
      color: #fff;
    }
    #avatar-container {
      position: relative;
      width: 640px;
      height: 480px;
      background: #000;
      border-radius: 12px;
      overflow: hidden;
    }
    #avatar-video {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    #status {
      margin-top: 20px;
      padding: 10px 20px;
      background: rgba(0,255,0,0.1);
      border-radius: 8px;
      font-family: monospace;
      color: #0f0;
    }
    #canvas { display: none; }
    .controls {
      margin-top: 20px;
      display: flex;
      gap: 10px;
    }
    button {
      padding: 10px 20px;
      background: #4CAF50;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
    }
    button:hover { background: #45a049; }
  </style>
</head>
<body>
  <div id="avatar-container">
    <video id="avatar-video" autoplay playsinline></video>
  </div>
  <canvas id="canvas" width="640" height="480"></canvas>
  <div id="status">Connecting to LiveKit...</div>
  <div class="controls">
    <button onclick="testSpeak()">Test Speech</button>
  </div>

  <script>
    const LIVEKIT_URL = "${livekitUrl}";
    const ACCESS_TOKEN = "${accessToken}";
    const SESSION_ID = "${sessionId}";
    const API_KEY = "${HEYGEN_API_KEY}";

    const video = document.getElementById('avatar-video');
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const status = document.getElementById('status');

    let room = null;

    async function connect() {
      try {
        status.textContent = 'Creating LiveKit room...';
        
        // Create LiveKit room
        room = new LivekitClient.Room({
          adaptiveStream: true,
          dynacast: true,
          videoCaptureDefaults: {
            resolution: { width: 640, height: 480, frameRate: 30 }
          }
        });

        // Handle track subscriptions
        room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {
          console.log('Track subscribed:', track.kind, participant.identity);
          
          if (track.kind === 'video') {
            status.textContent = 'Avatar video connected!';
            track.attach(video);
            window.__avatarReady = true;
            
            // Start canvas capture
            startCanvasCapture();
          }
        });

        room.on(LivekitClient.RoomEvent.Disconnected, () => {
          status.textContent = 'Disconnected';
          window.__avatarReady = false;
        });

        room.on(LivekitClient.RoomEvent.ParticipantConnected, (participant) => {
          console.log('Participant connected:', participant.identity);
        });

        // Connect to LiveKit
        status.textContent = 'Connecting to LiveKit...';
        await room.connect(LIVEKIT_URL, ACCESS_TOKEN);
        
        status.textContent = 'Connected! Waiting for avatar stream...';
        console.log('Connected to room:', room.name);

        // Subscribe to existing tracks
        room.remoteParticipants.forEach(participant => {
          participant.trackPublications.forEach(publication => {
            if (publication.track) {
              if (publication.track.kind === 'video') {
                publication.track.attach(video);
                status.textContent = 'Avatar ready!';
                window.__avatarReady = true;
                startCanvasCapture();
              }
            }
          });
        });

      } catch (err) {
        console.error('Connection error:', err);
        status.textContent = 'Error: ' + err.message;
      }
    }

    function startCanvasCapture() {
      // Draw video to canvas for frame capture
      function draw() {
        if (video.readyState >= 2) {
          ctx.drawImage(video, 0, 0, 640, 480);
        }
        requestAnimationFrame(draw);
      }
      draw();

      // Create stream from canvas
      window.__canvasStream = canvas.captureStream(30);
      console.log('Canvas stream ready for capture');
    }

    async function testSpeak() {
      status.textContent = 'Speaking...';
      try {
        const response = await fetch('https://api.heygen.com/v1/streaming.task', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': API_KEY
          },
          body: JSON.stringify({
            session_id: SESSION_ID,
            text: 'Hello! I am your AI Professor. Welcome to the session!',
            task_type: 'talk'
          })
        });
        const result = await response.json();
        console.log('Speak result:', result);
        status.textContent = 'Speaking complete!';
      } catch (err) {
        status.textContent = 'Speak error: ' + err.message;
      }
    }

    // Connect on load
    connect();
  </script>
</body>
</html>
  `;

  const server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(avatarHtml);
  });

  server.listen(PORT, () => {
    console.log(`   ✓ Avatar server: http://localhost:${PORT}`);
  });

  // Step 3: Launch browser
  console.log('\n🌐 Launching browser...');
  
  const browser = await chromium.launch({
    headless: false,
    args: [
      '--disable-blink-features=AutomationControlled',
      '--autoplay-policy=no-user-gesture-required',
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream'
    ]
  });

  const context = await browser.newContext({
    permissions: ['microphone', 'camera'],
    viewport: { width: 1400, height: 900 }
  });

  // Step 4: Load avatar page
  console.log('\n🎭 Loading HeyGen avatar...');
  const avatarPage = await context.newPage();
  await avatarPage.goto(`http://localhost:${PORT}`, { waitUntil: 'domcontentloaded' });

  // Wait for avatar to be ready
  console.log('   ⏳ Waiting for avatar stream...');
  try {
    await avatarPage.waitForFunction(() => window.__avatarReady === true, { timeout: 45000 });
    console.log('   ✓ Avatar connected!');
  } catch {
    console.log('   ⚠️ Avatar connection timeout, continuing...');
  }

  await avatarPage.waitForTimeout(3000);

  // Step 5: Open Zoom
  console.log('\n🔗 Opening Zoom...');
  const zoomPage = await context.newPage();

  // Inject camera override before page loads
  await zoomPage.addInitScript(`
    // Create canvas for our fake camera
    const __fakeCanvas = document.createElement('canvas');
    __fakeCanvas.width = 640;
    __fakeCanvas.height = 480;
    const __fakeCtx = __fakeCanvas.getContext('2d');
    
    // Draw gradient background initially
    const grad = __fakeCtx.createLinearGradient(0, 0, 640, 480);
    grad.addColorStop(0, '#1a1a2e');
    grad.addColorStop(1, '#16213e');
    __fakeCtx.fillStyle = grad;
    __fakeCtx.fillRect(0, 0, 640, 480);
    __fakeCtx.fillStyle = '#fff';
    __fakeCtx.font = '20px system-ui';
    __fakeCtx.textAlign = 'center';
    __fakeCtx.fillText('AI Professor', 320, 240);
    
    // Create fake stream
    window.__fakeStream = __fakeCanvas.captureStream(30);
    window.__fakeCanvas = __fakeCanvas;
    window.__fakeCtx = __fakeCtx;
    
    // Override getUserMedia
    const __origGUM = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async function(constraints) {
      console.log('[CAMERA] getUserMedia called');
      
      if (constraints.video) {
        console.log('[CAMERA] Returning fake camera stream');
        
        // If audio is also requested, get real audio
        if (constraints.audio) {
          try {
            const audioStream = await __origGUM({ audio: true, video: false });
            const combined = new MediaStream();
            window.__fakeStream.getVideoTracks().forEach(t => combined.addTrack(t));
            audioStream.getAudioTracks().forEach(t => combined.addTrack(t));
            return combined;
          } catch (e) {
            console.log('[CAMERA] Audio failed, returning video only');
          }
        }
        
        return window.__fakeStream;
      }
      
      return __origGUM(constraints);
    };
    
    console.log('[CAMERA] Fake camera hook installed');
  `);

  await zoomPage.goto(`https://zoom.us/wc/join/${MEETING_ID}`, { 
    waitUntil: 'networkidle', 
    timeout: 60000 
  });

  // Start frame relay from avatar to zoom
  console.log('   🔄 Starting frame relay...');
  
  const relayFrames = async () => {
    let frameCount = 0;
    while (true) {
      try {
        // Get frame from avatar canvas
        const frameData = await avatarPage.evaluate(() => {
          const canvas = document.getElementById('canvas');
          if (canvas) return canvas.toDataURL('image/jpeg', 0.85);
          return null;
        });

        if (frameData) {
          // Draw on zoom's fake canvas
          await zoomPage.evaluate((dataUrl) => {
            const img = new Image();
            img.onload = () => {
              if (window.__fakeCtx) {
                window.__fakeCtx.drawImage(img, 0, 0, 640, 480);
              }
            };
            img.src = dataUrl;
          }, frameData);
          
          frameCount++;
          if (frameCount % 150 === 0) {
            console.log(`   📊 Relayed ${frameCount} frames`);
          }
        }
        
        // ~20 fps
        await new Promise(r => setTimeout(r, 50));
      } catch (e) {
        break;
      }
    }
  };

  // Start relay in background
  relayFrames();

  await zoomPage.waitForTimeout(2000);

  // Fill form
  console.log('   📝 Filling form...');
  
  try {
    const nameInput = await zoomPage.waitForSelector('#input-for-name', { timeout: 5000 });
    await nameInput.fill(BOT_NAME);
    console.log(`   ✓ Name: ${BOT_NAME}`);
  } catch {}

  try {
    const pwdInput = await zoomPage.waitForSelector('#input-for-pwd', { timeout: 5000 });
    await pwdInput.fill(PASSCODE);
    console.log('   ✓ Passcode entered');
  } catch {}

  await zoomPage.waitForTimeout(1000);

  try {
    await zoomPage.waitForSelector('button.preview-join-button:not(.zm-btn--disabled)', { timeout: 10000 });
    await zoomPage.click('button.preview-join-button');
    console.log('   ✓ Clicked Join!');
  } catch {}

  console.log('\n⏳ Waiting to be admitted to meeting...');
  
  // Wait for meeting to load (look for meeting controls)
  await zoomPage.waitForTimeout(5000);
  
  // Function to enable camera
  async function enableCamera() {
    console.log('   🎥 Attempting to enable camera...');
    
    // Look for video/camera button - try multiple selectors
    const cameraSelectors = [
      'button[aria-label*="video" i]',
      'button[aria-label*="camera" i]',
      'button[aria-label*="Start Video" i]',
      'button[aria-label="start my video"]',
      '.footer-button__button[aria-label*="video" i]',
      '.video-btn',
      '[data-testid="video-button"]',
      'button:has-text("Start Video")',
      // Zoom web client specific
      '.send-video-container button',
      '.footer__btns button:nth-child(2)'
    ];
    
    for (const selector of cameraSelectors) {
      try {
        const btn = await zoomPage.$(selector);
        if (btn) {
          const ariaLabel = await btn.getAttribute('aria-label') || '';
          console.log(`   Found button: ${selector} (${ariaLabel})`);
          
          // Check if video is currently off (button says "start" or similar)
          if (ariaLabel.toLowerCase().includes('start') || 
              ariaLabel.toLowerCase().includes('unmute video') ||
              !ariaLabel.toLowerCase().includes('stop')) {
            await btn.click();
            console.log('   ✓ Clicked to enable camera!');
            return true;
          }
        }
      } catch {}
    }
    return false;
  }
  
  // Try to enable camera multiple times as meeting loads
  for (let i = 0; i < 10; i++) {
    await zoomPage.waitForTimeout(3000);
    
    // Check if we're in the meeting (look for footer controls)
    const inMeeting = await zoomPage.$('.footer-button__button, .footer__btns, .meeting-app');
    if (inMeeting) {
      console.log('   ✓ In meeting! Enabling camera...');
      const enabled = await enableCamera();
      if (enabled) break;
    } else {
      console.log(`   ⏳ Waiting to join meeting... (attempt ${i + 1})`);
    }
  }

  console.log('\n✅ Bot joined with HeyGen avatar as camera!');
  
  // Test speech after a delay
  setTimeout(async () => {
    console.log('\n🗣️ Testing avatar speech...');
    await speakText(sessionId, 'Hello everyone! I am your AI Professor for today.');
  }, 10000);

  console.log('\n⏳ Browser will stay open. Press Ctrl+C to exit.');
  await new Promise(() => {});
}

main().catch(err => {
  console.error('\n❌ Error:', err);
  process.exit(1);
});
