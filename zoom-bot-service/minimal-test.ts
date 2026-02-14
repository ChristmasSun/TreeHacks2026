/**
 * Minimal test - just try to join a Zoom meeting
 */
import puppeteer from 'puppeteer';
import { generateJWT } from './src/utils/signature';
import * as dotenv from 'dotenv';

dotenv.config();

async function test() {
  console.log('Starting minimal Zoom bot test...');

  const SDK_KEY = process.env.ZOOM_SDK_KEY!;
  const SDK_SECRET = process.env.ZOOM_SDK_SECRET!;

  // First, let's create a test meeting using Zoom API
  console.log('\nStep 1: Creating test meeting via Zoom REST API...');

  const axios = require('axios');

  // We need a Zoom account token - but let's first just try with a manual meeting number
  const meetingNumber = process.argv[2];
  const passcode = process.argv[3] || '';

  if (!meetingNumber) {
    console.error('Usage: ts-node minimal-test.ts <meeting_number> [passcode]');
    console.error('Example: ts-node minimal-test.ts 1234567890 abc123');
    process.exit(1);
  }

  console.log(`\nStep 2: Generating signature for meeting ${meetingNumber}...`);
  const signature = generateJWT(SDK_KEY, SDK_SECRET, meetingNumber, 0);
  console.log('Signature generated:', signature.substring(0, 50) + '...');

  console.log('\nStep 3: Launching browser...');
  const browser = await puppeteer.launch({
    headless: false, // Show browser so we can see what's happening
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      '--no-sandbox',
      '--disable-setuid-sandbox'
    ]
  });

  const page = await browser.newPage();

  // Enable console logging from page
  page.on('console', (msg) => {
    console.log('[PAGE]', msg.text());
  });

  console.log('\nStep 4: Loading Zoom SDK page...');
  await page.goto('file://' + __dirname + '/public/zoom-bot.html');

  // Wait for SDK to load
  await page.waitForFunction(() => typeof (window as any).ZoomMtg !== 'undefined', { timeout: 10000 });
  console.log('Zoom SDK loaded');

  console.log('\nStep 5: Attempting to join meeting...');
  await page.evaluate((config) => {
    (window as any).joinMeeting({
      sdkKey: config.sdkKey,
      signature: config.signature,
      meetingNumber: config.meetingNumber,
      userName: 'Test Bot',
      password: config.passcode
    });
  }, {
    sdkKey: SDK_KEY,
    signature,
    meetingNumber,
    passcode
  });

  console.log('\nStep 6: Waiting for bot to join...');

  // Wait and check status
  for (let i = 0; i < 30; i++) {
    await new Promise(resolve => setTimeout(resolve, 1000));

    const botState = await page.evaluate(() => (window as any).botState);
    console.log(`[${i+1}s] Bot status: ${botState.status}`);

    if (botState.status === 'joined') {
      console.log('\n✅ SUCCESS! Bot joined the meeting!');
      console.log('Participant ID:', botState.participantId);
      break;
    }

    if (botState.status === 'error') {
      console.error('\n❌ ERROR:', botState.error);
      break;
    }
  }

  console.log('\nTest complete. Browser will stay open for 10 seconds...');
  await new Promise(resolve => setTimeout(resolve, 10000));

  await browser.close();
}

test().catch(console.error);
