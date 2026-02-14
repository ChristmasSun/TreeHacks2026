/**
 * HeyGen Avatar as Fake Camera
 * 
 * Uses Chromium's ability to inject fake media devices combined with
 * aggressive getUserMedia interception to make HeyGen BE the camera.
 */
const { chromium } = require('playwright');
const https = require('https');
const http = require('http');
const fs = require('fs');
require('dotenv').config();

const HEYGEN_API_KEY = process.env.HEYGEN_API_KEY;
const MEETING_ID = process.env.ZOOM_MEETING_ID;
const PASSCODE = process.env.ZOOM_PASSCODE;
const BOT_NAME = process.env.BOT_NAME || 'AI Professor';

// Create HeyGen avatar session
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
          else reject(new Error(data));
        } catch (e) { reject(e); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

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

async function main() {
  console.log('\n🤖 HeyGen Avatar Fake Camera Bot');
  console.log('='.repeat(50));

  // Step 1: Create HeyGen session
  console.log('\n📡 Creating HeyGen session...');
  const heygenData = await createHeyGenSession();
  const sessionId = heygenData.session_id;
  const iceServers = heygenData.ice_servers2 || [];
  const sdpOffer = heygenData.sdp;
  console.log(`   ✓ Session: ${sessionId.substring(0, 20)}...`);

  await startHeyGenSession(sessionId);
  console.log('   ✓ Session started');

  // Step 2: Create a local server that serves the combined HeyGen+Zoom page
  const PORT = 9876;
  
  const combinedHtml = `
<!DOCTYPE html>
<html>
<head>
  <title>HeyGen Camera Bot</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: system-ui; background: #0a0a0a; color: #fff; }
    #container { display: flex; height: 100vh; }
    #avatar-panel { width: 300px; padding: 10px; background: #111; border-right: 1px solid #333; }
    #avatar-video { width: 100%; aspect-ratio: 4/3; background: #000; border-radius: 8px; }
    #zoom-panel { flex: 1; }
    #zoom-frame { width: 100%; height: 100%; border: none; }
    #status { padding: 10px; font-size: 12px; color: #0f0; font-family: monospace; }
    h3 { padding: 10px 0; color: #888; font-size: 14px; }
    #canvas { display: none; }
  </style>
</head>
<body>
  <div id="container">
    <div id="avatar-panel">
      <h3>HeyGen Avatar (Camera Source)</h3>
      <video id="avatar-video" autoplay playsinline muted></video>
      <canvas id="canvas" width="640" height="480"></canvas>
      <div id="status">Initializing...</div>
    </div>
    <div id="zoom-panel">
      <iframe id="zoom-frame" allow="camera; microphone; display-capture"></iframe>
    </div>
  </div>

  <script>
    const ICE_SERVERS = ${JSON.stringify(iceServers)};
    const SDP_OFFER = ${JSON.stringify(sdpOffer)};
    const SESSION_ID = "${sessionId}";
    const API_KEY = "${HEYGEN_API_KEY}";
    const MEETING_ID = "${MEETING_ID}";
    const PASSCODE = "${PASSCODE}";
    const BOT_NAME = "${BOT_NAME}";

    const video = document.getElementById('avatar-video');
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const status = document.getElementById('status');
    const zoomFrame = document.getElementById('zoom-frame');

    let avatarStream = null;
    let canvasStream = null;

    // Connect to HeyGen
    async function connectHeyGen() {
      status.textContent = 'Connecting to HeyGen...';
      
      const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
      
      pc.ontrack = (event) => {
        if (event.track.kind === 'video') {
          video.srcObject = event.streams[0];
          avatarStream = event.streams[0];
          status.textContent = 'Avatar connected! Setting up camera...';
          setupFakeCamera();
        }
      };

      pc.oniceconnectionstatechange = () => {
        console.log('ICE state:', pc.iceConnectionState);
      };

      await pc.setRemoteDescription(new RTCSessionDescription({
        type: 'offer',
        sdp: SDP_OFFER.sdp
      }));

      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);

      await fetch('https://api.heygen.com/v1/streaming.ice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-api-key': API_KEY },
        body: JSON.stringify({ session_id: SESSION_ID, sdp: { type: 'answer', sdp: answer.sdp } })
      });
    }

    // Set up fake camera from avatar stream
    function setupFakeCamera() {
      // Draw avatar to canvas continuously
      function drawFrame() {
        if (video.readyState >= 2) {
          ctx.drawImage(video, 0, 0, 640, 480);
        }
        requestAnimationFrame(drawFrame);
      }
      drawFrame();

      // Create stream from canvas
      canvasStream = canvas.captureStream(30);
      
      // Store globally so Zoom iframe can access it
      window.__heygenStream = canvasStream;
      window.__avatarReady = true;
      
      status.textContent = 'Camera ready! Loading Zoom...';
      
      // Now load Zoom
      loadZoom();
    }

    // Load Zoom in iframe with our fake camera
    function loadZoom() {
      // We can't directly inject into iframe from different origin
      // So instead, open Zoom in a new window/tab where we CAN inject
      status.textContent = 'Opening Zoom (check new tab)...';
      
      // Signal to parent that we're ready
      if (window.opener) {
        window.opener.postMessage({ type: 'avatar_ready', stream: true }, '*');
      }
      
      // Display info
      status.innerHTML = \`
        <strong>Avatar streaming!</strong><br>
        Meeting: \${MEETING_ID}<br>
        Name: \${BOT_NAME}<br><br>
        <em>Zoom will open in main browser...</em>
      \`;
    }

    // Start
    connectHeyGen().catch(err => {
      status.textContent = 'Error: ' + err.message;
      console.error(err);
    });
  </script>
</body>
</html>
  `;

  const server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(combinedHtml);
  });
  
  server.listen(PORT, () => {
    console.log(`   ✓ Local server on http://localhost:${PORT}`);
  });

  // Step 3: Launch browser with special flags
  console.log('\n🌐 Launching browser...');
  
  const browser = await chromium.launch({
    headless: false,
    args: [
      '--disable-blink-features=AutomationControlled',
      '--autoplay-policy=no-user-gesture-required',
      '--disable-features=WebRtcHideLocalIpsWithMdns',
      // These flags enable fake media devices
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      // Allow getUserMedia override
      '--disable-web-security',
      '--allow-running-insecure-content'
    ]
  });

  const context = await browser.newContext({
    permissions: ['microphone', 'camera'],
    viewport: { width: 1400, height: 900 },
    ignoreHTTPSErrors: true
  });

  // Step 4: First load the avatar page and wait for stream
  console.log('\n🎭 Loading HeyGen avatar...');
  const avatarPage = await context.newPage();
  await avatarPage.goto(`http://localhost:${PORT}`, { waitUntil: 'domcontentloaded' });

  // Wait for avatar to be ready
  console.log('   ⏳ Waiting for avatar stream...');
  try {
    await avatarPage.waitForFunction(() => window.__avatarReady === true, { timeout: 30000 });
    console.log('   ✓ Avatar stream ready!');
  } catch {
    console.log('   ⚠️ Avatar timeout, continuing anyway...');
  }

  await avatarPage.waitForTimeout(2000);

  // Get the canvas stream from the avatar page
  const streamReady = await avatarPage.evaluate(() => {
    return window.__heygenStream ? true : false;
  });
  console.log(`   Stream available: ${streamReady}`);

  // Step 5: Open Zoom page with getUserMedia override
  console.log('\n🔗 Opening Zoom with camera override...');
  const zoomPage = await context.newPage();

  // Inject script to grab stream from avatar page and use it
  await zoomPage.addInitScript(`
    // Store reference to get stream later
    window.__getAvatarStream = async function() {
      // Try to get stream from opener or broadcast channel
      return new Promise((resolve) => {
        const bc = new BroadcastChannel('heygen-stream');
        bc.onmessage = (e) => {
          if (e.data.type === 'stream') {
            resolve(e.data.stream);
          }
        };
        bc.postMessage({ type: 'request-stream' });
        
        // Timeout fallback
        setTimeout(() => resolve(null), 1000);
      });
    };

    // Override getUserMedia
    const originalGUM = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    
    navigator.mediaDevices.getUserMedia = async function(constraints) {
      console.log('[CAMERA HOOK] getUserMedia called:', JSON.stringify(constraints));
      
      // Always call original to get a real stream structure
      const realStream = await originalGUM(constraints);
      
      // If we have a canvas stream injected, replace the video track
      if (constraints.video && window.__injectedVideoTrack) {
        console.log('[CAMERA HOOK] Replacing video track with HeyGen!');
        const newStream = new MediaStream();
        
        // Add our HeyGen video track
        newStream.addTrack(window.__injectedVideoTrack);
        
        // Add original audio track if present
        realStream.getAudioTracks().forEach(t => newStream.addTrack(t));
        
        return newStream;
      }
      
      return realStream;
    };
    
    console.log('[CAMERA HOOK] getUserMedia override installed');
  `);

  // Navigate to Zoom
  await zoomPage.goto(`https://zoom.us/wc/join/${MEETING_ID}`, { 
    waitUntil: 'networkidle', 
    timeout: 60000 
  });

  // Now try to inject the video track from avatar page into zoom page
  // We'll capture frames from avatar and create a new stream in zoom context
  console.log('   📹 Injecting HeyGen video track...');

  // Create a frame capture from avatar page and inject into zoom
  // This uses a creative approach: capture to data URL and recreate
  
  await zoomPage.evaluate(async () => {
    // Create a canvas that we'll update with frames
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext('2d');
    
    // Fill with a nice gradient initially
    const gradient = ctx.createLinearGradient(0, 0, 640, 480);
    gradient.addColorStop(0, '#1a1a2e');
    gradient.addColorStop(1, '#16213e');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 640, 480);
    ctx.fillStyle = '#fff';
    ctx.font = '24px system-ui';
    ctx.textAlign = 'center';
    ctx.fillText('HeyGen Avatar Loading...', 320, 240);
    
    // Create stream from canvas
    const stream = canvas.captureStream(30);
    window.__canvasForAvatar = canvas;
    window.__ctxForAvatar = ctx;
    window.__injectedVideoTrack = stream.getVideoTracks()[0];
    
    console.log('[CAMERA] Canvas stream created, track:', window.__injectedVideoTrack.id);
  });

  // Now continuously send frames from avatar page to zoom page
  console.log('   🔄 Starting frame relay...');
  
  // Start frame relay in background
  const relayFrames = async () => {
    let frameCount = 0;
    while (true) {
      try {
        // Capture frame from avatar page as data URL
        const frameData = await avatarPage.evaluate(() => {
          const canvas = document.getElementById('canvas');
          if (canvas) {
            return canvas.toDataURL('image/jpeg', 0.8);
          }
          return null;
        });

        if (frameData) {
          // Send to zoom page and draw on its canvas
          await zoomPage.evaluate((dataUrl) => {
            const img = new Image();
            img.onload = () => {
              if (window.__ctxForAvatar) {
                window.__ctxForAvatar.drawImage(img, 0, 0, 640, 480);
              }
            };
            img.src = dataUrl;
          }, frameData);
          
          frameCount++;
          if (frameCount % 100 === 0) {
            console.log(`   📊 Relayed ${frameCount} frames`);
          }
        }
        
        // ~15 fps
        await new Promise(r => setTimeout(r, 66));
      } catch (e) {
        // Page might have navigated, stop relay
        break;
      }
    }
  };

  // Start relay in background (don't await)
  relayFrames();

  await zoomPage.waitForTimeout(2000);

  // Fill the Zoom form
  console.log('   📝 Filling join form...');
  
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
  } catch (e) {
    console.log('   ⚠️ Join button issue');
  }

  console.log('\n✅ Bot should be joining with HeyGen as camera!');
  console.log('\n⏳ Browser will stay open. Press Ctrl+C to exit.');
  
  // Keep running
  await new Promise(() => {});
}

main().catch(err => {
  console.error('\n❌ Error:', err);
  process.exit(1);
});
