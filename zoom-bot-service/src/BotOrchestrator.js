/**
 * Bot Orchestrator - Manages multiple HeyGen+Zoom bot instances
 * 
 * This service:
 * 1. Receives requests to deploy bots to breakout rooms
 * 2. Spawns Playwright browsers for each bot
 * 3. Each bot joins Zoom and shares HeyGen avatar screen
 * 4. Provides API to control avatars (make them speak)
 */

const { chromium } = require('playwright');
const https = require('https');
const http = require('http');
const EventEmitter = require('events');

class BotOrchestrator extends EventEmitter {
  constructor(options = {}) {
    super();
    this.heygenApiKey = options.heygenApiKey || process.env.HEYGEN_API_KEY;
    this.bots = new Map(); // botId -> BotInstance
    this.serverPort = options.serverPort || 9000;
    this.server = null;
  }

  /**
   * Deploy multiple bots to breakout rooms
   */
  async deployBots(config) {
    const {
      meetingId,
      passcode,
      rooms // Array of { roomId, roomName, studentName, botName }
    } = config;

    console.log(`\n🚀 Deploying ${rooms.length} bots to meeting ${meetingId}`);
    
    const results = {
      successful: [],
      failed: []
    };

    // Deploy bots in parallel (but with slight delay to avoid rate limits)
    const deployPromises = rooms.map((room, index) => {
      return new Promise(async (resolve) => {
        // Stagger deployments by 2 seconds each
        await this.delay(index * 2000);
        
        try {
          const bot = await this.createBot({
            botId: `bot_${room.roomId}`,
            meetingId,
            passcode,
            roomName: room.roomName,
            botName: room.botName || `AI Tutor - ${room.studentName}`,
            studentName: room.studentName,
            roomId: room.roomId
          });
          
          results.successful.push({
            roomId: room.roomId,
            botId: bot.id,
            status: 'deployed'
          });
          resolve();
        } catch (err) {
          console.error(`❌ Failed to deploy bot for room ${room.roomId}:`, err.message);
          results.failed.push({
            roomId: room.roomId,
            error: err.message
          });
          resolve();
        }
      });
    });

    await Promise.all(deployPromises);

    console.log(`\n✅ Deployment complete: ${results.successful.length} success, ${results.failed.length} failed`);
    return results;
  }

  /**
   * Create and start a single bot
   */
  async createBot(options) {
    const {
      botId,
      meetingId,
      passcode,
      roomName,
      botName,
      studentName,
      roomId
    } = options;

    console.log(`\n📦 Creating bot ${botId} for room: ${roomName}`);

    // Create HeyGen session
    console.log('   🎭 Creating HeyGen session...');
    const heygenSession = await this.createHeyGenSession();
    console.log(`   ✓ HeyGen session: ${heygenSession.session_id.substring(0, 15)}...`);

    // Start HeyGen session  
    await this.startHeyGenSession(heygenSession.session_id);
    console.log('   ✓ HeyGen session started');

    // Launch browser
    console.log('   🌐 Launching browser...');
    const browser = await chromium.launch({
      headless: false, // Set to true for production
      args: [
        '--use-fake-ui-for-media-stream',
        '--use-fake-device-for-media-stream',
        '--autoplay-policy=no-user-gesture-required',
        '--disable-infobars',
        '--no-first-run'
      ]
    });

    const context = await browser.newContext({
      permissions: ['microphone', 'camera'],
      viewport: { width: 1280, height: 720 }
    });

    // Create bot instance
    const bot = {
      id: botId,
      roomId,
      roomName,
      studentName,
      botName,
      meetingId,
      passcode,
      heygenSessionId: heygenSession.session_id,
      heygenUrl: heygenSession.url,
      heygenToken: heygenSession.access_token,
      browser,
      context,
      heygenPage: null,
      zoomPage: null,
      status: 'initializing',
      createdAt: new Date()
    };

    this.bots.set(botId, bot);

    // Start the bot flow
    await this.runBot(bot);

    return bot;
  }

