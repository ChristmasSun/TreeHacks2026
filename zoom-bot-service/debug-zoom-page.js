/**
 * Debug script to see Zoom page structure
 */
const { chromium } = require('playwright');
require('dotenv').config();

const MEETING_ID = process.env.ZOOM_MEETING_ID || '83565992668';

async function main() {
  console.log('🔍 Debugging Zoom page structure...\n');

  const browser = await chromium.launch({
    headless: false,
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream']
  });

  const context = await browser.newContext({
    permissions: ['microphone', 'camera'],
    viewport: { width: 1280, height: 800 }
  });

  const page = await context.newPage();

  const zoomUrl = `https://zoom.us/wc/join/${MEETING_ID}`;
  console.log(`📄 Navigating to: ${zoomUrl}`);
  await page.goto(zoomUrl, { waitUntil: 'networkidle', timeout: 60000 });

  await page.waitForTimeout(5000);

  // Take screenshot
  await page.screenshot({ path: 'debug-zoom.png', fullPage: true });
  console.log('📸 Screenshot saved: debug-zoom.png');

  // Get all input elements
  console.log('\n📋 All INPUT elements on page:');
  const inputs = await page.$$eval('input', els => 
    els.map(el => ({
      id: el.id,
      name: el.name,
      type: el.type,
      placeholder: el.placeholder,
      className: el.className,
      value: el.value
    }))
  );
  console.log(JSON.stringify(inputs, null, 2));

  // Get all button elements
  console.log('\n📋 All BUTTON elements on page:');
  const buttons = await page.$$eval('button', els =>
    els.map(el => ({
      id: el.id,
      text: el.innerText.substring(0, 50),
      className: el.className,
      type: el.type
    }))
  );
  console.log(JSON.stringify(buttons, null, 2));

  // Get page title and URL
  console.log('\n📍 Current URL:', page.url());
  console.log('📍 Page title:', await page.title());

  // Get body text preview
  const bodyText = await page.textContent('body');
  console.log('\n📋 Page text preview:');
  console.log(bodyText.substring(0, 1000));

  console.log('\n⏳ Browser staying open for inspection... (60s)');
  await page.waitForTimeout(60000);

  await browser.close();
}

main().catch(console.error);
