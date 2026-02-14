/**
 * HeyGen Avatar → Zoom Bot (Working Solution)
 * 
 * This solution:
 * 1. Connects to HeyGen and captures avatar frames to a video file
 * 2. Restarts browser with the video file as fake camera
 * 3. Joins Zoom with the avatar as camera
 * 
 * Usage: HEYGEN_API_KEY=xxx node heygen-zoom-working.js
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');
require('dotenv').config();

// Config
const MEETING_ID = process.env.ZOOM_MEETING_ID || '89711545987';
const PASSCODE = process.env.ZOOM_PASSCODE || '926454';
const BOT_NAME = process.env.BOT_NAME || 'AI Professor';
const HEYGEN_API_KEY = process.env.HEYGEN_API_KEY;

const CAPTURE_DURATION = 10; // seconds to capture avatar
const VIDEO_FILE = path.join(__dirname, 'avatar-capture.webm');

if (!HEYGEN_API_KEY) {
  console.error('❌ HEYGEN_API_KEY required');
  console.error('   Set HEYGEN_API_KEY in .env or pass as environment variable');
  process.exit(1);
}

// HeyGen API
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
          if (j.error) reject(new Error(j.error.message || JSON.stringify(j.error)));
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
  console.log('\n🎭 HeyGen Avatar → Zoom Bot');
  console.log('═'.repeat(50));
  
  let sessionId = null;
  let server = null;

  try {
    // Step 1: Create and start HeyGen session
    console.log('\n📡 Creating HeyGen avatar session...');
    const session = await heygenAPI('/streaming.new', {
      quality: 'medium',
      video_encoding: 'VP8',
      version: 'v2',
      disable_idle_timeout: true
    });
    sessionId = session.session_id;
    console.log(`   ✓ Session: ${sessionId.substring(0, 20)}...`);

    console.log('▶️  Starting session...');
    await heygenAPI('/streaming.start', { session_id: sessionId });
    console.log('   ✓ Session active');

    // Step 2: Create local server
    const PORT = 9999;
    server = http.createServer((_, res) => {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(captureHTML(session, sessionId));
    });
    await new Promise(r => server.listen(PORT, r));

    // Step 3: Capture avatar video
    console.log(`\n📹 Capturing ${CAPTURE_DURATION}s of avatar video...`);
    
    let browser = await chromium.launch({ headless: false });
    let context = await browser.newContext({ 
      permissions: ['microphone', 'camera'],
      recordVideo: { dir: __dirname, size: { width: 640, height: 480 } }
    });
    let page = await context.newPage();

    page.on('console', msg => {
      if (msg.text().includes('[')) console.log(`   ${msg.text()}`);
    });

    await page.goto(`http://localhost:${PORT}`);
    
    // Wait for avatar to connect
    console.log('   Waiting for avatar...');
    await page.waitForFunction(() => window.__ready === true, { timeout: 60000 });
    console.log('   ✓ Avatar streaming');

    // Make avatar say something
    console.log('   Making avatar speak...');
    await page.evaluate(async () => {
      await window.speakText("Hello! I'm your AI assistant. I'm ready to join the meeting now.");
    });
    
    // Wait for capture
    console.log(`   Recording ${CAPTURE_DURATION} seconds...`);
    await page.waitForTimeout(CAPTURE_DURATION * 1000);

    // Get the recorded video
    await page.close();
    const video = await page.video();
    const videoPath = await video?.path();
    
    await context.close();
    await browser.close();

    if (videoPath && fs.existsSync(videoPath)) {
      // Move to our target location
      fs.renameSync(videoPath, VIDEO_FILE);
      console.log(`   ✓ Video saved: ${VIDEO_FILE}`);
    } else {
      console.log('   ⚠️ Video recording not available, using live mode');
    }

    // Step 4: Join Zoom with captured/live avatar
    console.log('\n🔗 Opening Zoom with avatar camera...');
    
    browser = await chromium.launch({
      headless: false,
      args: [
        '--use-fake-ui-for-media-stream',
        '--use-fake-device-for-media-stream',
        fs.existsSync(VIDEO_FILE) ? `--use-file-for-fake-video-capture=${VIDEO_FILE}` : '',
        '--autoplay-policy=no-user-gesture-required'
      ].filter(Boolean)
    });

    context = await browser.newContext({
      permissions: ['microphone', 'camera'],
      viewport: { width: 1280, height: 800 }
    });

    page = await context.newPage();
    
    page.on('console', msg => {
      const t = msg.text();
      if (t.includes('Zoom') || msg.type() === 'error') {
        console.log(`[Zoom] ${t}`);
      }
    });

    // Go to Zoom join page
    const zoomUrl = `https://zoom.us/wc/join/${MEETING_ID}`;
    console.log(`   Navigating to: ${zoomUrl}`);
    await page.goto(zoomUrl, { waitUntil: 'domcontentloaded' });

    // Wait a bit for page to load
    await page.waitForTimeout(3000);

    // Try to fill in the name and passcode
    console.log('   Looking for input fields...');
    
    // Screenshot for debugging
    await page.screenshot({ path: path.join(__dirname, 'zoom-step1.png') });

    // Look for name input
    try {
      const nameInput = await page.waitForSelector('input[name="name"], input#inputname, input[placeholder*="name" i]', { timeout: 10000 });
      await nameInput.fill(BOT_NAME);
      console.log(`   ✓ Entered name: ${BOT_NAME}`);
    } catch {
      console.log('   ⚠️ Name field not found');
    }

    // Look for passcode
    try {
      const pwdInput = await page.waitForSelector('input[type="password"], input[name="password"], input#inputpasscode', { timeout: 5000 });
      await pwdInput.fill(PASSCODE);
      console.log(`   ✓ Entered passcode`);
    } catch {
      console.log('   ⚠️ Passcode field not found (may not be needed)');
    }

    await page.screenshot({ path: path.join(__dirname, 'zoom-step2.png') });

    // Click join button
    try {
      const joinBtn = await page.waitForSelector('button:has-text("Join"), button[type="submit"], .zm-btn--primary', { timeout: 5000 });
      await joinBtn.click();
      console.log('   ✓ Clicked join button');
    } catch {
      console.log('   ⚠️ Join button not found');
    }

    await page.waitForTimeout(5000);
    await page.screenshot({ path: path.join(__dirname, 'zoom-step3.png') });

    // Check for "join from browser" link
    try {
      const browserLink = await page.waitForSelector('a:has-text("Join from Your Browser"), a:has-text("join from your browser")', { timeout: 10000 });
      await browserLink.click();
      console.log('   ✓ Clicked "Join from Browser"');
    } catch {
      console.log('   ⚠️ Already in web client or link not found');
    }

    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(__dirname, 'zoom-step4.png') });

    console.log('\n' + '═'.repeat(50));
    console.log('✅ Bot is attempting to join the meeting!');
    console.log('   Check the browser window and screenshots.');
    console.log('   Screenshots saved to zoom-bot-service/zoom-step*.png');
    console.log('═'.repeat(50));
    console.log('\nKeeping browser open for 10 minutes...');
    console.log('   Press Ctrl+C to stop.');
    
    await page.waitForTimeout(600000);
    await browser.close();

  } catch (err) {
    console.error('\n❌ Error:', err.message);
    console.error(err.stack);
  } finally {
    // Cleanup
    if (sessionId) {
      console.log('\n🔄 Closing HeyGen session...');
      try { await heygenAPI('/streaming.stop', { session_id: sessionId }); } catch {}
    }
    if (server) server.close();
    
    // Clean up video file
    if (fs.existsSync(VIDEO_FILE)) {
      fs.unlinkSync(VIDEO_FILE);
    }
  }
  
  console.log('✅ Done');
}

function captureHTML(session, sessionId) {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>HeyGen Capture</title>
  <style>
    body { margin: 0; background: #000; display: flex; justify-content: center; align-items: center; height: 100vh; }
    video { width: 640px; height: 480px; object-fit: cover; }
    #status { position: fixed; top: 10px; left: 10px; color: #0f0; font-family: monospace; background: rgba(0,0,0,0.8); padding: 8px 12px; border-radius: 4px; }
  </style>
</head>
<body>
  <div id="status">Connecting...</div>
  <video id="vid" autoplay playsinline></video>
  
  <script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
  <script>
    window.__ready = false;
    const vid = document.getElementById('vid');
    const status = document.getElementById('status');
    
    window.speakText = async (text) => {
      await fetch('https://api.heygen.com/v1/streaming.task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-api-key': '${HEYGEN_API_KEY}' },
        body: JSON.stringify({ session_id: '${sessionId}', text, task_type: 'talk' })
      });
    };
    
    async function connect() {
      const room = new LivekitClient.Room();
      
      room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, pub, part) => {
        console.log('[HeyGen] Track:', track.kind);
        if (track.kind === 'video') {
          track.attach(vid);
          window.__ready = true;
          status.textContent = '✓ Avatar connected';
          console.log('[HeyGen] Video attached');
        }
      });
      
      try {
        status.textContent = 'Connecting to LiveKit...';
        await room.connect('${session.url}', '${session.access_token}');
        status.textContent = 'Connected, waiting for video...';
        console.log('[HeyGen] Connected to room');
      } catch (e) {
        status.textContent = 'Error: ' + e.message;
        console.error('[HeyGen] Error:', e);
      }
    }
    
    connect();
  </script>
</body>
</html>`;
}

main();