  /**
   * Run the bot flow: open HeyGen, join Zoom, share screen
   */
  async runBot(bot) {
    try {
      // Step 1: Open HeyGen avatar page
      bot.status = 'connecting_heygen';
      bot.heygenPage = await bot.context.newPage();
      
      // Serve HeyGen page via local server
      const heygenPort = await this.serveBotPage(bot);
      await bot.heygenPage.goto(`http://localhost:${heygenPort}`, { waitUntil: 'domcontentloaded' });

      // Wait for avatar to connect
      console.log(`   ⏳ [${bot.id}] Waiting for avatar...`);
      try {
        await bot.heygenPage.waitForFunction(() => window.__avatarReady === true, { timeout: 45000 });
        console.log(`   ✓ [${bot.id}] Avatar connected`);
      } catch {
        console.log(`   ⚠️ [${bot.id}] Avatar timeout, continuing...`);
      }

      // Step 2: Open Zoom in new tab and join meeting
      bot.status = 'joining_zoom';
      bot.zoomPage = await bot.context.newPage();
      
      const zoomUrl = `https://zoom.us/wc/join/${bot.meetingId}`;
      console.log(`   🔗 [${bot.id}] Navigating to Zoom...`);
      await bot.zoomPage.goto(zoomUrl, { waitUntil: 'networkidle', timeout: 60000 });
      await this.delay(3000);

      // Fill name - try multiple selectors
      console.log(`   🔍 [${bot.id}] Looking for name input...`);
      const nameSelectors = [
        '#input-for-name',
        'input[id="input-for-name"]',
        'input[name="name"]',
        'input#inputname',
        'input[placeholder*="name" i]'
      ];
      
      let nameFound = false;
      for (const selector of nameSelectors) {
        try {
          const nameInput = await bot.zoomPage.waitForSelector(selector, { timeout: 3000 });
          if (nameInput) {
            await nameInput.fill(bot.botName);
            console.log(`   ✓ [${bot.id}] Name entered: ${bot.botName}`);
            nameFound = true;
            break;
          }
        } catch {}
      }
      if (!nameFound) {
        console.log(`   ⚠️ [${bot.id}] Name input not found`);
      }

      // Fill passcode - try multiple selectors
      console.log(`   🔍 [${bot.id}] Looking for passcode input...`);
      const passcodeSelectors = [
        '#input-for-pwd',
        'input[id="input-for-pwd"]',
        'input[name="password"]',
        'input#inputpasscode',
        'input[placeholder*="passcode" i]',
        'input[type="password"]'
      ];
      
      let passcodeFound = false;
      for (const selector of passcodeSelectors) {
        try {
          const pwdInput = await bot.zoomPage.waitForSelector(selector, { timeout: 3000 });
          if (pwdInput) {
            await pwdInput.fill(bot.passcode);
            console.log(`   ✓ [${bot.id}] Passcode entered`);
            passcodeFound = true;
            break;
          }
        } catch {}
      }
      if (!passcodeFound) {
        console.log(`   ⚠️ [${bot.id}] Passcode input not found`);
      }

      // Wait a moment for form validation
      await this.delay(1000);

      // Click join button - wait for it to be enabled
      console.log(`   🔍 [${bot.id}] Looking for join button...`);
      
      let joinClicked = false;
      try {
        // Wait for join button to exist and not be disabled
        await bot.zoomPage.waitForSelector('button.preview-join-button:not(.zm-btn--disabled)', { timeout: 10000 });
        const joinBtn = await bot.zoomPage.$('button.preview-join-button');
        if (joinBtn) {
          await joinBtn.click();
          console.log(`   ✓ [${bot.id}] Clicked Join button`);
          joinClicked = true;
        }
      } catch {}
      
      // Fallback: try other selectors
      if (!joinClicked) {
        const joinSelectors = [
          'button:has-text("Join"):not(.disabled)',
          'button[type="button"]:has-text("Join")',
          '#joinBtn'
        ];
        for (const selector of joinSelectors) {
          try {
            const joinBtn = await bot.zoomPage.waitForSelector(selector, { timeout: 3000 });
            if (joinBtn) {
              await joinBtn.click();
              console.log(`   ✓ [${bot.id}] Clicked Join button (fallback)`);
              joinClicked = true;
              break;
            }
          } catch {}
        }
      }
      
      if (!joinClicked) {
        console.log(`   ⚠️ [${bot.id}] Join button not found or still disabled`);
      }

      await this.delay(5000);

      // Check for "Join from Browser" link (appears after first join click)
      console.log(`   🔍 [${bot.id}] Looking for "Join from Browser" link...`);
      const browserSelectors = [
        'a:has-text("Join from Your Browser")',
        'a:has-text("join from your browser")',
        'a:has-text("Join from your Browser")',
        '.webclient',
        'a[href*="wc/join"]'
      ];
      
      for (const selector of browserSelectors) {
        try {
          const browserLink = await bot.zoomPage.waitForSelector(selector, { timeout: 5000 });
          if (browserLink) {
            await browserLink.click();
            console.log(`   ✓ [${bot.id}] Clicked "Join from Browser"`);
            await this.delay(5000);
            break;
          }
        } catch {}
      }

      // Handle any additional prompts (agree to terms, etc)
      try {
        const agreeBtn = await bot.zoomPage.waitForSelector('button:has-text("I Agree"), button:has-text("Agree")', { timeout: 3000 });
        if (agreeBtn) {
          await agreeBtn.click();
          console.log(`   ✓ [${bot.id}] Agreed to terms`);
        }
      } catch {}

      await this.delay(3000);

      bot.status = 'in_meeting';
      console.log(`   ✅ [${bot.id}] Bot in meeting - ready to share screen`);

      // Step 3: Prompt for screen share (manual or automated)
      // Note: Automated screen share requires user interaction typically
      // But we'll set it up so the HeyGen tab is ready to be shared

      this.emit('bot_ready', {
        botId: bot.id,
        roomId: bot.roomId,
        status: 'ready'
      });

    } catch (err) {
      console.error(`   ❌ [${bot.id}] Error:`, err.message);
      bot.status = 'error';
      bot.error = err.message;
      this.emit('bot_error', { botId: bot.id, error: err.message });
    }
  }

