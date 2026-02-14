/**
 * Zoom Bot Service - Main Entry Point
 */
import dotenv from 'dotenv';
import { BotManager } from './BotManager';
import { createServer } from './server';

// Load environment variables
dotenv.config();

// Validate environment
function validateEnv() {
  const required = ['ZOOM_SDK_KEY', 'ZOOM_SDK_SECRET'];
  const missing = required.filter(key => !process.env[key]);

  if (missing.length > 0) {
    console.error('❌ Missing required environment variables:', missing.join(', '));
    console.error('Please check your .env file');
    process.exit(1);
  }

  console.log('✓ Environment variables validated');
}

async function main() {
  console.log('🤖 Zoom Bot Service Starting...');
  console.log('=====================================');

  // Validate environment
  validateEnv();

  // Initialize bot manager
  const botManager = new BotManager();

  // Set up bot manager event listeners
  botManager.on('bot-status-change', ({ botId, status }) => {
    console.log(`[Event] Bot ${botId} status: ${status}`);
  });

  botManager.on('bot-joined', (botId) => {
    console.log(`[Event] Bot ${botId} joined meeting`);
  });

  botManager.on('bot-error', ({ botId, error }) => {
    console.error(`[Event] Bot ${botId} error: ${error}`);
  });

  botManager.on('audio-chunk', ({ botId, roomId, audioData }) => {
    // TODO: Forward audio to Python backend
    console.log(`[Event] Audio from bot ${botId}, room ${roomId}: ${audioData.length} bytes`);
  });

  // Create HTTP server
  const app = createServer(botManager);

  // Start server
  const PORT = parseInt(process.env.PORT || '3001');

  app.listen(PORT, () => {
    console.log('=====================================');
    console.log(`✓ Zoom Bot Service running on port ${PORT}`);
    console.log(`✓ Python backend URL: ${process.env.PYTHON_BACKEND_URL || 'http://localhost:8000'}`);
    console.log('');
    console.log('API Endpoints:');
    console.log(`  GET  http://localhost:${PORT}/health`);
    console.log(`  POST http://localhost:${PORT}/bots/create`);
    console.log(`  GET  http://localhost:${PORT}/bots`);
    console.log(`  GET  http://localhost:${PORT}/stats`);
    console.log('');
    console.log('Ready to receive bot creation requests!');
    console.log('=====================================');
  });

  // Graceful shutdown
  process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down gracefully...');

    try {
      await botManager.removeAllBots();
      console.log('✓ All bots removed');
      process.exit(0);
    } catch (error) {
      console.error('Error during shutdown:', error);
      process.exit(1);
    }
  });
}

// Run
main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
