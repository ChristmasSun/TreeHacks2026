/**
 * Bot Service API Server
 * 
 * REST API for controlling HeyGen+Zoom bots
 * 
 * Endpoints:
 *   POST /deploy       - Deploy bots to breakout rooms
 *   POST /speak        - Make a bot speak
 *   DELETE /bot/:id    - Remove a specific bot
 *   DELETE /bots       - Remove all bots
 *   GET /status        - Get all bots status
 *   GET /status/:id    - Get specific bot status
 *   GET /health        - Health check
 */

const express = require('express');
const cors = require('cors');
const { BotOrchestrator } = require('./BotOrchestrator');
require('dotenv').config();

const app = express();
const PORT = process.env.BOT_SERVICE_PORT || 3002;

// Middleware
app.use(cors());
app.use(express.json());

// Create orchestrator
const orchestrator = new BotOrchestrator({
  heygenApiKey: process.env.HEYGEN_API_KEY
});

// Event logging
orchestrator.on('bot_ready', (data) => {
  console.log(`📣 Event: Bot ${data.botId} ready`);
});

orchestrator.on('bot_error', (data) => {
  console.error(`📣 Event: Bot ${data.botId} error: ${data.error}`);
});

// ======== API Endpoints ========

/**
 * Health check
 */
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    service: 'bot-orchestrator',
    activeBots: orchestrator.bots.size,
    timestamp: new Date().toISOString()
  });
});

/**
 * Deploy bots to breakout rooms
 * 
 * Body: {
 *   meetingId: string,
 *   passcode: string,
 *   rooms: [{ roomId, roomName, studentName, botName? }]
 * }
 */
app.post('/deploy', async (req, res) => {
  try {
    const { meetingId, passcode, rooms } = req.body;

    if (!meetingId || !rooms || !Array.isArray(rooms)) {
      return res.status(400).json({ 
        error: 'Missing required fields: meetingId, rooms' 
      });
    }

    console.log(`\n📥 Deploy request: ${rooms.length} bots to meeting ${meetingId}`);

    const result = await orchestrator.deployBots({
      meetingId,
      passcode: passcode || '',
      rooms
    });

    res.json({
      success: true,
      deployed: result.successful.length,
      failed: result.failed.length,
      results: result
    });

  } catch (err) {
    console.error('Deploy error:', err);
    res.status(500).json({ error: err.message });
  }
});

/**
 * Make a bot speak
 * 
 * Body: { botId, text }
 */
app.post('/speak', async (req, res) => {
  try {
    const { botId, text } = req.body;

    if (!botId || !text) {
      return res.status(400).json({ 
        error: 'Missing required fields: botId, text' 
      });
    }

    const result = await orchestrator.speakText(botId, text);
    res.json({ success: true, result });

  } catch (err) {
    console.error('Speak error:', err);
    res.status(500).json({ error: err.message });
  }
});

/**
 * Get all bots status
 */
app.get('/status', (req, res) => {
  const bots = orchestrator.getAllBotsStatus();
  res.json({ 
    count: bots.length, 
    bots 
  });
});

/**
 * Get specific bot status
 */
app.get('/status/:botId', (req, res) => {
  const bot = orchestrator.getBotStatus(req.params.botId);
  if (!bot) {
    return res.status(404).json({ error: 'Bot not found' });
  }
  res.json(bot);
});

/**
 * Remove a specific bot
 */
app.delete('/bot/:botId', async (req, res) => {
  try {
    await orchestrator.removeBot(req.params.botId);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * Remove all bots
 */
app.delete('/bots', async (req, res) => {
  try {
    await orchestrator.removeAllBots();
    res.json({ success: true, message: 'All bots removed' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ======== Start Server ========

app.listen(PORT, () => {
  console.log(`\n🤖 Bot Orchestrator Service`);
  console.log(`═════════════════════════════════`);
  console.log(`   Port: ${PORT}`);
  console.log(`   HeyGen Key: ${process.env.HEYGEN_API_KEY ? '✓ Set' : '✗ Missing'}`);
  console.log(`═════════════════════════════════`);
  console.log(`\nEndpoints:`);
  console.log(`   POST   /deploy     - Deploy bots to meeting`);
  console.log(`   POST   /speak      - Make bot speak`);
  console.log(`   GET    /status     - Get all bots status`);
  console.log(`   GET    /status/:id - Get bot status`);
  console.log(`   DELETE /bot/:id    - Remove bot`);
  console.log(`   DELETE /bots       - Remove all bots`);
  console.log(`   GET    /health     - Health check`);
  console.log(`\nReady for requests...\n`);
});

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n\n🛑 Shutting down...');
  await orchestrator.removeAllBots();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  await orchestrator.removeAllBots();
  process.exit(0);
});
