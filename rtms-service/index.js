/**
 * RTMS Transcription Service
 * Receives live transcriptions from Zoom meetings and forwards to HeyGen avatars
 */
import express from 'express';
import http from 'http';
import { WebSocketServer } from 'ws';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

import { config } from './config.js';
import { WebhookManager } from './webhookManager.js';
import { RTMSClient, MEDIA_TYPES } from './library/RTMSClient.js';
import { HeyGenBridge } from './heygenBridge.js';
import { textToSpeechBase64 } from './deepgramService.js';
import fetch from 'node-fetch';

// Get Zoom access token
async function getZoomAccessToken() {
  const credentials = Buffer.from(`${config.clientId}:${config.clientSecret}`).toString('base64');
  const response = await fetch('https://zoom.us/oauth/token?grant_type=account_credentials&account_id=' + config.accountId, {
    method: 'POST',
    headers: {
      'Authorization': `Basic ${credentials}`,
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  });
  const data = await response.json();
  return data.access_token;
}

// Start RTMS for a meeting
async function startRTMS(meetingId) {
  try {
    const token = await getZoomAccessToken();
    console.log('[RTMS] Starting RTMS for meeting:', meetingId);

    const response = await fetch(`https://api.zoom.us/v2/meetings/${meetingId}/rtms/start`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (response.ok) {
      console.log('[RTMS] RTMS started successfully for meeting:', meetingId);
      return true;
    } else {
      const error = await response.text();
      console.error('[RTMS] Failed to start RTMS:', error);
      return false;
    }
  } catch (error) {
    console.error('[RTMS] Error starting RTMS:', error);
    return false;
  }
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config({ path: path.join(__dirname, '.env') });

// Initialize Express
const app = express();
const server = http.createServer(app);

// Initialize services
const heygenBridge = new HeyGenBridge(config.pythonBackendUrl);
const activeClients = new Map(); // meetingUuid -> RTMSClient
const frontendClients = new Set(); // WebSocket clients

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    activeSessions: activeClients.size,
    frontendClients: frontendClients.size
  });
});

// OAuth redirect handler (for Zoom app authorization)
app.get('/redirect', (req, res) => {
  const code = req.query.code;
  console.log('[OAuth] Authorization code received:', code);
  res.send(`
    <html>
      <body style="font-family: sans-serif; text-align: center; padding: 50px;">
        <h1>✅ Zoom App Authorized!</h1>
        <p>You can close this window and start a meeting.</p>
        <p style="color: gray; font-size: 12px;">Auth code: ${code ? code.substring(0, 10) + '...' : 'none'}</p>
      </body>
    </html>
  `);
});

// Stats endpoint
app.get('/stats', (req, res) => {
  const sessions = [];
  for (const [uuid, client] of activeClients) {
    sessions.push({
      meetingUuid: uuid,
      state: client.state,
      streamId: client.streamId
    });
  }
  res.json({
    activeSessions: sessions,
    frontendClients: frontendClients.size
  });
});

// Setup webhook handler
const webhookManager = new WebhookManager({
  config: {
    webhookPath: config.webhookPath,
    zoomSecretToken: config.zoomSecretToken
  },
  app: app
});

webhookManager.setup();

