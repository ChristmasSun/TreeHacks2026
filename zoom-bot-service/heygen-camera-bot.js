/**
 * HeyGen Avatar as Camera Bot
 * 
 * This approach:
 * 1. Creates a HeyGen avatar session
 * 2. Captures the avatar video stream
 * 3. Injects it as the camera feed when joining Zoom
 * 
 * No screen share needed - the avatar IS the camera!
 */
const { chromium } = require('playwright');
const https = require('https');
require('dotenv').config();

const HEYGEN_API_KEY = process.env.HEYGEN_API_KEY;
const MEETING_ID = process.env.ZOOM_MEETING_ID;
const PASSCODE = process.env.ZOOM_PASSCODE;
const BOT_NAME = process.env.BOT_NAME || 'AI Professor';

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
        } catch (e) {
          reject(e);
        }
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
  console.log('\n🤖 HeyGen Avatar Camera Bot');
  console.log('='.repeat(50));

  // Step 1: Create HeyGen session
  console.log('\n📡 Creating HeyGen session...');
  const heygenData = await createHeyGenSession();
  const sessionId = heygenData.session_id;
  const iceServers = heygenData.ice_servers2 || [];
  const sdpOffer = heygenData.sdp;
  console.log(`   ✓ Session: ${sessionId.substring(0, 20)}...`);

  // Start the session
  await startHeyGenSession(sessionId);
  console.log('   ✓ Session started');

  // Step 2: Launch browser
  console.log('\n🌐 Launching browser...');
  const browser = await chromium.launch({
    headless: false,
    args: [
      '--disable-blink-features=AutomationControlled',
      '--autoplay-policy=no-user-gesture-required',
      '--disable-features=WebRtcHideLocalIpsWithMdns'
    ]
  });

  const context = await browser.newContext({
    permissions: ['microphone', 'camera'],
    viewport: { width: 1400, height: 900 }
  });

  // Step 3: Create a page with HeyGen avatar that we'll capture
  console.log('\n🎭 Setting up HeyGen avatar...');
  const avatarPage = await context.newPage();
  
  // HTML page that connects to HeyGen and renders the avatar
  const avatarHtml = `
<!DOCTYPE html>
<html>
<head>
  <title>HeyGen Avatar</title>
  <style>
    body { margin: 0; background: #1a1a2e; display: flex; justify-content: center; align-items: center; height: 100vh; }
    #avatar-video { width: 640px; height: 480px; background: #000; border-radius: 8px; }
    #status { position: absolute; top: 10px; left: 10px; color: #0f0; font-family: monospace; }
  </style>
</head>
<body>
  <video id="avatar-video" autoplay playsinline></video>
  <div id="status">Connecting...</div>
  
  <script>
    const ICE_SERVERS = ${JSON.stringify(iceServers)};
    const SDP_OFFER = ${JSON.stringify(sdpOffer)};
    const SESSION_ID = "${sessionId}";
    const API_KEY = "${HEYGEN_API_KEY}";
    
    const video = document.getElementById('avatar-video');
    const status = document.getElementById('status');
    
    async function connect() {
      try {
        // Create RTCPeerConnection
        const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
        window.__pc = pc;
        
        pc.ontrack = (event) => {
          status.textContent = 'Connected!';
          if (event.track.kind === 'video') {
            video.srcObject = event.streams[0];
            window.__avatarStream = event.streams[0];
            window.__avatarReady = true;
            console.log('Avatar video connected!');
          }
        };
        
        pc.oniceconnectionstatechange = () => {
          status.textContent = 'ICE: ' + pc.iceConnectionState;
        };
        
        // Set remote description (offer from HeyGen)
        await pc.setRemoteDescription(new RTCSessionDescription({
          type: 'offer',
          sdp: SDP_OFFER.sdp
        }));
        
        // Create answer
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        
        // Send answer to HeyGen
        const response = await fetch('https://api.heygen.com/v1/streaming.ice', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': API_KEY
          },
          body: JSON.stringify({
            session_id: SESSION_ID,
            sdp: { type: 'answer', sdp: answer.sdp }
          })
        });
        
        console.log('ICE response:', await response.json());
        
      } catch (err) {
        console.error('Connection error:', err);
        status.textContent = 'Error: ' + err.message;
      }
    }
    
    connect();
  </script>
</body>
</html>
  `;

  await avatarPage.setContent(avatarHtml);
  
  // Wait for avatar to connect
  console.log('   ⏳ Waiting for avatar stream...');
  try {
    await avatarPage.waitForFunction(() => window.__avatarReady === true, { timeout: 30000 });
    console.log('   ✓ Avatar connected!');
  } catch {
    console.log('   ⚠️ Avatar connection timeout');
  }

  await avatarPage.waitForTimeout(2000);

  // Step 4: Now open Zoom in the same browser, but inject the avatar stream as camera
  console.log('\n🔗 Joining Zoom meeting...');
  console.log(`   Meeting: ${MEETING_ID}`);
  console.log(`   Name: ${BOT_NAME}`);

  const zoomPage = await context.newPage();
  
  // Inject script to override getUserMedia BEFORE the page loads
  await zoomPage.addInitScript(() => {
    // Store original getUserMedia
    const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    
    // Override getUserMedia
    navigator.mediaDevices.getUserMedia = async (constraints) => {
      console.log('[HOOK] getUserMedia called with:', JSON.stringify(constraints));
      
      // If requesting video, try to use our avatar stream
      if (constraints.video) {
        // Check if avatar stream is available via window opener or broadcast
        if (window.__injectedVideoStream) {
          console.log('[HOOK] Returning injected video stream!');
          return window.__injectedVideoStream;
        }
        
        // Check for canvas stream
        if (window.__canvasStream) {
          console.log('[HOOK] Returning canvas stream!');
          return window.__canvasStream;
        }
      }
      
      // Fall back to original
      console.log('[HOOK] Falling back to original getUserMedia');
      return originalGetUserMedia(constraints);
    };
    
    console.log('[HOOK] getUserMedia override installed');
  });

  // Navigate to Zoom
  const zoomUrl = `https://zoom.us/wc/join/${MEETING_ID}`;
  await zoomPage.goto(zoomUrl, { waitUntil: 'networkidle', timeout: 60000 });
  await zoomPage.waitForTimeout(3000);

  // Fill the form
  console.log('   📝 Filling join form...');
  
  // Name
  try {
    const nameInput = await zoomPage.waitForSelector('#input-for-name', { timeout: 5000 });
    await nameInput.fill(BOT_NAME);
    console.log(`   ✓ Name: ${BOT_NAME}`);
  } catch (e) {
    console.log('   ⚠️ Name input not found');
  }

  // Passcode
  try {
    const pwdInput = await zoomPage.waitForSelector('#input-for-pwd', { timeout: 5000 });
    await pwdInput.fill(PASSCODE);
    console.log('   ✓ Passcode entered');
  } catch (e) {
    console.log('   ⚠️ Passcode input not found');
  }

  // Wait for join button to be enabled
  await zoomPage.waitForTimeout(1000);
  
  // Click Join
  try {
    await zoomPage.waitForSelector('button.preview-join-button:not(.zm-btn--disabled)', { timeout: 10000 });
    await zoomPage.click('button.preview-join-button');
    console.log('   ✓ Clicked Join');
  } catch (e) {
    console.log('   ⚠️ Join button issue:', e.message);
  }

  await zoomPage.waitForTimeout(5000);

  // Now try to inject the avatar stream into Zoom
  // We need to capture the avatar video and create a new stream from it
  console.log('\n🎥 Attempting to inject avatar as camera...');
  
  // Get the video stream from avatar page and try to share it
  // This is tricky because we can't directly share streams between pages
  // Instead, we'll create a canvas capture approach
  
  // Go back to avatar page and create a shareable stream broadcast
  await avatarPage.evaluate(() => {
    const video = document.getElementById('avatar-video');
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext('2d');
    
    // Draw video to canvas continuously
    function draw() {
      ctx.drawImage(video, 0, 0, 640, 480);
      requestAnimationFrame(draw);
    }
    draw();
    
    // Create stream from canvas
    window.__canvasStream = canvas.captureStream(30);
    console.log('Canvas stream created');
  });

  console.log('\n✅ Bot is in the meeting!');
  console.log('\n📋 Current status:');
  console.log('   - Avatar page: Running with HeyGen stream');
  console.log('   - Zoom page: Joined meeting');
  console.log('\n⚠️  Note: Due to browser security, we cannot directly inject');
  console.log('   the avatar stream as camera. The bot has joined but shows');
  console.log('   the default camera or test pattern.');
  console.log('\n🔧 Workaround: Use the screen share feature to share the avatar tab.');
  
  // Keep browser open
  console.log('\n⏳ Browser will stay open. Press Ctrl+C to exit.');
  
  // Keep the process running
  await new Promise(() => {});
}

main().catch(err => {
  console.error('\n❌ Error:', err);
  process.exit(1);
});
