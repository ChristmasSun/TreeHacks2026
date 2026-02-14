/**
 * Zoom Meeting Join Test using Playwright + Local Server
 * 
 * Usage: node join-meeting-test.js
 */

const { chromium } = require('playwright');
const { KJUR } = require('jsrsasign');
const http = require('http');
const path = require('path');
require('dotenv').config();

// Meeting details
const MEETING_NUMBER = '89711545987';
const PASSCODE = '926454';
const BOT_NAME = 'Test Bot';

// Get SDK credentials
const SDK_KEY = process.env.ZOOM_SDK_KEY;
const SDK_SECRET = process.env.ZOOM_SDK_SECRET;

if (!SDK_KEY || !SDK_SECRET) {
  console.error('❌ Missing ZOOM_SDK_KEY or ZOOM_SDK_SECRET in .env');
  process.exit(1);
}

/**
 * Generate Meeting SDK JWT using KJUR
 */
function generateSignature(sdkKey, sdkSecret, meetingNumber, role = 0) {
  const iat = Math.floor(Date.now() / 1000);
  const exp = iat + 60 * 60 * 2;

  const oHeader = { alg: 'HS256', typ: 'JWT' };
  const oPayload = {
    appKey: sdkKey,
    sdkKey: sdkKey,
    mn: meetingNumber,
    role: role,
    iat: iat,
    exp: exp,
    tokenExp: exp
  };

  return KJUR.jws.JWS.sign('HS256', JSON.stringify(oHeader), JSON.stringify(oPayload), sdkSecret);
}

/**
 * Create HTML content for the test page
 */
