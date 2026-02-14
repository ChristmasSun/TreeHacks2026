/**
 * Zoom Meeting Join via Web Browser (No SDK)
 * Joins as a guest user through the Zoom web client
 * 
 * Usage: node join-as-guest.js
 */

const { chromium } = require('playwright');

// Meeting details
const MEETING_ID = '89711545987';
const PASSCODE = '926454';
const USER_NAME = 'Test Bot';

async function main() {
  console.log('\n🤖 Zoom Web Client Join Test');
  console.log('='.repeat(40));
  console.log(`Meeting: ${MEETING_ID}`);
  console.log(`Passcode: ${PASSCODE}`);
  console.log(`Name: ${USER_NAME}`);
  console.log('');

  // Launch browser
  console.log('🚀 Launching browser...');
  const browser = await chromium.launch({
    headless: false,
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      '--autoplay-policy=no-user-gesture-required',
      '--disable-features=WebRtcHideLocalIpsWithMdns'
    ]
  });

  const context = await browser.newContext({
    permissions: ['microphone', 'camera'],
    viewport: { width: 1280, height: 800 },
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });

  const page = await context.newPage();

  // Enable verbose logging
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`[CONSOLE] ${msg.text()}`);
    }
  });

  try {
    // Go to Zoom join page
    const joinUrl = `https://zoom.us/wc/join/${MEETING_ID}`;
    console.log(`📄 Navigating to: ${joinUrl}`);
    await page.goto(joinUrl, { waitUntil: 'networkidle', timeout: 60000 });
    
    // Take screenshot for debugging
    await page.screenshot({ path: 'join-step1.png' });
    console.log('📸 Screenshot saved: join-step1.png');

    // Wait a bit for any redirects
    await page.waitForTimeout(3000);

    // Check current URL
    console.log(`📍 Current URL: ${page.url()}`);

    // Look for name input field
    console.log('🔍 Looking for name input...');
    
    // Try different selectors for name input
    const nameSelectors = [
      'input[name="name"]',
      'input#inputname',
      'input[placeholder*="name"]',
      'input[placeholder*="Name"]',
      '#join-confno + input',
      'input.preview-meeting-info-field-input'
    ];

    let nameInput = null;
    for (const selector of nameSelectors) {
      try {
        nameInput = await page.waitForSelector(selector, { timeout: 5000 });
        if (nameInput) {
          console.log(`✅ Found name input with selector: ${selector}`);
          break;
        }
      } catch (e) {
        // Try next selector
      }
    }

    if (nameInput) {
      await nameInput.fill(USER_NAME);
      console.log(`✅ Entered name: ${USER_NAME}`);
    } else {
      console.log('⚠️ Could not find name input, trying to proceed...');
    }

    // Take screenshot
    await page.screenshot({ path: 'join-step2.png' });
    console.log('📸 Screenshot saved: join-step2.png');

    // Look for passcode input if needed
    console.log('🔍 Looking for passcode input...');
    const passcodeSelectors = [
      'input[name="password"]',
      'input#inputpasscode',
      'input[placeholder*="passcode"]',
      'input[placeholder*="Passcode"]',
      'input[placeholder*="password"]',
      'input[type="password"]'
    ];

    for (const selector of passcodeSelectors) {
      try {
        const passcodeInput = await page.waitForSelector(selector, { timeout: 3000 });
        if (passcodeInput) {
          await passcodeInput.fill(PASSCODE);
          console.log(`✅ Entered passcode with selector: ${selector}`);
          break;
        }
      } catch (e) {
        // Try next selector
      }
    }

    // Take screenshot
    await page.screenshot({ path: 'join-step3.png' });
    console.log('📸 Screenshot saved: join-step3.png');

    // Look for join button
    console.log('🔍 Looking for join button...');
    const joinSelectors = [
      'button:has-text("Join")',
      'button[type="submit"]',
      '#joinBtn',
      '.zm-btn--primary',
      'button.btn-join',
      'input[type="submit"]'
    ];

    for (const selector of joinSelectors) {
      try {
        const joinBtn = await page.waitForSelector(selector, { timeout: 3000 });
        if (joinBtn) {
          console.log(`✅ Found join button: ${selector}`);
          await joinBtn.click();
          console.log('🔗 Clicked join button!');
          break;
        }
      } catch (e) {
        // Try next selector
      }
    }

    // Wait and take screenshot
    await page.waitForTimeout(5000);
    await page.screenshot({ path: 'join-step4.png' });
    console.log('📸 Screenshot saved: join-step4.png');

    // Check if we need to click "Join from Your Browser"
    console.log('🔍 Looking for "Join from Browser" link...');
    const browserJoinSelectors = [
      'a:has-text("Join from Your Browser")',
      'a:has-text("join from your browser")',
      'a:has-text("Join from your Browser")',
      '.webclient',
      'a[href*="wc/join"]',
      '#joinFromBrowser'
    ];

    for (const selector of browserJoinSelectors) {
      try {
        const browserLink = await page.waitForSelector(selector, { timeout: 5000 });
        if (browserLink) {
          console.log(`✅ Found browser join link: ${selector}`);
          await browserLink.click();
          console.log('🔗 Clicked "Join from Browser"!');
          break;
        }
      } catch (e) {
        // Try next selector
      }
    }

    // Wait for potential page changes
    await page.waitForTimeout(5000);
    await page.screenshot({ path: 'join-step5.png' });
    console.log('📸 Screenshot saved: join-step5.png');
    console.log(`📍 Current URL: ${page.url()}`);

    // Print page content for debugging
    const bodyText = await page.textContent('body');
    console.log('\n📋 Page content preview:');
    console.log(bodyText.substring(0, 500) + '...\n');

    // Keep browser open
    console.log('\n✅ Browser will stay open for 2 minutes for manual inspection...');
    console.log('   Check the screenshots and browser window.');
    await page.waitForTimeout(120000);

  } catch (error) {
    console.error('\n❌ Error:', error.message);
    await page.screenshot({ path: 'join-error.png' });
    console.log('📸 Error screenshot saved: join-error.png');
    
    // Keep open for debugging
    console.log('\nBrowser stays open for 30 seconds for debugging...');
    await page.waitForTimeout(30000);
  }

  await browser.close();
  console.log('\n🛑 Done.');
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
