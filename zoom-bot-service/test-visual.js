/**
 * Visual test - browser stays open so you can see what's happening
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
    console.error('Usage: node test-visual.js <meeting_number> [passcode]');
    process.exit(1);
  }

  const SDK_KEY = process.env.ZOOM_SDK_KEY;
  const SDK_SECRET = process.env.ZOOM_SDK_SECRET;

  console.log('\n🤖 Visual Zoom Bot Test');
  console.log('======================');
  console.log('Meeting:', meetingNumber);
  console.log('Passcode:', passcode || '(none)');
  console.log('');

  const signature = generateSDKSignature(SDK_KEY, SDK_SECRET, meetingNumber, 0);

  console.log('🚀 Launching browser (VISIBLE - watch for permission prompts!)...\n');
  const browser = await chromium.launch({
    headless: false,
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream']
  });

  const context = await browser.newContext({
    permissions: ['microphone', 'camera'],
    bypassCSP: true
  });

  const page = await context.newPage();

  // Log everything
  page.on('console', msg => console.log('[PAGE]', msg.text()));
  page.on('pageerror', err => console.error('[ERROR]', err.message));
  page.on('dialog', dialog => {
    console.log('[DIALOG]', dialog.message());
    dialog.accept().catch(() => {});
  });

  const htmlPath = 'file://' + path.join(__dirname, 'public', 'zoom-bot.html');
  await page.goto(htmlPath);

  console.log('⏳ Waiting for SDK...');
  await page.waitForFunction(() => typeof window.ZoomMtg !== 'undefined', { timeout: 15000 });
  console.log('✅ SDK loaded\n');

  console.log('🔗 Attempting to join...\n');
  await page.evaluate(({ sdkKey, signature, meetingNumber, passcode }) => {
    window.joinMeeting({
      sdkKey,
      signature,
      meetingNumber,
      userName: 'Visual Test Bot',
      password: passcode
    });
  }, { sdkKey: SDK_KEY, signature, meetingNumber, passcode });

  console.log('⏳ Monitoring status...');
  console.log('👀 WATCH THE BROWSER WINDOW for any permission prompts!');
  console.log('Press Ctrl+C to exit\n');

  // Monitor forever until user kills it
  let lastStatus = null;
  while (true) {
    try {
      await page.waitForTimeout(2000);
      const state = await page.evaluate(() => window.botState);

      if (state.status !== lastStatus) {
        console.log(`📊 Status changed: ${lastStatus} → ${state.status}`);
        lastStatus = state.status;

        if (state.status === 'joined') {
          console.log('\n🎉 🎉 🎉 SUCCESS! 🎉 🎉 🎉');
          console.log('Bot joined the meeting!');
          console.log('Participant ID:', state.participantId);
          console.log('\nBrowser will stay open. Press Ctrl+C to exit.');
        }

        if (state.status === 'error') {
          console.log('\n❌ ERROR:', state.error);
          console.log('\nBrowser will stay open. Press Ctrl+C to exit.');
        }
      }
    } catch (err) {
      console.error('Monitoring error:', err.message);
      break;
    }
  }
}

main().catch(err => {
  console.error('\n❌ Fatal error:', err);
  process.exit(1);
});
