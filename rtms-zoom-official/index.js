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

// Track participants we've already DM'd (to avoid spamming)
const dmSentToParticipants = new Map(); // meetingId -> Set of userIds

// S2S OAuth - Get access token to call Zoom APIs
let cachedToken = null;
let tokenExpiry = 0;

async function getS2SAccessToken() {
  // Return cached token if still valid
  if (cachedToken && Date.now() < tokenExpiry) {
    return cachedToken;
  }

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

  cachedToken = data.access_token;
  tokenExpiry = Date.now() + (data.expires_in - 60) * 1000; // Refresh 1 min early
  return cachedToken;
}

// Send chat message to a live meeting
async function sendMeetingChatMessage(meetingId, message) {
  try {
    const token = await getS2SAccessToken();
    if (!token) {
      console.error('[Chat] No token available');
      return false;
    }

    // meetingId might be a UUID with special chars, need to encode
    const encodedMeetingId = encodeURIComponent(encodeURIComponent(meetingId));

    const response = await fetch(`https://api.zoom.us/v2/live_meetings/${encodedMeetingId}/chat/messages`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: message,
        to_channel: 'everyone' // Send to everyone in meeting
      })
    });

    if (response.ok) {
      console.log(`[Chat] Sent message to meeting ${meetingId}`);
      return true;
    } else {
      const errorText = await response.text();
      console.error(`[Chat] Failed to send message: ${response.status} ${errorText}`);
      return false;
    }
  } catch (error) {
    console.error('[Chat] Error sending message:', error);
    return false;
  }
}

