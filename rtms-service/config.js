import dotenv from 'dotenv';
dotenv.config();

export const config = {
  port: process.env.PORT || 3002,
  mode: process.env.MODE || 'webhook',

  // Webhook configuration
  webhookPath: process.env.WEBHOOK_PATH || '/webhook',

  // Zoom credentials
  clientId: process.env.ZOOM_CLIENT_ID,
  clientSecret: process.env.ZOOM_CLIENT_SECRET,
  zoomSecretToken: process.env.ZOOM_SECRET_TOKEN,

  // WebSocket event delivery (alternative to webhooks)
  zoomWSURLForEvents: process.env.zoomWSURLForEvents || '',

  // Frontend WebSocket URL
  frontendWssUrl: process.env.FRONTEND_WSS_URL_TO_CONNECT_TO || 'ws://localhost:3002/ws',

  // Python backend for HeyGen integration
  pythonBackendUrl: process.env.PYTHON_BACKEND_URL || 'http://localhost:8000',

  // Deepgram TTS
  deepgramApiKey: process.env.DEEPGRAM_API_KEY,

  // OpenRouter/LLM
  openrouterApiKey: process.env.OPENROUTER_API_KEY,
  openrouterModel: process.env.OPENROUTER_MODEL || 'anthropic/claude-3-haiku',
};

// Validate required credentials
const requiredVars = ['ZOOM_CLIENT_ID', 'ZOOM_CLIENT_SECRET'];
for (const key of requiredVars) {
  if (!process.env[key]) {
    console.warn(`Warning: Missing environment variable: ${key}`);
  }
}
