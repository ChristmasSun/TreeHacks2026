/**
 * HeyGen Avatar Bot with Zoom Meeting Context
 *
 * This bot:
 * 1. Connects to HeyGen avatar via LiveKit
 * 2. Fetches live transcript context from RTMS service
 * 3. Uses Cerebras to generate contextual responses
 * 4. Avatar speaks the responses
 */
const { chromium } = require('playwright');
const https = require('https');
const http = require('http');
require('dotenv').config();

// Config
const HEYGEN_API_KEY = process.env.HEYGEN_API_KEY;
const CEREBRAS_API_KEY = process.env.CEREBRAS_API_KEY;
const MEETING_ID = process.env.ZOOM_MEETING_ID;
const PASSCODE = process.env.ZOOM_PASSCODE;
const BOT_NAME = process.env.BOT_NAME || 'AI Professor';

// RTMS transcript service URL (Render deployment)
const RTMS_SERVICE_URL = process.env.RTMS_SERVICE_URL || 'https://rtms-webhook.onrender.com';

// Fetch meeting transcript context from RTMS service
async function fetchTranscriptContext(meetingId) {
  return new Promise((resolve, reject) => {
    const url = new URL(`/api/transcripts/${meetingId}`, RTMS_SERVICE_URL);

    const protocol = url.protocol === 'https:' ? https : http;

    protocol.get(url.href, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          resolve(json);
        } catch (e) {
          resolve({ transcripts: [], fullContext: '' });
        }
      });
    }).on('error', () => {
      resolve({ transcripts: [], fullContext: '' });
    });
  });
}

// Get all active meetings with transcripts
async function getActiveMeetings() {
  return new Promise((resolve, reject) => {
    const url = new URL('/api/transcripts', RTMS_SERVICE_URL);
    const protocol = url.protocol === 'https:' ? https : http;

    protocol.get(url.href, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          resolve({ meetings: [] });
        }
      });
    }).on('error', () => {
      resolve({ meetings: [] });
    });
  });
}

