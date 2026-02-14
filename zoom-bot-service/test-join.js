/**
 * Super simple test - just try to join a Zoom meeting
 * Usage: node test-join.js <meeting_number> [passcode]
 */
const puppeteer = require('puppeteer');
const crypto = require('crypto');
const path = require('path');
require('dotenv').config();

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
  const meetingNumber = process.argv[2];
  const passcode = process.argv[3] || '';

  if (!meetingNumber) {
    console.error('❌ Usage: node test-join.js <meeting_number> [passcode]');
    console.error('Example: node test-join.js 1234567890 abc123');
    console.error('\n💡 Start a Zoom meeting first, then run this with your meeting number');
    process.exit(1);
  }

  const SDK_KEY = process.env.ZOOM_SDK_KEY;
  const SDK_SECRET = process.env.ZOOM_SDK_SECRET;

  if (!SDK_KEY || !SDK_SECRET) {
    console.error('❌ Missing ZOOM_SDK_KEY or ZOOM_SDK_SECRET in .env file');
    process.exit(1);
  }

  console.log('\n🤖 Zoom Bot Join Test');
  console.log('==================');
  console.log('Meeting Number:', meetingNumber);
  console.log('Passcode:', passcode || '(none)');
  console.log('SDK Key:', SDK_KEY.substring(0, 10) + '...');
  console.log('');

  console.log('📝 Generating signature...');
  const signature = generateJWT(SDK_KEY, SDK_SECRET, meetingNumber, 0);
  console.log('✅ Signature generated:', signature.substring(0, 30) + '...\n');

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

  // Forward all console logs
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('[Bot]')) {
      console.log('  ' + text);
    }
  });

  const htmlPath = 'file://' + path.join(__dirname, 'public', 'zoom-bot.html');
  console.log('📄 Loading HTML:', htmlPath);
  await page.goto(htmlPath, { waitUntil: 'networkidle2' });

  console.log('⏳ Waiting for Zoom SDK to load...');
  await page.waitForFunction(() => typeof window.ZoomMtg !== 'undefined', { timeout: 10000 });
  console.log('✅ Zoom SDK loaded\n');

  console.log('🔗 Attempting to join meeting...\n');
  await page.evaluate((config) => {
    window.joinMeeting({
      sdkKey: config.sdkKey,
      signature: config.signature,
      meetingNumber: config.meetingNumber,
      userName: 'Test Bot ' + Math.floor(Math.random() * 1000),
      password: config.passcode
    });
  }, {
    sdkKey: SDK_KEY,
    signature,
    meetingNumber,
    passcode
  });

  console.log('⏳ Waiting for join result (60 seconds max)...\n');

  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 1000));

    const state = await page.evaluate(() => window.botState);

    if (state.status === 'joined') {
      console.log('\n✅ ✅ ✅ SUCCESS! Bot joined the meeting! ✅ ✅ ✅');
      console.log('Participant ID:', state.participantId);
      console.log('\nBrowser will stay open for 30 seconds so you can verify...');
      await new Promise(r => setTimeout(r, 30000));
      break;
    }

    if (state.status === 'error') {
      console.log('\n❌ ERROR:', state.error);
      console.log('\nBrowser will stay open so you can inspect...');
      await new Promise(r => setTimeout(r, 60000));
      break;
    }

    if (i % 5 === 0) {
      console.log(`  [${i}s] Status: ${state.status}`);
    }
  }

  await browser.close();
  console.log('\n✅ Test complete');
}

main().catch(err => {
  console.error('\n❌ Fatal error:', err);
  process.exit(1);
});