// Get user email from Zoom API
async function getUserEmail(userId) {
  try {
    const token = await getS2SAccessToken();
    if (!token) return null;

    const response = await fetch(`https://api.zoom.us/v2/users/${userId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
      const data = await response.json();
      return data.email;
    }
    return null;
  } catch (error) {
    console.error('[User] Error getting user email:', error);
    return null;
  }
}

// DM a participant via the chatbot (through Python backend)
async function dmParticipantQuiz(meetingId, userId, userName) {
  // Check if we already DM'd this user in this meeting
  if (!dmSentToParticipants.has(meetingId)) {
    dmSentToParticipants.set(meetingId, new Set());
  }
  if (dmSentToParticipants.get(meetingId).has(userId)) {
    console.log(`[Quiz DM] Already sent to ${userName} (${userId})`);
    return;
  }

  console.log(`[Quiz DM] Sending quiz DM to ${userName} (${userId})`);

  // Get user's email to look up their JID
  const email = await getUserEmail(userId);
  if (!email) {
    console.log(`[Quiz DM] Could not get email for ${userName}`);
    return;
  }

  // Mark as sent
  dmSentToParticipants.get(meetingId).add(userId);

  // Call Python backend to send DM via chatbot
  const backendUrl = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';
  try {
    const response = await fetch(`${backendUrl}/api/quiz/dm-participant`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        meeting_id: meetingId,
        user_id: userId,
        user_name: userName,
        user_email: email
      })
    });

    if (response.ok) {
      console.log(`[Quiz DM] Successfully triggered DM to ${userName} (${email})`);
    } else {
      const error = await response.text();
      console.error(`[Quiz DM] Failed: ${error}`);
    }
  } catch (error) {
    console.error(`[Quiz DM] Error: ${error.message}`);
  }
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

// Accumulated transcript for HeyGen context
const meetingTranscripts = new Map(); // meetingId -> [{speaker, text, timestamp}]

// Enable CORS for all origins (needed for browser clients)
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
  res.header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }
  next();
});

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'public'));
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

app.get('/', (req, res) => {
  res.render('index', { websocket_url: config.frontendWssUrl });
});

// OAuth callback for Zoom app installation
app.get('/oauth/callback', (req, res) => {
  const { code, error } = req.query;

  if (error) {
    return res.status(400).send(`
      <html>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
          <h1>Installation Failed</h1>
          <p>Error: ${error}</p>
          <p>Please try again or contact support.</p>
        </body>
      </html>
    `);
  }

  if (code) {
    console.log('[OAuth] Zoom app installed successfully (auth code received)');
  }

  res.send(`
    <html>
      <body style="font-family: sans-serif; text-align: center; padding: 50px;">
        <h1>Quiz Bot Installed Successfully!</h1>
        <p>The quiz bot has been added to your Zoom account.</p>
        <p>You can now use <code>/quiz</code> in any Zoom Team Chat to start a quiz.</p>
        <p>You can close this window.</p>
      </body>
    </html>
  `);
});

// Zoom Team Chat Chatbot webhook - broadcasts to connected WebSocket clients
app.post('/webhook/zoom-chatbot', async (req, res) => {
  const payload = req.body;
  console.log('[Chatbot Webhook] Received:', JSON.stringify(payload).substring(0, 200));

  // Broadcast the chatbot event to all connected WebSocket clients
  // Local Python backend can listen for 'chatbot_webhook' type messages
  broadcastToFrontendClients({
    type: 'chatbot_webhook',
    data: payload,
    headers: {
      'x-zm-signature': req.headers['x-zm-signature'] || '',
      'x-zm-request-timestamp': req.headers['x-zm-request-timestamp'] || ''
    },
    timestamp: Date.now()
  });

  console.log('[Chatbot Webhook] Broadcasted to WebSocket clients');

  // Return success to Zoom immediately
  res.json({ success: true });
});

// API endpoint to get accumulated transcripts for a meeting
app.get('/api/transcripts/:meetingId', (req, res) => {
  const meetingId = req.params.meetingId;
  const transcripts = meetingTranscripts.get(meetingId) || [];
  res.json({
    meetingId,
    transcripts,
    count: transcripts.length,
    fullContext: transcripts.map(t => `${t.speaker}: ${t.text}`).join('\n')
  });
});

// API endpoint to get all active meetings with transcripts
app.get('/api/transcripts', (req, res) => {
  const meetings = [];
  for (const [meetingId, transcripts] of meetingTranscripts) {
    meetings.push({
      meetingId,
      transcriptCount: transcripts.length,
      lastUpdate: transcripts.length > 0 ? transcripts[transcripts.length - 1].timestamp : null
    });
  }
  res.json({ meetings });
});

// API endpoint to clear transcripts for a specific meeting or all
app.delete('/api/transcripts/:meetingId', (req, res) => {
  const meetingId = req.params.meetingId;
  if (meetingTranscripts.has(meetingId)) {
    meetingTranscripts.delete(meetingId);
    console.log(`[RTMS] Cleared transcripts for meeting: ${meetingId}`);
    res.json({ success: true, message: `Cleared transcripts for ${meetingId}` });
  } else {
    res.json({ success: false, message: 'Meeting not found' });
  }
});

// API endpoint to clear ALL transcripts
app.delete('/api/transcripts', (req, res) => {
  const count = meetingTranscripts.size;
  meetingTranscripts.clear();
  console.log(`[RTMS] Cleared all transcripts (${count} meetings)`);
  res.json({ success: true, message: `Cleared ${count} meetings` });
});

// API endpoint to trigger quiz DM to a specific user
// Called from Python backend's "Send Quiz to All" feature
app.post('/api/trigger-quiz-dm', async (req, res) => {
  const { meeting_id, user_name, user_id } = req.body;

  console.log(`[Quiz] Trigger DM for ${user_name} in meeting ${meeting_id}`);

  try {
    // Find user_id from transcripts if not provided
    let targetUserId = user_id;
    if (!targetUserId && meetingTranscripts.has(meeting_id)) {
      // Look through transcripts to find this user
      const transcripts = meetingTranscripts.get(meeting_id);
      for (const t of transcripts) {
        if (t.speaker === user_name && t.userId) {
          targetUserId = t.userId;
          break;
        }
      }
    }

    if (!targetUserId) {
      // Can't find user_id, try to DM via Python backend directly with email lookup
      const backendUrl = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/quiz/dm-by-name`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          meeting_id,
          user_name
        })
      });

      if (response.ok) {
        res.json({ success: true, message: `Quiz DM triggered for ${user_name}` });
      } else {
        res.json({ success: false, error: 'Could not find user' });
      }
      return;
    }

    // We have user_id, trigger the DM
    await dmParticipantQuiz(meeting_id, targetUserId, user_name);
    res.json({ success: true, message: `Quiz DM sent to ${user_name}` });

  } catch (error) {
    console.error(`[Quiz] Error triggering DM: ${error.message}`);
    res.status(500).json({ success: false, error: error.message });
  }
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
  console.log(`Transcript [${userName}]: ${text}`);

  // Auto-DM quiz to participants when they first speak
  if (userId && userName) {
    dmParticipantQuiz(meetingId, userId, userName);
  }

  // Accumulate transcript
  if (!meetingTranscripts.has(meetingId)) {
    meetingTranscripts.set(meetingId, []);
  }
  meetingTranscripts.get(meetingId).push({
    speaker: userName,
    userId: userId,
    text: text,
    timestamp: timestamp || Date.now()
  });

  // Forward to Python backend for HeyGen context
  const backendUrl = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';
  try {
    await fetch(`${backendUrl}/api/rtms/transcript`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        meeting_uuid: meetingId,
        speaker_name: userName,
        text: text,
        timestamp: timestamp
      })
    });
    console.log(`[RTMS] Forwarded transcript to backend`);
  } catch (error) {
    console.error('[RTMS] Failed to forward transcript to backend:', error.message);
  }

  // Broadcast to frontend WebSocket clients
  broadcastToFrontendClients({
    type: 'transcript',
    data: {
      speaker: userName,
      text: text,
      timestamp: timestamp || Date.now(),
      meetingId: meetingId
    }
  });
});