  /**
   * Make a bot's avatar speak
   */
  async speakText(botId, text) {
    const bot = this.bots.get(botId);
    if (!bot) {
      throw new Error(`Bot ${botId} not found`);
    }

    console.log(`🗣️ [${botId}] Speaking: "${text.substring(0, 50)}..."`);

    return new Promise((resolve, reject) => {
      const body = JSON.stringify({
        session_id: bot.heygenSessionId,
        text,
        task_type: 'talk'
      });

      const req = https.request({
        hostname: 'api.heygen.com',
        path: '/v1/streaming.task',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': this.heygenApiKey,
          'Content-Length': body.length
        }
      }, res => {
        let result = '';
        res.on('data', c => result += c);
        res.on('end', () => {
          try {
            const j = JSON.parse(result);
            resolve(j);
          } catch {
            reject(new Error(result));
          }
        });
      });

      req.on('error', reject);
      req.write(body);
      req.end();
    });
  }

  /**
   * Remove a bot
   */
  async removeBot(botId) {
    const bot = this.bots.get(botId);
    if (!bot) return;

    console.log(`🗑️ Removing bot ${botId}...`);

    // Close HeyGen session
    try {
      await this.stopHeyGenSession(bot.heygenSessionId);
    } catch {}

    // Close browser
    try {
      await bot.browser.close();
    } catch {}

    this.bots.delete(botId);
    console.log(`   ✓ Bot ${botId} removed`);
  }

  /**
   * Remove all bots
   */
  async removeAllBots() {
    const botIds = Array.from(this.bots.keys());
    for (const botId of botIds) {
      await this.removeBot(botId);
    }
  }

  /**
   * Get bot status
   */
  getBotStatus(botId) {
    const bot = this.bots.get(botId);
    if (!bot) return null;

    return {
      id: bot.id,
      roomId: bot.roomId,
      roomName: bot.roomName,
      studentName: bot.studentName,
      status: bot.status,
      createdAt: bot.createdAt,
      error: bot.error
    };
  }

  /**
   * Get all bots status
   */
  getAllBotsStatus() {
    return Array.from(this.bots.values()).map(bot => this.getBotStatus(bot.id));
  }

  // ======== HeyGen API Helpers ========

  async createHeyGenSession() {
    return this.heygenRequest('/streaming.new', {
      quality: 'medium',
      video_encoding: 'VP8',
      version: 'v2',
      disable_idle_timeout: true
    });
  }

  async startHeyGenSession(sessionId) {
    return this.heygenRequest('/streaming.start', { session_id: sessionId });
  }

  async stopHeyGenSession(sessionId) {
    return this.heygenRequest('/streaming.stop', { session_id: sessionId });
  }

  heygenRequest(endpoint, data) {
    return new Promise((resolve, reject) => {
      const body = JSON.stringify(data);
      const req = https.request({
        hostname: 'api.heygen.com',
        path: '/v1' + endpoint,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': this.heygenApiKey,
          'Content-Length': body.length
        }
      }, res => {
        let result = '';
        res.on('data', c => result += c);
        res.on('end', () => {
          try {
            const j = JSON.parse(result);
            if (j.error) reject(new Error(JSON.stringify(j.error)));
            else resolve(j.data || j);
          } catch { reject(new Error(result)); }
        });
      });
      req.on('error', reject);
      req.write(body);
      req.end();
    });
  }

  // ======== Server for Bot Pages ========

  async serveBotPage(bot) {
    // Find available port
    const port = 10000 + Math.floor(Math.random() * 5000);
    
    const server = http.createServer((req, res) => {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(this.createBotPageHTML(bot));
    });

    await new Promise(r => server.listen(port, r));
    bot.pageServer = server;
    bot.pagePort = port;
    
    return port;
  }

  createBotPageHTML(bot) {
    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>HeyGen Avatar - ${bot.roomName}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      display: flex;
      flex-direction: column;
      height: 100vh;
      font-family: system-ui;
    }
    #header {
      padding: 10px 15px;
      background: rgba(0,0,0,0.5);
      color: white;
      font-size: 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    #header .room { color: #00d9ff; font-weight: 600; }
    #header .student { color: #ff6b6b; }
    #header .status { 
      padding: 3px 10px; 
      border-radius: 10px; 
      font-size: 12px;
      background: #0a4d32;
    }
    #videoContainer {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    #avatarVideo {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
    }
  </style>
