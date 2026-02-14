/**
 * Test with Playwright instead of Puppeteer
 */
const { chromium } = require('playwright');
const crypto = require('crypto');
const path = require('path');
require('dotenv').config();

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

async function main() {
  const meetingNumber = process.argv[2];
  const passcode = process.argv[3] || '';

  if (!meetingNumber) {
    console.error('Usage: node test-playwright.js <meeting_number> [passcode]');
    process.exit(1);
  }

  const SDK_KEY = process.env.ZOOM_SDK_KEY;
  const SDK_SECRET = process.env.ZOOM_SDK_SECRET;

  console.log('\n🤖 Zoom Bot Test (Playwright)');
  console.log('===========================');
  console.log('Meeting:', meetingNumber);
  console.log('Passcode:', passcode || '(none)');
  console.log('');

  console.log('📝 Generating signature...');
  const signature = generateSDKSignature(SDK_KEY, SDK_SECRET, meetingNumber, 0);
  console.log('✅ Signature:', signature.substring(0, 30) + '...\n');

  console.log('🚀 Launching browser...');
  const browser = await chromium.launch({
    headless: false,
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream'
    ]
  });

  const context = await browser.newContext({
    permissions: ['microphone', 'camera']
  });

  const page = await context.newPage();

  // Log console messages
  page.on('console', async msg => {
    const text = msg.text();
    const type = msg.type();

    if (type === 'error' || type === 'warning') {
      console.log(`[PAGE ${type.toUpperCase()}]`, text);
      // Try to get more details
      const args = await Promise.all(msg.args().map(arg => arg.jsonValue().catch(() => arg.toString())));
      if (args.length > 0) {
        console.log('[DETAILS]', args);
      }
    } else {
      console.log('[PAGE]', text);
    }
  });

  // Log errors
  page.on('pageerror', err => {
    console.error('[PAGE ERROR]', err.message);
    console.error('[STACK]', err.stack);
  });

  // Log network failures
  page.on('requestfailed', request => {
    console.error('[NETWORK FAIL]', request.url(), request.failure().errorText);
  });

  const htmlPath = 'http://localhost:3001/zoom-bot.html';
  console.log('📄 Loading:', htmlPath);
  await page.goto(htmlPath);

  console.log('⏳ Waiting for Zoom SDK...');
  await page.waitForFunction(() => typeof window.ZoomMtg !== 'undefined', { timeout: 15000 });
  console.log('✅ SDK loaded\n');

  console.log('🔗 Joining meeting...\n');
  await page.evaluate(({ sdkKey, signature, meetingNumber, passcode }) => {
    window.joinMeeting({
      sdkKey,
      signature,
      meetingNumber,
      userName: 'Playwright Test Bot',
      password: passcode
    });
  }, { sdkKey: SDK_KEY, signature, meetingNumber, passcode });

  console.log('⏳ Waiting for result (60 seconds max)...\n');

  for (let i = 0; i < 60; i++) {
    await page.waitForTimeout(1000);

    const state = await page.evaluate(() => window.botState);

    if (state.status === 'joined') {
      console.log('\n🎉 SUCCESS! Bot joined!');
      console.log('Participant ID:', state.participantId);
      console.log('\nBrowser stays open for 30 seconds...');
      await page.waitForTimeout(30000);
      break;
    }

    if (state.status === 'error') {
      console.log('\n❌ ERROR:', state.error);
      console.log('\nBrowser stays open for 60 seconds...');
      await page.waitForTimeout(60000);
      break;
    }

    if (i % 5 === 0) {
      console.log(`  [${i}s] Status: ${state.status}`);
    }
  }

  await browser.close();
  console.log('\nTest complete');
}

main().catch(err => {
  console.error('\n❌ Fatal error:', err);
  process.exit(1);
});
