import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Load local .env first, then fall back to zoom-bot-service/.env for shared Zoom creds
dotenv.config();
dotenv.config({ path: path.resolve(__dirname, '..', 'zoom-bot-service', '.env') });

// Map zoom-bot-service credential names if RTMS-specific ones aren't set
if (!process.env.ZOOM_CLIENT_ID && process.env.ZOOM_API_KEY) {
  process.env.ZOOM_CLIENT_ID = process.env.ZOOM_API_KEY;
}
if (!process.env.ZOOM_CLIENT_SECRET && process.env.ZOOM_API_SECRET) {
  process.env.ZOOM_CLIENT_SECRET = process.env.ZOOM_API_SECRET;
}

const requiredVars = ['ZOOM_CLIENT_ID', 'ZOOM_CLIENT_SECRET'];

for (const key of requiredVars) {
  if (!process.env[key]) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
}

export const config = {
  port: process.env.PORT || 3000,

  mode: process.env.MODE || 'webhook',
  zoomWSURLForEvents: process.env.zoomWSURLForEvents || '',
  
  webhookPath: process.env.WEBHOOK_PATH || '/webhook',

  clientId: process.env.ZOOM_CLIENT_ID,
  clientSecret: process.env.ZOOM_CLIENT_SECRET,

  s2sClientId: process.env.ZOOM_S2S_CLIENT_ID || null,
  s2sClientSecret: process.env.ZOOM_S2S_CLIENT_SECRET || null,
  accountId: process.env.ZOOM_ACCOUNT_ID || null,

  zoomSecretToken: process.env.ZOOM_SECRET_TOKEN,
  frontendWssUrl: process.env.FRONTEND_WSS_URL_TO_CONNECT_TO,
};
