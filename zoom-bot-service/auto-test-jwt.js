/**
 * Fully automated test using JWT API credentials
 * Creates a meeting and joins it automatically
 */
const puppeteer = require('puppeteer');
const crypto = require('crypto');
const path = require('path');
const axios = require('axios');
const jwt = require('jsonwebtoken');
require('dotenv').config();

function generateZoomAPIToken(apiKey, apiSecret) {
  const payload = {
    iss: apiKey,
    exp: Math.floor(Date.now() / 1000) + 3600 // 1 hour
  };
  return jwt.sign(payload, apiSecret);
}

function generateSDKSignature(sdkKey, sdkSecret, meetingNumber, role = 0) {
  const iat = Math.floor(Date.now() / 1000) - 30;
  const exp = iat + 60 * 60 * 2;

  const header = { alg: 'HS256', typ: 'JWT' };
  const payload = {
    sdkKey: sdkKey,
    mn: meetingNumber,
    role: role,
    iat: iat,
    exp: exp,
    appKey: sdkKey,
    tokenExp: exp
  };

  const encodedHeader = Buffer.from(JSON.stringify(header)).toString('base64url');
  const encodedPayload = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const signatureInput = `${encodedHeader}.${encodedPayload}`;
  const signature = crypto.createHmac('sha256', sdkSecret).update(signatureInput).digest('base64url');

  return `${encodedHeader}.${encodedPayload}.${signature}`;
}

async function createMeeting(token) {
  const response = await axios.post(
    'https://api.zoom.us/v2/users/me/meetings',
    {
      topic: 'Automated Bot Test Meeting',
      type: 1, // Instant meeting
      settings: {
        join_before_host: true,
        waiting_room: false,
        mute_upon_entry: false
      }
    },
    {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    }
  );

  return {
    id: response.data.id.toString(),
    password: response.data.password,
    join_url: response.data.join_url
  };
}

async function main() {
  console.log('\n🤖 Automated Zoom Bot Test (JWT)');
  console.log('=================================\n');

  const API_KEY = process.env.ZOOM_API_KEY;
  const API_SECRET = process.env.ZOOM_API_SECRET;
  const SDK_KEY = process.env.ZOOM_SDK_KEY;
  const SDK_SECRET = process.env.ZOOM_SDK_SECRET;

  if (!API_KEY || !API_SECRET) {
    console.error('❌ Missing ZOOM_API_KEY or ZOOM_API_SECRET');
    process.exit(1);
  }

  // Step 1: Generate API token
  console.log('🔑 Generating Zoom API token...');
  const apiToken = generateZoomAPIToken(API_KEY, API_SECRET);
  console.log('✅ Token generated\n');

  // Step 2: Create meeting
  console.log('📅 Creating test meeting...');
  let meeting;
  try {
    meeting = await createMeeting(apiToken);
    console.log('✅ Meeting created!');
    console.log('   ID:', meeting.id);
    console.log('   Password:', meeting.password);
    console.log('   URL:', meeting.join_url);
    console.log('');
  } catch (error) {
    console.error('❌ Failed to create meeting:', error.response?.data || error.message);
    process.exit(1);
  }

  // Step 3: Generate SDK signature
  console.log('📝 Generating SDK signature...');
  const sdkSignature = generateSDKSignature(SDK_KEY, SDK_SECRET, meeting.id, 0);
  console.log('✅ Signature generated\n');

  // Step 4: Launch browser and join
  console.log('🚀 Launching browser (non-headless so you can see)...');
  const browser = await puppeteer.launch({
    headless: false,
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-web-security'
    ]
  });

  const page = await browser.newPage();

  // Log page console
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('[Bot]')) {
      console.log('  ' + text);
    }
  });

  const htmlPath = 'file://' + path.join(__dirname, 'public', 'zoom-bot.html');
  console.log('📄 Loading:', htmlPath);
  await page.goto(htmlPath, { waitUntil: 'networkidle2' });

  console.log('⏳ Waiting for Zoom SDK to load...');
  await page.waitForFunction(() => typeof window.ZoomMtg !== 'undefined', { timeout: 10000 });
  console.log('✅ SDK loaded\n');

  console.log('🔗 Joining meeting...\n');
  await page.evaluate((config) => {
    window.joinMeeting({
      sdkKey: config.sdkKey,
      signature: config.signature,
      meetingNumber: config.meetingNumber,
      userName: 'Automated Test Bot',
      password: config.password
    });
  }, {
    sdkKey: SDK_KEY,
    signature: sdkSignature,
    meetingNumber: meeting.id,
    password: meeting.password
  });

  console.log('⏳ Waiting for join result (max 60 seconds)...\n');

  let success = false;
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 1000));

    const state = await page.evaluate(() => window.botState);

    if (state.status === 'joined') {
      console.log('\n🎉 🎉 🎉 SUCCESS! 🎉 🎉 🎉');
      console.log('✅ Bot successfully joined the meeting!');
      console.log('\n📺 You can verify by visiting:', meeting.join_url);
      console.log('\nKeeping browser open for 30 seconds so you can verify...');
      success = true;
      await new Promise(r => setTimeout(r, 30000));
      break;
    }

    if (state.status === 'error') {
      console.log('\n❌ JOIN FAILED');
      console.log('Error:', state.error);
      console.log('\nKeeping browser open for 60 seconds so you can inspect...');
      await new Promise(r => setTimeout(r, 60000));
      break;
    }

    if (i % 5 === 0) {
      console.log(`  [${i}s] Status: ${state.status}`);
    }
  }

  await browser.close();

  if (success) {
    console.log('\n✅ ✅ ✅ ALL TESTS PASSED! ✅ ✅ ✅');
    console.log('The Zoom bot is working correctly!\n');
  } else {
    console.log('\n❌ Test failed - check errors above\n');
    process.exit(1);
  }
}

main().catch(err => {
  console.error('\n❌ Fatal error:', err.message);
  if (err.response) {
    console.error('Response:', err.response.data);
  }
  process.exit(1);
});
