/**
 * Fully automated test - creates a meeting, then joins it
 *
 * Setup (one-time):
 * 1. Go to: https://marketplace.zoom.us/develop/create
 * 2. Click "Server-to-Server OAuth"
 * 3. Fill in app name (anything), company name, contact email
 * 4. Click "Create"
 * 5. Copy Account ID, Client ID, Client Secret to .env file as:
 *    ZOOM_ACCOUNT_ID=xxx
 *    ZOOM_CLIENT_ID=xxx
 *    ZOOM_CLIENT_SECRET=xxx
 * 6. Go to "Scopes" tab, add: meeting:write, meeting:read
 * 7. Click "Continue", then "Activate"
 *
 * Then run: node auto-test.js
 */
const puppeteer = require('puppeteer');
const crypto = require('crypto');
const path = require('path');
const axios = require('axios');
require('dotenv').config();

async function getZoomAccessToken() {
  const accountId = process.env.ZOOM_ACCOUNT_ID;
  const clientId = process.env.ZOOM_CLIENT_ID;
  const clientSecret = process.env.ZOOM_CLIENT_SECRET;

  if (!accountId || !clientId || !clientSecret) {
    console.error('\n❌ Missing OAuth credentials in .env file!');
    console.error('\n📋 Quick Setup (takes 2 minutes):');
    console.error('1. Go to: https://marketplace.zoom.us/develop/create');
    console.error('2. Click "Server-to-Server OAuth"');
    console.error('3. Fill in app name, company name, email (anything works)');
    console.error('4. Copy the credentials to .env file:');
    console.error('   ZOOM_ACCOUNT_ID=your_account_id');
    console.error('   ZOOM_CLIENT_ID=your_client_id');
    console.error('   ZOOM_CLIENT_SECRET=your_client_secret');
    console.error('5. Click "Scopes" tab, add: meeting:write, meeting:read');
    console.error('6. Click "Continue", then "Activate"');
    console.error('\nThen run: node auto-test.js\n');
    process.exit(1);
  }

  const authString = Buffer.from(`${clientId}:${clientSecret}`).toString('base64');

  const response = await axios.post(
    `https://zoom.us/oauth/token?grant_type=account_credentials&account_id=${accountId}`,
    {},
    {
      headers: {
        'Authorization': `Basic ${authString}`,
        'Content-Type': 'application/json'
      }
    }
  );

  return response.data.access_token;
}

async function createZoomMeeting(accessToken) {
  const response = await axios.post(
    'https://api.zoom.us/v2/users/me/meetings',
    {
      topic: 'Bot Test Meeting',
      type: 1, // Instant meeting
      settings: {
        join_before_host: true,
        waiting_room: false,
        mute_upon_entry: false
      }
    },
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
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

function generateJWT(sdkKey, sdkSecret, meetingNumber, role = 0) {
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

async function main() {
  console.log('\n🤖 Fully Automated Zoom Bot Test');
  console.log('================================\n');

  // Step 1: Get OAuth token
  console.log('🔑 Getting Zoom OAuth token...');
  const accessToken = await getZoomAccessToken();
  console.log('✅ Got access token\n');

  // Step 2: Create meeting
  console.log('📅 Creating test meeting...');
  const meeting = await createZoomMeeting(accessToken);
  console.log('✅ Meeting created!');
  console.log('   ID:', meeting.id);
  console.log('   Password:', meeting.password);
  console.log('   URL:', meeting.join_url);
  console.log('');

  // Step 3: Generate SDK signature
  const SDK_KEY = process.env.ZOOM_SDK_KEY;
  const SDK_SECRET = process.env.ZOOM_SDK_SECRET;

  console.log('📝 Generating SDK signature...');
  const signature = generateJWT(SDK_KEY, SDK_SECRET, meeting.id, 0);
  console.log('✅ Signature generated\n');

  // Step 4: Launch browser and join
  console.log('🚀 Launching browser...');
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

  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('[Bot]')) {
      console.log('  ' + text);
    }
  });

  const htmlPath = 'file://' + path.join(__dirname, 'public', 'zoom-bot.html');
  await page.goto(htmlPath, { waitUntil: 'networkidle2' });

  console.log('⏳ Waiting for Zoom SDK...');
  await page.waitForFunction(() => typeof window.ZoomMtg !== 'undefined', { timeout: 10000 });
  console.log('✅ SDK loaded\n');

  console.log('🔗 Joining meeting...\n');
  await page.evaluate((config) => {
    window.joinMeeting({
      sdkKey: config.sdkKey,
      signature: config.signature,
      meetingNumber: config.meetingNumber,
      userName: 'Auto Test Bot',
      password: config.password
    });
  }, {
    sdkKey: SDK_KEY,
    signature,
    meetingNumber: meeting.id,
    password: meeting.password
  });

  console.log('⏳ Waiting for join...\n');

  let success = false;
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 1000));

    const state = await page.evaluate(() => window.botState);

    if (state.status === 'joined') {
      console.log('\n🎉 🎉 🎉 SUCCESS! 🎉 🎉 🎉');
      console.log('Bot successfully joined the meeting!');
      console.log('\nYou can verify by going to:', meeting.join_url);
      console.log('\nKeeping browser open for 30 seconds...');
      success = true;
      await new Promise(r => setTimeout(r, 30000));
      break;
    }

    if (state.status === 'error') {
      console.log('\n❌ JOIN FAILED');
      console.log('Error:', state.error);
      console.log('\nKeeping browser open for inspection...');
      await new Promise(r => setTimeout(r, 60000));
      break;
    }

    if (i % 5 === 0) {
      console.log(`  [${i}s] Status: ${state.status}`);
    }
  }

  await browser.close();

  if (success) {
    console.log('\n✅ ✅ ✅ TEST PASSED! ✅ ✅ ✅');
    console.log('The Zoom bot is working correctly!');
  } else {
    console.log('\n❌ Test failed - see errors above');
  }
}

main().catch(err => {
  console.error('\n❌ Fatal error:', err.message);
  if (err.response) {
    console.error('API Error:', err.response.data);
  }
  process.exit(1);
});
