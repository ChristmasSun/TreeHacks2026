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
const DEEPGRAM_API_KEY = process.env.DEEPGRAM_API_KEY;
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
  <title>HeyGen Avatar - Voice Conversation</title>
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
      position: relative;
    }
    #avatar-video {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    #mic-indicator {
      position: absolute;
      bottom: 15px;
      right: 15px;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: #666;
      transition: all 0.2s;
    }
    #mic-indicator.listening {
      background: #f44336;
      box-shadow: 0 0 20px #f44336;
      animation: pulse 1s infinite;
    }
    @keyframes pulse {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.2); }
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
    button.mic { background: #f44336; }
    button.mic:hover { background: #d32f2f; }
    button.mic.active { background: #4CAF50; }
    #transcript-box {
      margin-top: 15px;
      padding: 12px;
      background: #2a2a4e;
      border-radius: 8px;
      width: 640px;
      max-height: 300px;
      overflow-y: auto;
    }
    #transcript-box h4 {
      color: #4CAF50;
      margin-bottom: 8px;
    }
    .message {
      padding: 8px 12px;
      margin: 5px 0;
      border-radius: 8px;
      max-width: 85%;
    }
    .message.user {
      background: #2196F3;
      margin-left: auto;
      text-align: right;
    }
    .message.avatar {
      background: #333;
    }
    .message.interim {
      opacity: 0.6;
      font-style: italic;
    }
    #context-box {
      margin-top: 15px;
      padding: 12px;
      background: #2a2a4e;
      border-radius: 8px;
      width: 640px;
      max-height: 150px;
      overflow-y: auto;
      font-family: monospace;
      font-size: 11px;
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
    <div id="mic-indicator"></div>
  </div>
  <canvas id="canvas" width="640" height="480"></canvas>
  <div id="status">Connecting to LiveKit...</div>

  <div class="controls">
    <div class="input-row">
      <button id="mic-btn" class="mic" onclick="toggleMic()">Start Conversation</button>
      <button class="secondary" onclick="testGreeting()">Test Greeting</button>
    </div>
    <div class="input-row">
      <input type="text" id="question" placeholder="Or type a question..." />
      <button onclick="askQuestion()">Send</button>
    </div>
  </div>

  <div id="transcript-box">
    <h4>Conversation:</h4>
    <div id="conversation"></div>
  </div>

  <div id="context-box">
    <h4>Meeting Context (from Zoom RTMS):</h4>
    <div id="context-content">Loading...</div>
  </div>

  <script>
    const LIVEKIT_URL = "${livekitUrl}";
    const ACCESS_TOKEN = "${accessToken}";
    const SESSION_ID = "${heygenSessionId}";
    const API_KEY = "${HEYGEN_API_KEY}";
    const RTMS_URL = "${RTMS_SERVICE_URL}";
    const DEEPGRAM_KEY = "${DEEPGRAM_API_KEY || ''}";

    const video = document.getElementById('avatar-video');
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const status = document.getElementById('status');
    const contextContent = document.getElementById('context-content');
    const conversation = document.getElementById('conversation');
    const micIndicator = document.getElementById('mic-indicator');
    const micBtn = document.getElementById('mic-btn');

    let room = null;
    let currentContext = '';
    let isListening = false;
    let mediaRecorder = null;
    let deepgramSocket = null;
    let interimText = '';
    let finalText = '';
    let silenceTimer = null;
    let isAvatarSpeaking = false;

    // Connect to LiveKit for HeyGen
    async function connect() {
      try {
        status.textContent = 'Creating LiveKit room...';
        room = new LivekitClient.Room({ adaptiveStream: true, dynacast: true });

        room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {
          if (track.kind === 'video') {
            status.textContent = 'Avatar connected! Click "Start Conversation"';
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
              status.textContent = 'Avatar ready! Click "Start Conversation"';
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
    }

    // Add message to conversation
    function addMessage(text, type, isInterim = false) {
      if (isInterim) {
        let interimEl = conversation.querySelector('.interim');
        if (!interimEl) {
          interimEl = document.createElement('div');
          interimEl.className = 'message user interim';
          conversation.appendChild(interimEl);
        }
        interimEl.textContent = text;
      } else {
        // Remove interim message
        const interimEl = conversation.querySelector('.interim');
        if (interimEl) interimEl.remove();

        const msg = document.createElement('div');
        msg.className = 'message ' + type;
        msg.textContent = text;
        conversation.appendChild(msg);
      }
      conversation.scrollTop = conversation.scrollHeight;
    }

    // Toggle microphone
    async function toggleMic() {
      if (isListening) {
        stopListening();
      } else {
        await startListening();
      }
    }

    // Start listening with Deepgram
    async function startListening() {
      if (!DEEPGRAM_KEY) {
        status.textContent = 'Deepgram API key not configured';
        return;
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        // Connect to Deepgram
        deepgramSocket = new WebSocket(
          'wss://api.deepgram.com/v1/listen?model=nova-2&punctuate=true&interim_results=true&endpointing=300',
          ['token', DEEPGRAM_KEY]
        );

        deepgramSocket.onopen = () => {
          status.textContent = 'Listening... speak now!';
          isListening = true;
          micIndicator.classList.add('listening');
          micBtn.textContent = 'Stop Conversation';
          micBtn.classList.add('active');

          // Create MediaRecorder to send audio
          mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
          mediaRecorder.ondataavailable = (e) => {
            if (deepgramSocket?.readyState === WebSocket.OPEN && !isAvatarSpeaking) {
              deepgramSocket.send(e.data);
            }
          };
          mediaRecorder.start(100); // Send every 100ms
        };

        deepgramSocket.onmessage = (msg) => {
          const data = JSON.parse(msg.data);
          const transcript = data.channel?.alternatives?.[0]?.transcript;

          if (transcript) {
            if (data.is_final) {
              finalText += ' ' + transcript;
              addMessage(finalText.trim(), 'user', false);

              // Reset silence timer
              clearTimeout(silenceTimer);
              silenceTimer = setTimeout(() => {
                if (finalText.trim()) {
                  processUserInput(finalText.trim());
                  finalText = '';
                }
              }, 1500); // 1.5s of silence triggers response
            } else {
              interimText = finalText + ' ' + transcript;
              addMessage(interimText.trim(), 'user', true);
            }
          }
        };

        deepgramSocket.onerror = (e) => {
          console.error('Deepgram error:', e);
          status.textContent = 'Speech recognition error';
          stopListening();
        };

        deepgramSocket.onclose = () => {
          if (isListening) stopListening();
        };

      } catch (err) {
        status.textContent = 'Microphone error: ' + err.message;
      }
    }

    function stopListening() {
      isListening = false;
      micIndicator.classList.remove('listening');
      micBtn.textContent = 'Start Conversation';
      micBtn.classList.remove('active');

      if (mediaRecorder?.state !== 'inactive') {
        mediaRecorder?.stop();
      }
      if (deepgramSocket?.readyState === WebSocket.OPEN) {
        deepgramSocket.close();
      }
      clearTimeout(silenceTimer);
      status.textContent = 'Conversation paused';
    }

    // Process user input and get avatar response
    async function processUserInput(text) {
      if (!text.trim() || isAvatarSpeaking) return;

      status.textContent = 'Thinking...';
      isAvatarSpeaking = true;

      try {
        // Get response from Cerebras via backend
        const response = await fetch('/api/respond', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: text, context: currentContext })
        });
        const { answer } = await response.json();

        addMessage(answer, 'avatar');
        status.textContent = 'Avatar speaking...';

        // Make avatar speak
        await fetch('https://api.heygen.com/v1/streaming.task', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'x-api-key': API_KEY },
          body: JSON.stringify({ session_id: SESSION_ID, text: answer, task_type: 'talk' })
        });

        // Estimate speaking time (rough: 150 words per minute)
        const wordCount = answer.split(' ').length;
        const speakingTime = Math.max(2000, (wordCount / 150) * 60 * 1000);

        setTimeout(() => {
          isAvatarSpeaking = false;
          status.textContent = 'Listening...';
        }, speakingTime);

      } catch (e) {
        status.textContent = 'Error: ' + e.message;
        isAvatarSpeaking = false;
      }
    }

    // Fetch transcript context
    async function refreshContext() {
      try {
        const meetingsRes = await fetch(RTMS_URL + '/api/transcripts');
        const { meetings } = await meetingsRes.json();

        if (meetings.length > 0) {
          const meetingId = meetings[0].meetingId;
          const res = await fetch(RTMS_URL + '/api/transcripts/' + encodeURIComponent(meetingId));
          const data = await res.json();
          currentContext = data.fullContext || '';
          contextContent.textContent = currentContext || 'No transcripts yet...';
        } else {
          contextContent.textContent = 'No active meetings';
        }
      } catch (e) {
        contextContent.textContent = 'Error: ' + e.message;
      }
    }

    // Text input fallback
    async function askQuestion() {
      const input = document.getElementById('question');
      const question = input.value.trim();
      if (!question) return;
      input.value = '';
      addMessage(question, 'user');
      await processUserInput(question);
    }

    async function testGreeting() {
      isAvatarSpeaking = true;
      status.textContent = 'Avatar speaking...';
      addMessage("Hello! I'm your AI Professor. I have access to the live meeting transcript. Feel free to ask me anything about what's been discussed!", 'avatar');

      await fetch('https://api.heygen.com/v1/streaming.task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-api-key': API_KEY },
        body: JSON.stringify({
          session_id: SESSION_ID,
          text: "Hello! I'm your AI Professor. I have access to the live meeting transcript. Feel free to ask me anything about what's been discussed!",
          task_type: 'talk'
        })
      });

      setTimeout(() => {
        isAvatarSpeaking = false;
        status.textContent = 'Ready';
      }, 8000);
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
