/**
 * HeyGen Avatar Bot - Fixed Camera Injection
 * 
 * This version aggressively maintains the camera hook and handles
 * Zoom's post-join camera request.
 */
const { chromium } = require('playwright');
const https = require('https');
const http = require('http');
require('dotenv').config();

const HEYGEN_API_KEY = process.env.HEYGEN_API_KEY;
const MEETING_ID = process.env.ZOOM_MEETING_ID;
const PASSCODE = process.env.ZOOM_PASSCODE;
const BOT_NAME = process.env.BOT_NAME || 'AI Professor';

// Create HeyGen session
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
  console.log('\n🤖 HeyGen Avatar Bot (Fixed Camera)');
  console.log('='.repeat(50));

  // Step 1: Create HeyGen session
  console.log('\n📡 Creating HeyGen session...');
  const heygenData = await createHeyGenSession();
  const sessionId = heygenData.session_id;
  const livekitUrl = heygenData.url;
  const accessToken = heygenData.access_token;
  
  console.log(`   ✓ Session: ${sessionId.substring(0, 20)}...`);

  await startHeyGenSession(sessionId);
  console.log('   ✓ Session started');

  // Step 2: Create local server with avatar page
  const PORT = 9877; // Different port to avoid conflicts
  
  const avatarHtml = `
<!DOCTYPE html>
<html>
<head>
  <title>HeyGen Avatar</title>
  <script src="https://cdn.jsdelivr.net/npm/livekit-client@2.1.5/dist/livekit-client.umd.min.js"></script>
  <style>
    body { background: #1a1a2e; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; font-family: system-ui; color: #fff; }
    #avatar-video { width: 640px; height: 480px; background: #000; border-radius: 12px; }
    #status { margin-top: 20px; padding: 10px 20px; background: rgba(0,255,0,0.1); border-radius: 8px; font-family: monospace; color: #0f0; }
    #canvas { display: none; }
  </style>
</head>
<body>
  <video id="avatar-video" autoplay playsinline></video>
  <canvas id="canvas" width="640" height="480"></canvas>
  <div id="status">Connecting...</div>

  <script>
    const LIVEKIT_URL = "${livekitUrl}";
    const ACCESS_TOKEN = "${accessToken}";

    const video = document.getElementById('avatar-video');
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const status = document.getElementById('status');

    async function connect() {
      try {
        const room = new LivekitClient.Room({ adaptiveStream: true, dynacast: true });

        room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {
          if (track.kind === 'video') {
            status.textContent = 'Avatar connected!';
            track.attach(video);
            window.__avatarReady = true;
            
            // Start canvas capture
            function draw() {
              if (video.readyState >= 2) {
                ctx.drawImage(video, 0, 0, 640, 480);
              }
              requestAnimationFrame(draw);
            }
            draw();
            window.__canvasStream = canvas.captureStream(30);
          }
        });

        await room.connect(LIVEKIT_URL, ACCESS_TOKEN);
        status.textContent = 'Connected, waiting for avatar...';

        // Check existing tracks
        room.remoteParticipants.forEach(p => {
          p.trackPublications.forEach(pub => {
            if (pub.track && pub.track.kind === 'video') {
              pub.track.attach(video);
              window.__avatarReady = true;
            }
          });
        });
      } catch (err) {
        status.textContent = 'Error: ' + err.message;
      }
    }
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

  // Step 3: Launch browser with aggressive permissions
  console.log('\n🌐 Launching browser...');
  
  const browser = await chromium.launch({
    headless: false,
    args: [
      '--disable-blink-features=AutomationControlled',
      '--autoplay-policy=no-user-gesture-required',
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      // Force grant all permissions
      '--enable-features=MediaStreamCamera'
    ]
  });

  const context = await browser.newContext({
    permissions: ['microphone', 'camera'],
    viewport: { width: 1400, height: 900 }
  });

  // Grant permissions to Zoom domain
  await context.grantPermissions(['microphone', 'camera'], { origin: 'https://zoom.us' });
  await context.grantPermissions(['microphone', 'camera'], { origin: 'https://app.zoom.us' });

  // Step 4: Load avatar page
  console.log('\n🎭 Loading HeyGen avatar...');
  const avatarPage = await context.newPage();
  await avatarPage.goto(`http://localhost:${PORT}`, { waitUntil: 'domcontentloaded' });

  console.log('   ⏳ Waiting for avatar stream...');
  try {
    await avatarPage.waitForFunction(() => window.__avatarReady === true, { timeout: 45000 });
    console.log('   ✓ Avatar connected!');
  } catch {
    console.log('   ⚠️ Avatar timeout, continuing...');
  }

  await avatarPage.waitForTimeout(3000);

  // Step 5: Open Zoom with comprehensive camera hook
  console.log('\n🔗 Opening Zoom...');
  const zoomPage = await context.newPage();

  // More aggressive hook that intercepts ALL camera requests
  await zoomPage.addInitScript(`
    (function() {
      console.log('[HOOK] Installing comprehensive camera hook...');
      
      // Create our fake camera canvas
      const canvas = document.createElement('canvas');
      canvas.width = 640;
      canvas.height = 480;
      const ctx = canvas.getContext('2d');
      
      // Initial frame
      ctx.fillStyle = '#1a1a2e';
      ctx.fillRect(0, 0, 640, 480);
      ctx.fillStyle = '#fff';
      ctx.font = '24px system-ui';
      ctx.textAlign = 'center';
      ctx.fillText('AI Professor', 320, 240);
      
      // Create stream
      const fakeVideoStream = canvas.captureStream(30);
      const fakeVideoTrack = fakeVideoStream.getVideoTracks()[0];
      
      // Store globally for frame updates
      window.__fakeCanvas = canvas;
      window.__fakeCtx = ctx;
      window.__fakeVideoTrack = fakeVideoTrack;
      window.__fakeVideoStream = fakeVideoStream;
      
      // Store original methods
      const origGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      const origEnumerateDevices = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
      
      // Override getUserMedia
      navigator.mediaDevices.getUserMedia = async function(constraints) {
        console.log('[HOOK] getUserMedia called:', JSON.stringify(constraints));
        
        if (constraints && constraints.video) {
          console.log('[HOOK] Returning fake video stream!');
          
          const resultStream = new MediaStream();
          
          // Always add our fake video
          resultStream.addTrack(window.__fakeVideoTrack.clone());
          
          // Try to get real audio if requested
          if (constraints.audio) {
            try {
              const audioStream = await origGetUserMedia({ audio: constraints.audio, video: false });
              audioStream.getAudioTracks().forEach(t => resultStream.addTrack(t));
            } catch (e) {
              console.log('[HOOK] Audio failed:', e.message);
            }
          }
          
          return resultStream;
        }
        
        return origGetUserMedia(constraints);
      };
      
      // Override enumerateDevices to show our fake camera
      navigator.mediaDevices.enumerateDevices = async function() {
        const devices = await origEnumerateDevices();
        
        // Check if we already have a video input
        const hasVideo = devices.some(d => d.kind === 'videoinput');
        if (!hasVideo) {
          devices.push({
            deviceId: 'heygen-avatar-camera',
            groupId: 'heygen-group',
            kind: 'videoinput',
            label: 'HeyGen Avatar Camera'
          });
        }
        
        return devices;
      };
      
      // Also hook the older getUserMedia API
      if (navigator.getUserMedia) {
        navigator.getUserMedia = function(constraints, success, error) {
          navigator.mediaDevices.getUserMedia(constraints).then(success).catch(error);
        };
      }
      
      // Hook MediaStreamTrack.getSources (legacy)
      if (MediaStreamTrack && MediaStreamTrack.getSources) {
        const origGetSources = MediaStreamTrack.getSources.bind(MediaStreamTrack);
        MediaStreamTrack.getSources = function(callback) {
          origGetSources(function(sources) {
            sources.push({
              id: 'heygen-avatar-camera',
              kind: 'video',
              label: 'HeyGen Avatar Camera',
              facing: 'user'
            });
            callback(sources);
          });
        };
      }
      
      console.log('[HOOK] All camera hooks installed!');
    })();
  `);

  await zoomPage.goto(`https://zoom.us/wc/join/${MEETING_ID}`, { 
    waitUntil: 'networkidle', 
    timeout: 60000 
  });

  // Start frame relay from avatar to zoom
  console.log('   🔄 Starting frame relay...');
  
  let relayActive = true;
  const relayFrames = async () => {
    let frameCount = 0;
    while (relayActive) {
      try {
        const frameData = await avatarPage.evaluate(() => {
          const canvas = document.getElementById('canvas');
          if (canvas) return canvas.toDataURL('image/jpeg', 0.85);
          return null;
        });

        if (frameData) {
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
          if (frameCount % 200 === 0) {
            console.log(`   📊 Relayed ${frameCount} frames`);
          }
        }
        
        await new Promise(r => setTimeout(r, 50)); // ~20 fps
      } catch (e) {
        if (relayActive) {
          console.log('   ⚠️ Frame relay error:', e.message);
        }
        break;
      }
    }
  };

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

  console.log('\n⏳ Waiting to be admitted...');
  console.log('   (You need to admit the bot from the host side)');

  // Monitor for meeting join and handle any camera prompts
  const handleMeetingJoin = async () => {
    for (let i = 0; i < 30; i++) {
      await zoomPage.waitForTimeout(2000);
      
      // Look for "enable camera" prompt and click it
      try {
        const enableBtn = await zoomPage.$('button:has-text("Enable"), button:has-text("Allow"), button:has-text("OK")');
        if (enableBtn) {
          const text = await enableBtn.textContent();
          console.log(`   🔘 Found button: "${text}" - clicking...`);
          await enableBtn.click();
        }
      } catch {}
      
      // Check if we're in meeting (look for participant panel, chat, etc)
      const inMeeting = await zoomPage.$('.meeting-client, .meeting-app, [class*="MeetingClient"]');
      if (inMeeting) {
        console.log('   ✓ In meeting!');
        
        // Try to start video
        await zoomPage.waitForTimeout(2000);
        
        const videoButtons = [
          'button[aria-label*="Start Video" i]',
          'button[aria-label*="start my video" i]',
          'button[aria-label*="turn on camera" i]',
          '.footer-button-base__button[aria-label*="video" i]',
          '[data-testid="video-button"]'
        ];
        
        for (const selector of videoButtons) {
          try {
            const btn = await zoomPage.$(selector);
            if (btn) {
              const label = await btn.getAttribute('aria-label') || '';
              if (label.toLowerCase().includes('start') || !label.toLowerCase().includes('stop')) {
                console.log(`   🎥 Clicking video button: ${label}`);
                await btn.click();
                await zoomPage.waitForTimeout(1000);
              }
            }
          } catch {}
        }
        
        break;
      }
      
      // Check for waiting room message
      const waitingRoom = await zoomPage.$('text=waiting for the host');
      if (waitingRoom) {
        console.log(`   ⏳ In waiting room... (${i + 1}/30)`);
      }
    }
  };

  handleMeetingJoin();

  console.log('\n✅ Bot is running!');
  console.log('   - HeyGen avatar is streaming');
  console.log('   - Camera hook is active');
  console.log('   - Frame relay is running');
  
  // Test speech after delay
  setTimeout(async () => {
    console.log('\n🗣️ Testing avatar speech...');
    try {
      await speakText(sessionId, 'Hello! I am your AI Professor.');
    } catch (e) {
      console.log('   Speech error:', e.message);
    }
  }, 15000);

  console.log('\n⏳ Press Ctrl+C to exit.');
  await new Promise(() => {});
}

main().catch(err => {
  console.error('\n❌ Error:', err);
  process.exit(1);
});
