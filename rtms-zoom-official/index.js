import { RTMSManager } from './library/javascript/rtmsManager/RTMSManager.js';
import WebhookManager from './library/javascript/webhookManager/WebhookManager.js';
import WebsocketManager from './library/javascript/webSocketManager/WebsocketManager.js';
import express from 'express';
import http from 'http';
import path from 'path';
import { fileURLToPath } from 'url';
import ejs from 'ejs';
import dotenv from 'dotenv';
import { config } from './config.js';
import { setupFrontendWss, broadcastToFrontendClients, sharedServices } from './frontendWss.js';
import { textToSpeechBase64 } from './deepgramService.js';
import { chatWithOpenRouter } from './chatWithOpenrouter.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// S2S OAuth - Get access token to call Zoom APIs
async function getS2SAccessToken() {
  const credentials = Buffer.from(`${config.s2sClientId}:${config.s2sClientSecret}`).toString('base64');
  const response = await fetch(`https://zoom.us/oauth/token?grant_type=account_credentials&account_id=${config.accountId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Basic ${credentials}`,
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  });
  const data = await response.json();
  if (!data.access_token) {
    console.error('[S2S] Failed to get token:', data);
    return null;
  }
  return data.access_token;
}

// Start RTMS for a meeting via API
// Endpoint: PATCH /v2/live_meetings/{meetingId}/rtms_app/status
async function startRTMSForMeeting(meetingId, hostUserId) {
  if (!config.s2sClientId || !config.s2sClientSecret || !config.accountId) {
    console.log('[RTMS] S2S credentials not configured, skipping auto-start');
    return false;
  }

  try {
    const token = await getS2SAccessToken();
    if (!token) return false;

    console.log(`[RTMS] Starting RTMS for meeting ID: ${meetingId}`);

    // Use the correct RTMS API endpoint
    const response = await fetch(`https://api.zoom.us/v2/live_meetings/${meetingId}/rtms_app/status`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        action: 'start',
        settings: {
          participant_user_id: hostUserId,
          client_id: config.clientId
        }
      })
    });

    const responseText = await response.text();
    console.log(`[RTMS] Response status: ${response.status}, body: ${responseText}`);

    if (response.ok || response.status === 204) {
      console.log(`[RTMS] Successfully started RTMS for meeting: ${meetingId}`);
      return true;
    } else {
      console.error(`[RTMS] Failed to start RTMS:`, responseText);
      return false;
    }
  } catch (error) {
    console.error('[RTMS] Error starting RTMS:', error);
    return false;
  }
}

dotenv.config({ path: path.join(__dirname, '.env') });

const { MEDIA_PARAMS } = RTMSManager;

const rtmsConfig = {
  logging: 'info',
  logDir: path.join(__dirname, 'logs'),
  credentials: {
    meeting: {
      clientId: config.clientId,
      clientSecret: config.clientSecret,
      zoomSecretToken: config.zoomSecretToken,
    },
    websocket: {
      zoomWSURLForEvents: config.zoomWSURLForEvents,
      clientId: config.clientId,
      clientSecret: config.clientSecret,
    },
  },
  mediaParams: {
    audio: {
      contentType: MEDIA_PARAMS.MEDIA_CONTENT_TYPE_RTP,
      sampleRate: MEDIA_PARAMS.AUDIO_SAMPLE_RATE_SR_16K,
      channel: MEDIA_PARAMS.AUDIO_CHANNEL_MONO,
      codec: MEDIA_PARAMS.MEDIA_PAYLOAD_TYPE_L16,
      dataOpt: MEDIA_PARAMS.MEDIA_DATA_OPTION_AUDIO_MIXED_STREAM,
      sendRate: 100,
    },
    transcript: {
      contentType: MEDIA_PARAMS.MEDIA_CONTENT_TYPE_TEXT,
      language: MEDIA_PARAMS.LANGUAGE_ID_ENGLISH,
    },
  }
};

const app = express();
const server = http.createServer(app);

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'public'));
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

app.get('/', (req, res) => {
  res.render('index', { websocket_url: config.frontendWssUrl });
});

await RTMSManager.init(rtmsConfig);

if (config.mode === 'webhook') {
  const webhookManager = new WebhookManager({
    config: {
      webhookPath: config.webhookPath,
      zoomSecretToken: config.zoomSecretToken,
    },
    app: app
  });

  webhookManager.on('event', async (event, payload) => {
    console.log('[Consumer] Webhook Event:', event);

    // Auto-start RTMS when a meeting starts
    if (event === 'meeting.started') {
      const meetingId = payload?.object?.id;
      const hostUserId = payload?.object?.host_id;
      if (meetingId) {
        console.log(`[Consumer] Meeting started (ID: ${meetingId}, Host: ${hostUserId}), auto-starting RTMS`);
        await startRTMSForMeeting(meetingId, hostUserId);
      }
    }

    RTMSManager.handleEvent(event, payload);
  });

  webhookManager.setup();
  console.log('Webhook Manager initialized');
} else if (config.mode === 'websocket') {
  const websocketManager = new WebsocketManager({
    config: {
      zoomWSURLForEvents: config.zoomWSURLForEvents,
      clientId: config.clientId,
      clientSecret: config.clientSecret,
    }
  });

  websocketManager.on('event', (event, payload) => {
    console.log('[Consumer] WebSocket Event:', event);
    RTMSManager.handleEvent(event, payload);
  });

  await websocketManager.start();
  console.log('WebSocket Manager initialized');
}

sharedServices.textToSpeech = textToSpeechBase64;

setupFrontendWss(server);

RTMSManager.on('transcript', async ({ text, userId, userName, timestamp, meetingId, streamId, productType }) => {
  console.log('Transcript received:', text);
  
  try {
    const aiResponse = await chatWithOpenRouter(text);
    console.log('AI Response:', aiResponse);

    broadcastToFrontendClients({
      type: 'text',
      data: aiResponse,
      metadata: {
        source: 'transcript_response',
        originalText: text,
        userName: userName,
        timestamp: Date.now()
      }
    });

    if (sharedServices.textToSpeech) {
      const base64Audio = await sharedServices.textToSpeech(aiResponse);
      broadcastToFrontendClients({
        type: 'audio',
        data: base64Audio,
        metadata: {
          source: 'transcript_response',
          originalText: text,
          aiResponse: aiResponse,
          timestamp: Date.now()
        }
      });
    }
  } catch (error) {
    console.error('Error processing transcript:', error);
  }
});

RTMSManager.on('meeting.rtms_started', (payload) => {
  console.log(`RTMS started for meeting ${payload.meeting_uuid}`);
});

RTMSManager.on('meeting.rtms_stopped', (payload) => {
  console.log(`RTMS stopped for meeting ${payload.meeting_uuid}`);
});

await RTMSManager.start();

server.listen(config.port, () => {
  console.log(`Server running at http://localhost:${config.port}`);
  console.log(`Webhook available at http://localhost:${config.port}${config.webhookPath}`);
  console.log(`Frontend WebSocket available at ws://localhost:${config.port}/ws`);
});

process.on('SIGINT', async () => {
  console.log('Shutting down...');
  server.close();
  await RTMSManager.stop();
  process.exit(0);
});