// Generate response using Cerebras
async function generateResponse(userMessage, transcriptContext) {
  if (!CEREBRAS_API_KEY) {
    console.log('   [Cerebras] No API key, using echo response');
    return `I heard: ${userMessage}`;
  }

  const systemPrompt = `You are an AI Professor assistant in a Zoom meeting. You have access to the live meeting transcript and can provide contextual, helpful responses.

Here is the current meeting transcript:
${transcriptContext || 'No transcript available yet.'}

Respond naturally and helpfully to the student's question. Keep responses concise (2-3 sentences max) since they will be spoken aloud.`;

  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      model: 'llama-3.3-70b',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userMessage }
      ],
      max_tokens: 150
    });

    const req = https.request({
      hostname: 'api.cerebras.ai',
      path: '/v1/chat/completions',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${CEREBRAS_API_KEY}`,
        'Content-Length': Buffer.byteLength(body)
      }
    }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          const response = json.choices?.[0]?.message?.content || 'I apologize, I could not generate a response.';
          resolve(response);
        } catch (e) {
          resolve('I apologize, there was an error processing your request.');
        }
      });
    });
    req.on('error', () => resolve('I apologize, I could not connect to the AI service.'));
    req.write(body);
    req.end();
  });
}

// Create HeyGen session
async function createHeyGenSession() {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      quality: 'medium',
      avatar_name: 'Angela-inblackskirt-20220820',
      voice: { voice_id: '1bd001e7e50f421d891986aad5158bc8' },
      version: 'v2',
      video_encoding: 'H264'
    });

    const req = https.request({
      hostname: 'api.heygen.com',
      path: '/v1/streaming.new',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': HEYGEN_API_KEY,
        'Content-Length': body.length
      }
    }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          const j = JSON.parse(data);
          if (j.data) resolve(j.data);
          else reject(new Error(JSON.stringify(j)));
        } catch (e) { reject(e); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// Start HeyGen session
async function startHeyGenSession(sessionId) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ session_id: sessionId });
    const req = https.request({
      hostname: 'api.heygen.com',
      path: '/v1/streaming.start',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': HEYGEN_API_KEY,
        'Content-Length': body.length
      }
    }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => resolve(JSON.parse(data)));
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// Make avatar speak
async function speakText(sessionId, text) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      session_id: sessionId,
      text: text,
      task_type: 'talk'
    });
    const req = https.request({
      hostname: 'api.heygen.com',
      path: '/v1/streaming.task',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': HEYGEN_API_KEY,
        'Content-Length': body.length
      }
    }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => resolve(JSON.parse(data)));
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// Global state
let currentMeetingUuid = null;
let heygenSessionId = null;

async function main() {
  console.log('\n🤖 HeyGen Avatar Bot with Meeting Context');
  console.log('='.repeat(50));
  console.log(`📡 RTMS Service: ${RTMS_SERVICE_URL}`);
  console.log(`🧠 Cerebras: ${CEREBRAS_API_KEY ? 'Configured' : 'Not configured (will echo)'}`);

  // Check for active meetings with transcripts
  console.log('\n🔍 Checking for active meetings...');
  const { meetings } = await getActiveMeetings();
  if (meetings.length > 0) {
    console.log(`   Found ${meetings.length} active meeting(s):`);
    meetings.forEach(m => {
      console.log(`   - ${m.meetingId}: ${m.transcriptCount} transcripts`);
    });
    currentMeetingUuid = meetings[0].meetingId;
  } else {
    console.log('   No active meetings with transcripts yet');
  }

  // Step 1: Create HeyGen session
  console.log('\n📡 Creating HeyGen session...');
  const heygenData = await createHeyGenSession();
  heygenSessionId = heygenData.session_id;
  const livekitUrl = heygenData.url;
  const accessToken = heygenData.access_token;

  console.log(`   ✓ Session: ${heygenSessionId.substring(0, 20)}...`);

  await startHeyGenSession(heygenSessionId);
  console.log('   ✓ Session started');

  // Step 2: Create local server
  const PORT = 9876;

  const avatarHtml = `
<!DOCTYPE html>
<html>
<head>
  <title>HeyGen Avatar with Context</title>
  <script src="https://cdn.jsdelivr.net/npm/livekit-client@2.1.5/dist/livekit-client.umd.min.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #1a1a2e;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 20px;
      min-height: 100vh;
      font-family: system-ui;
      color: #fff;
    }
    #avatar-container {
      width: 640px;
      height: 480px;
      background: #000;
      border-radius: 12px;
      overflow: hidden;
    }
    #avatar-video {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    #status {
      margin-top: 15px;
      padding: 8px 16px;
      background: rgba(0,255,0,0.1);
      border-radius: 8px;
      font-family: monospace;
      color: #0f0;
    }
    #canvas { display: none; }
    .controls {
      margin-top: 20px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      width: 640px;
    }
    .input-row {
      display: flex;
      gap: 10px;
    }
    input {
      flex: 1;
      padding: 12px;
      border-radius: 8px;
      border: 1px solid #333;
      background: #2a2a4e;
      color: #fff;
      font-size: 14px;
    }
    button {
      padding: 12px 24px;
      background: #4CAF50;
      color: white;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 14px;
    }
    button:hover { background: #45a049; }
    button.secondary { background: #2196F3; }
    button.secondary:hover { background: #1976D2; }
    #context-box {
      margin-top: 15px;
      padding: 12px;
      background: #2a2a4e;
      border-radius: 8px;
      width: 640px;
      max-height: 200px;
      overflow-y: auto;
      font-family: monospace;
      font-size: 12px;
      white-space: pre-wrap;
    }
    #context-box h4 {
      color: #4CAF50;
      margin-bottom: 8px;
    }
  </style>
</head>
<body>
  <div id="avatar-container">
    <video id="avatar-video" autoplay playsinline></video>
  </div>
  <canvas id="canvas" width="640" height="480"></canvas>
  <div id="status">Connecting to LiveKit...</div>

  <div class="controls">
    <div class="input-row">
      <input type="text" id="question" placeholder="Ask a question..." />
      <button onclick="askQuestion()">Ask</button>
    </div>
    <div class="input-row">
      <button class="secondary" onclick="refreshContext()">Refresh Context</button>
      <button class="secondary" onclick="testGreeting()">Test Greeting</button>
    </div>
  </div>

  <div id="context-box">
    <h4>Meeting Transcript Context:</h4>
    <div id="context-content">Loading...</div>
  </div>

  <script>
    const LIVEKIT_URL = "${livekitUrl}";
    const ACCESS_TOKEN = "${accessToken}";
    const SESSION_ID = "${heygenSessionId}";
    const API_KEY = "${HEYGEN_API_KEY}";
    const RTMS_URL = "${RTMS_SERVICE_URL}";

    const video = document.getElementById('avatar-video');
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const status = document.getElementById('status');
    const contextContent = document.getElementById('context-content');

    let room = null;
    let currentContext = '';

    // Connect to LiveKit
    async function connect() {
      try {
        status.textContent = 'Creating LiveKit room...';
        room = new LivekitClient.Room({ adaptiveStream: true, dynacast: true });

        room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {
          if (track.kind === 'video') {
            status.textContent = 'Avatar connected!';
            track.attach(video);
            window.__avatarReady = true;
            startCanvasCapture();
          }
        });

        await room.connect(LIVEKIT_URL, ACCESS_TOKEN);
        status.textContent = 'Connected, waiting for avatar...';

        room.remoteParticipants.forEach(participant => {
          participant.trackPublications.forEach(publication => {
            if (publication.track?.kind === 'video') {
              publication.track.attach(video);
              status.textContent = 'Avatar ready!';
              window.__avatarReady = true;
              startCanvasCapture();
            }
          });
        });
      } catch (err) {
        status.textContent = 'Error: ' + err.message;
      }
    }

    function startCanvasCapture() {
      function draw() {
        if (video.readyState >= 2) {
          ctx.drawImage(video, 0, 0, 640, 480);
        }
        requestAnimationFrame(draw);
      }
      draw();
      window.__canvasStream = canvas.captureStream(30);
    }

    // Fetch transcript context
    async function refreshContext() {
      try {
        // Get active meetings first
        const meetingsRes = await fetch(RTMS_URL + '/api/transcripts');
        const { meetings } = await meetingsRes.json();

        if (meetings.length > 0) {
          const meetingId = meetings[0].meetingId;
          const res = await fetch(RTMS_URL + '/api/transcripts/' + encodeURIComponent(meetingId));
          const data = await res.json();
          currentContext = data.fullContext || '';
          contextContent.textContent = currentContext || 'No transcripts yet...';
          status.textContent = 'Context updated! ' + data.count + ' messages';
        } else {
          contextContent.textContent = 'No active meetings with transcripts';
        }
      } catch (e) {
        contextContent.textContent = 'Error fetching context: ' + e.message;
      }
    }

    // Ask question with context
    async function askQuestion() {
      const input = document.getElementById('question');
      const question = input.value.trim();
      if (!question) return;

      status.textContent = 'Generating response...';
      input.value = '';

      try {
        // Call backend to generate response
        const response = await fetch('/api/respond', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question, context: currentContext })
        });
        const { answer } = await response.json();

        status.textContent = 'Speaking: ' + answer.substring(0, 50) + '...';

        // Make avatar speak
        await fetch('https://api.heygen.com/v1/streaming.task', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'x-api-key': API_KEY },
          body: JSON.stringify({ session_id: SESSION_ID, text: answer, task_type: 'talk' })
        });

        status.textContent = 'Avatar speaking!';
      } catch (e) {
        status.textContent = 'Error: ' + e.message;
      }
    }

    async function testGreeting() {
      status.textContent = 'Speaking greeting...';
      await fetch('https://api.heygen.com/v1/streaming.task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-api-key': API_KEY },
        body: JSON.stringify({
          session_id: SESSION_ID,
          text: 'Hello! I am your AI Professor. I have access to the live meeting transcript and can answer questions about what has been discussed.',
          task_type: 'talk'
        })
      });
    }

    // Enter key to submit
    document.getElementById('question').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') askQuestion();
    });

    // Auto-refresh context every 10 seconds
    setInterval(refreshContext, 10000);

    // Initialize
    connect();
    setTimeout(refreshContext, 1000);
  </script>
</body>
</html>
  `;

  const server = http.createServer(async (req, res) => {
    if (req.method === 'POST' && req.url === '/api/respond') {
      let body = '';
      req.on('data', chunk => body += chunk);
      req.on('end', async () => {
        try {
          const { question, context } = JSON.parse(body);
          const answer = await generateResponse(question, context);
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ answer }));
        } catch (e) {
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: e.message }));
        }
      });
    } else {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(avatarHtml);
    }
  });

  server.listen(PORT, () => {
    console.log(`\n✅ Avatar server running at: http://localhost:${PORT}`);
    console.log('\nOpen this URL in your browser to interact with the avatar.');
    console.log('The avatar will have access to the live meeting transcript.');
    console.log('\nPress Ctrl+C to stop.');
  });

  // Keep alive
  await new Promise(() => {});
}

main().catch(err => {
  console.error('\n❌ Error:', err);
  process.exit(1);
});