// Handle chat messages from meeting
RTMSManager.on('chat', async ({ text, userId, userName, timestamp, meetingId, streamId, productType }) => {
  console.log(`[Chat] [${userName}]: ${text}`);

  // Check for quiz command
  if (text.toLowerCase().includes('/quiz') || text.toLowerCase() === 'quiz') {
    console.log(`[Quiz] Quiz command received from ${userName} in meeting ${meetingId}`);

    // Send acknowledgment
    await sendMeetingChatMessage(meetingId, `Hi ${userName}! Starting quiz... 🎓`);

    // Forward to Python backend to generate quiz
    const backendUrl = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';
    try {
      const response = await fetch(`${backendUrl}/api/quiz/start-meeting-quiz`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          meeting_id: meetingId,
          user_name: userName,
          user_id: userId
        })
      });

      if (response.ok) {
        const quizData = await response.json();
        // Send first question to meeting chat
        if (quizData.question) {
          await sendMeetingChatMessage(meetingId, quizData.question);
        }
      } else {
        await sendMeetingChatMessage(meetingId, "Sorry, couldn't start quiz. Try again later.");
      }
    } catch (error) {
      console.error('[Quiz] Error starting quiz:', error);
      await sendMeetingChatMessage(meetingId, "Quiz service unavailable. Please try again.");
    }
  }

  // Check for quiz answers (A, B, C, D)
  const answerMatch = text.trim().toUpperCase().match(/^([ABCD])$/);
  if (answerMatch) {
    const answer = answerMatch[1];
    console.log(`[Quiz] Answer received from ${userName}: ${answer}`);

    // Forward to Python backend
    const backendUrl = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';
    try {
      const response = await fetch(`${backendUrl}/api/quiz/meeting-answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          meeting_id: meetingId,
          user_name: userName,
          user_id: userId,
          answer: answer
        })
      });

      if (response.ok) {
        const result = await response.json();
        if (result.message) {
          await sendMeetingChatMessage(meetingId, result.message);
        }
      }
    } catch (error) {
      console.error('[Quiz] Error processing answer:', error);
    }
  }

  // Broadcast to frontend
  broadcastToFrontendClients({
    type: 'chat',
    data: {
      speaker: userName,
      text: text,
      timestamp: timestamp || Date.now(),
      meetingId: meetingId
    }
  });
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