</head>
<body>
  <div id="header">
    <span>
      <span class="room">${bot.roomName}</span> • 
      <span class="student">Student: ${bot.studentName}</span>
    </span>
    <span id="status" class="status">Connecting...</span>
  </div>
  <div id="videoContainer">
    <video id="avatarVideo" autoplay playsinline></video>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
  <script>
    window.__avatarReady = false;
    
    const LK_URL = '${bot.heygenUrl}';
    const LK_TOKEN = '${bot.heygenToken}';
    
    const statusEl = document.getElementById('status');
    const avatarVideo = document.getElementById('avatarVideo');
    
    async function connect() {
      try {
        const room = new LivekitClient.Room();
        
        room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, pub, participant) => {
          console.log('[HeyGen] Track:', track.kind);
          if (track.kind === 'video') {
            track.attach(avatarVideo);
            window.__avatarReady = true;
            statusEl.textContent = '✓ Avatar Ready';
            statusEl.style.background = '#0a4d32';
          }
          if (track.kind === 'audio') {
            const audio = track.attach();
            audio.volume = 0.7;
          }
        });
        
        room.on(LivekitClient.RoomEvent.Disconnected, () => {
          statusEl.textContent = 'Disconnected';
          statusEl.style.background = '#4d1a1a';
        });
        
        statusEl.textContent = 'Connecting...';
        await room.connect(LK_URL, LK_TOKEN);
        statusEl.textContent = 'Waiting for avatar...';
        
      } catch (err) {
        statusEl.textContent = 'Error: ' + err.message;
        statusEl.style.background = '#4d1a1a';
      }
    }
    
    connect();
  </script>
</body>
</html>`;
  }

  // ======== Utility ========

  delay(ms) {
    return new Promise(r => setTimeout(r, ms));
  }
}

module.exports = { BotOrchestrator };