// Handle RTMS events
webhookManager.on('event', async (event, payload) => {
  console.log(`[Main] Received event: ${event}`);

  // When meeting starts, trigger RTMS
  if (event === 'meeting.started') {
    const meetingId = payload?.object?.id || payload?.object?.meeting_id;
    if (meetingId) {
      console.log(`[Main] Meeting started, triggering RTMS for: ${meetingId}`);
      await startRTMS(meetingId);
    }
  }

  // Handle RTMS started events
  if (event === 'meeting.rtms_started' ||
      event === 'webinar.rtms_started' ||
      event === 'session.rtms_started') {

    const meetingUuid = payload.meeting_uuid || payload.session_id;
    const streamId = payload.rtms_stream_id;
    const serverUrls = payload.server_urls;

    console.log(`[Main] RTMS started for ${meetingUuid}`);

    // Create RTMS client
    const client = new RTMSClient({
      meetingUuid,
      streamId,
      serverUrls,
      clientId: config.clientId,
      clientSecret: config.clientSecret,
      mediaTypes: MEDIA_TYPES.AUDIO | MEDIA_TYPES.TRANSCRIPT
    });

    // Set up event handlers
    client.on('connected', () => {
      console.log(`[Main] RTMS client connected for ${meetingUuid}`);
      heygenBridge.notifySessionStart(meetingUuid, streamId);
      broadcastToFrontend({ type: 'rtms_connected', meetingUuid });
    });

    client.on('transcript', async (data) => {
      console.log(`[Main] Transcript: ${data.userName}: ${data.text}`);

      // Forward to HeyGen backend
      await heygenBridge.forwardTranscript(
        meetingUuid,
        data.userName,
        data.text,
        data.timestamp
      );

      // Broadcast to frontend clients
      broadcastToFrontend({
        type: 'transcript',
        data: {
          meetingUuid,
          speaker: data.userName,
          text: data.text,
          timestamp: data.timestamp
        }
      });
    });

    client.on('audio', (data) => {
      // Audio data available if needed for Whisper processing
      // console.log(`[Main] Audio from ${data.userName}: ${data.data.length} bytes`);
    });

    client.on('error', (error) => {
      console.error(`[Main] RTMS client error for ${meetingUuid}:`, error);
      broadcastToFrontend({ type: 'rtms_error', meetingUuid, error: error.message });
    });

    client.on('disconnected', () => {
      console.log(`[Main] RTMS client disconnected for ${meetingUuid}`);
      activeClients.delete(meetingUuid);
      broadcastToFrontend({ type: 'rtms_disconnected', meetingUuid });
    });

    // Connect
    try {
      await client.connect();
      activeClients.set(meetingUuid, client);
    } catch (error) {
      console.error(`[Main] Failed to connect RTMS client:`, error);
    }
  }

  // Handle RTMS stopped events
  if (event === 'meeting.rtms_stopped' ||
      event === 'webinar.rtms_stopped' ||
      event === 'session.rtms_stopped') {

    const meetingUuid = payload.meeting_uuid || payload.session_id;
    console.log(`[Main] RTMS stopped for ${meetingUuid}`);

    const client = activeClients.get(meetingUuid);
    if (client) {
      client.disconnect();
      activeClients.delete(meetingUuid);
    }

    await heygenBridge.notifySessionStop(meetingUuid);
    broadcastToFrontend({ type: 'rtms_stopped', meetingUuid });
  }
});

// Frontend WebSocket server
const wss = new WebSocketServer({ server, path: '/ws' });

wss.on('connection', (ws, req) => {
  console.log('[WS] Frontend client connected');
  frontendClients.add(ws);

  ws.send(JSON.stringify({ type: 'connected' }));

  ws.on('message', async (raw) => {
    try {
      const message = JSON.parse(raw);
      console.log('[WS] Received:', message.type);

      // Handle client messages if needed
      switch (message.type) {
        case 'ping':
          ws.send(JSON.stringify({ type: 'pong' }));
          break;

        case 'get_sessions':
          const sessions = [];
          for (const [uuid, client] of activeClients) {
            sessions.push({ meetingUuid: uuid, state: client.state });
          }
          ws.send(JSON.stringify({ type: 'sessions', data: sessions }));
          break;
      }
    } catch (error) {
      console.error('[WS] Error handling message:', error);
    }
  });

  ws.on('close', () => {
    console.log('[WS] Frontend client disconnected');
    frontendClients.delete(ws);
  });

  ws.on('error', (error) => {
    console.error('[WS] WebSocket error:', error);
    frontendClients.delete(ws);
  });
});

// Broadcast to all frontend clients
function broadcastToFrontend(message) {
  const json = JSON.stringify(message);
  for (const client of frontendClients) {
    if (client.readyState === 1) { // OPEN
      client.send(json);
    }
  }
}

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n[Main] Shutting down...');

  // Disconnect all RTMS clients
  for (const [uuid, client] of activeClients) {
    console.log(`[Main] Disconnecting ${uuid}`);
    client.disconnect();
  }

  server.close();
  process.exit(0);
});

// Start server
server.listen(config.port, () => {
  console.log('=========================================');
  console.log('  RTMS Transcription Service Started');
  console.log('=========================================');
  console.log(`  Port: ${config.port}`);
  console.log(`  Webhook: http://localhost:${config.port}${config.webhookPath}`);
  console.log(`  WebSocket: ws://localhost:${config.port}/ws`);
  console.log(`  HeyGen Backend: ${config.pythonBackendUrl}`);
  console.log('');
  console.log('  Endpoints:');
  console.log(`    GET  /health    - Health check`);
  console.log(`    GET  /stats     - Active sessions`);
  console.log(`    POST ${config.webhookPath}  - Zoom webhooks`);
  console.log('');
  console.log('  Ready for RTMS events!');
  console.log('=========================================');
});