function createHTML(config) {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Zoom Bot Test</title>
  <link type="text/css" rel="stylesheet" href="https://source.zoom.us/3.7.0/css/bootstrap.css" />
  <link type="text/css" rel="stylesheet" href="https://source.zoom.us/3.7.0/css/react-select.css" />
  <style>
    body { margin: 0; padding: 20px; font-family: sans-serif; background: #1a1a1a; color: white; }
    #status { padding: 15px; margin-bottom: 20px; background: #333; border-radius: 8px; font-family: monospace; }
    #zmmtg-root { display: none; }
  </style>
</head>
<body>
  <div id="status">Loading Zoom SDK...</div>
  <div id="zmmtg-root"></div>

  <script src="https://source.zoom.us/3.7.0/lib/vendor/react.min.js"></script>
  <script src="https://source.zoom.us/3.7.0/lib/vendor/react-dom.min.js"></script>
  <script src="https://source.zoom.us/3.7.0/lib/vendor/redux.min.js"></script>
  <script src="https://source.zoom.us/3.7.0/lib/vendor/redux-thunk.min.js"></script>
  <script src="https://source.zoom.us/3.7.0/lib/vendor/lodash.min.js"></script>
  <script src="https://source.zoom.us/zoom-meeting-3.7.0.min.js"></script>

  <script>
    const config = ${JSON.stringify(config)};
    
    window.joinState = { status: 'loading', error: null };

    function updateStatus(msg) {
      document.getElementById('status').textContent = msg;
      console.log('[Status] ' + msg);
    }

    // Wait for SDK
    function waitForSDK() {
      return new Promise((resolve, reject) => {
        let attempts = 0;
        const check = () => {
          if (typeof ZoomMtg !== 'undefined') {
            resolve();
          } else if (attempts++ > 100) {
            reject(new Error('SDK load timeout'));
          } else {
            setTimeout(check, 100);
          }
        };
        check();
      });
    }

    async function startJoin() {
      try {
        updateStatus('Waiting for Zoom SDK...');
        await waitForSDK();
        
        updateStatus('Preloading WASM...');
        ZoomMtg.preLoadWasm();
        ZoomMtg.prepareWebSDK();
        
        window.joinState.status = 'initializing';
        updateStatus('Initializing Zoom...');

        ZoomMtg.init({
          leaveUrl: 'about:blank',
          isSupportAV: true,
          disableInvite: true,
          disableCallOut: true,
          disableRecord: true,
          disableJoinAudio: false,
          audioPanelAlwaysOpen: false,
          showMeetingHeader: false,
          disablePreview: true,
          videoDrag: false,
          sharingMode: 'both',
          videoHeader: false,
          isLockBottom: false,
          isSupportNonverbal: false,
          isShowJoiningErrorDialog: false,
          success: () => {
            console.log('[Zoom] Init success');
            window.joinState.status = 'joining';
            updateStatus('Joining meeting ' + config.meetingNumber + '...');

            ZoomMtg.join({
              signature: config.signature,
              sdkKey: config.sdkKey,
              meetingNumber: config.meetingNumber,
              userName: config.userName,
              passWord: config.password,
              success: (res) => {
                console.log('[Zoom] Join success:', res);
                window.joinState.status = 'joined';
                updateStatus('✅ JOINED SUCCESSFULLY!');
              },
              error: (err) => {
                console.error('[Zoom] Join error:', err);
                window.joinState.status = 'error';
                window.joinState.error = JSON.stringify(err);
                updateStatus('❌ Join failed: ' + JSON.stringify(err));
              }
            });
          },
          error: (err) => {
            console.error('[Zoom] Init error:', err);
            window.joinState.status = 'error';
            window.joinState.error = JSON.stringify(err);
            updateStatus('❌ Init failed: ' + JSON.stringify(err));
          }
        });

      } catch (error) {
        console.error('[Error]', error);
        window.joinState.status = 'error';
        window.joinState.error = error.message;
        updateStatus('❌ Error: ' + error.message);
      }
    }

    // Auto-start
    startJoin();
  </script>
</body>
</html>`;
}

async function main() {
  console.log('\n🤖 Zoom Meeting Join Test');
  console.log('='.repeat(40));
  console.log(`Meeting: ${MEETING_NUMBER}`);
  console.log(`Passcode: ${PASSCODE}`);
  console.log(`Bot Name: ${BOT_NAME}`);
  console.log('');

  // Generate signature
  console.log('📝 Generating JWT signature...');
  const signature = generateSignature(SDK_KEY, SDK_SECRET, MEETING_NUMBER, 0);
  console.log(`✅ Signature: ${signature.substring(0, 50)}...`);
  console.log('');

  // Create config
  const config = {
    sdkKey: SDK_KEY,
    signature: signature,
    meetingNumber: MEETING_NUMBER,
    password: PASSCODE,
    userName: BOT_NAME
  };

  // Create HTTP server
  const PORT = 8899;
  const html = createHTML(config);
  
  const server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(html);
  });

  await new Promise(resolve => server.listen(PORT, resolve));
  console.log(`🌐 Local server running at http://localhost:${PORT}`);
  console.log('');

  // Launch browser
  console.log('🚀 Launching browser...');
  const browser = await chromium.launch({
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

  // Log important console messages
  page.on('console', msg => {
    const text = msg.text();
    if (msg.type() === 'error' || text.includes('[Zoom]') || text.includes('[Status]') || text.includes('[Error]')) {
      console.log(`[PAGE] ${text}`);
    }
  });

  page.on('pageerror', err => {
    console.error(`[PAGE ERROR] ${err.message}`);
  });

  // Navigate to our server
  console.log('📄 Loading page...');
  await page.goto(`http://localhost:${PORT}`, { waitUntil: 'domcontentloaded' });

  // Monitor join status
  console.log('⏳ Monitoring join status...\n');
  
  for (let i = 0; i < 120; i++) {
    await page.waitForTimeout(1000);
    
    try {
      const state = await page.evaluate(() => window.joinState);
      
      if (state.status === 'joined') {
        console.log('\n🎉 SUCCESS! Bot joined the meeting!');
        console.log('   Browser will stay open for 60 seconds...');
        await page.waitForTimeout(60000);
        break;
      }
      
      if (state.status === 'error') {
        console.log('\n❌ JOIN FAILED!');
        console.log('Error:', state.error);
        console.log('\n   Browser will stay open for 30 seconds for debugging...');
        await page.waitForTimeout(30000);
        break;
      }
      
      if (i % 10 === 0) {
        console.log(`  [${i}s] Status: ${state.status}`);
      }
    } catch (e) {
      // Page might have navigated
    }
  }

  console.log('\n🛑 Closing...');
  await browser.close();
  server.close();
  console.log('Done.');
}

main().catch(err => {
  console.error('\n❌ Fatal error:', err);
  process.exit(1);
});
