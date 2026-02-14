/**
 * Simple Zoom Meeting Join Test using Playwright
 * Uses Component View (embedded) for better automation support
 * 
 * Usage: node simple-join-test.js
 */

const { chromium } = require('playwright');
const { KJUR } = require('jsrsasign');
require('dotenv').config();

// Meeting details - hardcoded for this test
const MEETING_NUMBER = '89711545987';
const PASSCODE = '926454';
const BOT_NAME = 'Test Bot';

// Get SDK credentials from .env
const SDK_KEY = process.env.ZOOM_SDK_KEY;
const SDK_SECRET = process.env.ZOOM_SDK_SECRET;

if (!SDK_KEY || !SDK_SECRET) {
  console.error('❌ Missing ZOOM_SDK_KEY or ZOOM_SDK_SECRET in .env');
  process.exit(1);
}

/**
 * Generate Meeting SDK JWT using the official method
 * @param {string} sdkKey - Your SDK Key
 * @param {string} sdkSecret - Your SDK Secret
 * @param {string} meetingNumber - The meeting number
 * @param {number} role - 0 for attendee, 1 for host
 * @returns {string} JWT signature
 */
function generateSignature(sdkKey, sdkSecret, meetingNumber, role = 0) {
  const iat = Math.floor(Date.now() / 1000);
  const exp = iat + 60 * 60 * 2; // 2 hours

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

  const sHeader = JSON.stringify(oHeader);
  const sPayload = JSON.stringify(oPayload);
  
  return KJUR.jws.JWS.sign('HS256', sHeader, sPayload, sdkSecret);
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
  console.log(`✅ Signature generated (${signature.length} chars)`);
  console.log('');

  // Launch browser
  console.log('🚀 Launching browser...');
  const browser = await chromium.launch({
    headless: false,
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      '--disable-web-security',
      '--allow-running-insecure-content'
    ]
  });

  const context = await browser.newContext({
    permissions: ['microphone', 'camera'],
    viewport: { width: 1280, height: 720 }
  });

  const page = await context.newPage();

  // Log console messages
  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();
    if (type === 'error') {
      console.log(`[CONSOLE ERROR] ${text}`);
    } else if (type === 'warning') {
      console.log(`[CONSOLE WARN] ${text}`);
    } else if (text.includes('[Zoom]') || text.includes('Zoom') || text.includes('meeting')) {
      console.log(`[CONSOLE] ${text}`);
    }
  });

  // Log page errors
  page.on('pageerror', err => {
    console.error(`[PAGE ERROR] ${err.message}`);
  });

  // Create an HTML page with the Component View SDK
  const htmlContent = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Zoom Bot Test</title>
  <style>
    body { 
      margin: 0; 
      padding: 20px; 
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      background: #1a1a1a;
      color: white;
    }
    #status { 
      padding: 10px; 
      margin-bottom: 20px;
      background: #333;
      border-radius: 8px;
    }
    #meetingSDKElement {
      width: 100%;
      height: 600px;
      background: #000;
      border-radius: 8px;
    }
  </style>
</head>
<body>
  <div id="status">Initializing...</div>
  <div id="meetingSDKElement"></div>

  <script src="https://source.zoom.us/3.7.0/lib/vendor/react.min.js"></script>
  <script src="https://source.zoom.us/3.7.0/lib/vendor/react-dom.min.js"></script>
  <script src="https://source.zoom.us/3.7.0/lib/vendor/redux.min.js"></script>
  <script src="https://source.zoom.us/3.7.0/lib/vendor/redux-thunk.min.js"></script>
  <script src="https://source.zoom.us/3.7.0/lib/vendor/lodash.min.js"></script>
  <script src="https://source.zoom.us/zoom-meeting-embedded-3.7.0.min.js"></script>

  <script>
    window.joinState = { status: 'initializing', error: null };
    
    const updateStatus = (text) => {
      document.getElementById('status').textContent = text;
      console.log('[Zoom Status] ' + text);
    };

    window.initAndJoin = async (config) => {
      try {
        updateStatus('Creating Zoom client...');
        
        const client = ZoomMtgEmbedded.createClient();
        window.zoomClient = client;

        const meetingSDKElement = document.getElementById('meetingSDKElement');

        updateStatus('Initializing Zoom SDK...');
        await client.init({
          zoomAppRoot: meetingSDKElement,
          language: 'en-US',
          patchJsMedia: true,
          leaveOnPageUnload: true
        });

        updateStatus('Joining meeting...');
        await client.join({
          sdkKey: config.sdkKey,
          signature: config.signature,
          meetingNumber: config.meetingNumber,
          password: config.password,
          userName: config.userName,
          success: (success) => {
            console.log('[Zoom] Join success:', success);
            window.joinState.status = 'joined';
            updateStatus('✅ Successfully joined the meeting!');
          },
          error: (error) => {
            console.error('[Zoom] Join error:', error);
            window.joinState.status = 'error';
            window.joinState.error = error;
            updateStatus('❌ Failed to join: ' + JSON.stringify(error));
          }
        });

        // If we get here without error, we're connected
        window.joinState.status = 'joined';
        updateStatus('✅ Connected to meeting!');

      } catch (error) {
        console.error('[Zoom] Exception:', error);
        window.joinState.status = 'error';
        window.joinState.error = error.message || error;
        updateStatus('❌ Error: ' + (error.message || error));
      }
    };
  </script>
</body>
</html>
`;

  // Load the page as data URL
  console.log('📄 Loading Zoom SDK page...');
  await page.setContent(htmlContent, { waitUntil: 'domcontentloaded' });

  // Wait for SDK to load
  console.log('⏳ Waiting for Zoom SDK to load...');
  try {
    await page.waitForFunction(() => typeof ZoomMtgEmbedded !== 'undefined', { timeout: 30000 });
    console.log('✅ Zoom SDK loaded');
  } catch (e) {
    console.error('❌ SDK failed to load:', e.message);
    await browser.close();
    process.exit(1);
  }

  // Join the meeting
  console.log('🔗 Attempting to join meeting...');
  await page.evaluate((config) => {
    window.initAndJoin(config);
  }, {
    sdkKey: SDK_KEY,
    signature: signature,
    meetingNumber: MEETING_NUMBER,
    password: PASSCODE,
    userName: BOT_NAME
  });

  // Monitor join status
  console.log('⏳ Waiting for join result...');
  let joined = false;
  
  for (let i = 0; i < 120; i++) { // 2 minute timeout
    await page.waitForTimeout(1000);
    
    const state = await page.evaluate(() => window.joinState);
    
    if (state.status === 'joined') {
      console.log('\n🎉 SUCCESS! Bot joined the meeting!');
      joined = true;
      break;
    }
    
    if (state.status === 'error') {
      console.log('\n❌ JOIN FAILED!');
      console.log('Error:', state.error);
      break;
    }
    
    if (i % 10 === 0) {
      console.log(`  [${i}s] Status: ${state.status}`);
    }
  }

  if (joined) {
    console.log('\n✅ Bot is in the meeting. Keeping browser open for 60 seconds...');
    console.log('   (You can interact with the meeting in the browser window)');
    await page.waitForTimeout(60000);
  } else {
    console.log('\n⚠️ Keeping browser open for 30 seconds for debugging...');
    await page.waitForTimeout(30000);
  }

  console.log('\n🛑 Closing browser...');
  await browser.close();
  console.log('Done.');
}

main().catch(err => {
  console.error('\n❌ Fatal error:', err);
  process.exit(1);
});
