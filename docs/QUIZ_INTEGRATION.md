# Quiz Integration Guide

This document explains how to generate educational videos from YouTube lectures, create quizzes, and deliver them via Zoom Team Chat.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MANIM PIPELINE                                  │
│  YouTube URL → Transcribe → Scene Split → Narration → Render → Stitch       │
│                                    ↓                                         │
│                         outputs/{topic}/                                     │
│                         ├── videos/scene_XXX_voiced.mp4                     │
│                         ├── quiz_questions.json                              │
│                         └── scene_plan.json                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ZOOM CHATBOT FLOW                                  │
│                                                                              │
│  User types /makequiz                                                        │
│         ↓                                                                    │
│  Zoom sends webhook → Render (Node.js) → WebSocket → Local Python           │
│         ↓                                                                    │
│  Python loads quiz_questions.json                                            │
│         ↓                                                                    │
│  Sends interactive quiz cards via Zoom API                                   │
│         ↓                                                                    │
│  On wrong answer → triggers video playback                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Step 1: Generate Videos from YouTube

```bash
# Set environment variables
export DEDALUS_API_KEY="your-dedalus-key"
export HF_TOKEN="your-huggingface-token"

# Run the pipeline
uv run python -c "
import asyncio
from src.pipeline import run

result = asyncio.run(run(
    'https://www.youtube.com/watch?v=YOUR_VIDEO_ID',
    'outputs/your-topic-name',
    clip_concurrency=4,
    max_render_attempts=3
))
print(f'Result: {result}')
"
```

This creates:
- `outputs/your-topic-name/videos/` - Individual scene videos with voiceover
- `outputs/your-topic-name/scene_plan.json` - Concepts and descriptions
- `outputs/your-topic-name/transcript.txt` - Full transcript

## Step 2: Generate Quiz Questions

Quiz questions can be generated automatically or manually created.

### Automatic Generation

```python
from backend.services.quiz_generator import generate_quiz_from_output_dir

quiz = await generate_quiz_from_output_dir(
    output_dir="outputs/your-topic-name",
    num_questions=10,
    topic="Your Topic Name"
)

# Save to JSON
import json
with open("outputs/your-topic-name/quiz_questions.json", "w") as f:
    json.dump([{
        "id": q.id,
        "concept": q.concept,
        "question": q.question_text,
        "options": q.options,
        "correct_answer": q.correct_answer,
        "explanation": q.explanation,
        "video_path": q.video_path
    } for q in quiz.questions], f, indent=2)
```

### Manual Quiz Format

Create `quiz_questions.json` with this structure:

```json
[
  {
    "id": "q1",
    "concept": "Concept Name (shown as tag)",
    "question": "What is the main idea of...?",
    "options": [
      "A) First option",
      "B) Second option",
      "C) Third option",
      "D) Fourth option"
    ],
    "correct_answer": "B",
    "explanation": "Explanation shown after answering",
    "video_path": "outputs/your-topic-name/videos/scene_001_voiced.mp4"
  }
]
```

The `video_path` links each question to its explainer video - shown when the student answers incorrectly.

## Step 3: Configure Zoom Chatbot

### Environment Variables

Create `backend/.env`:

```bash
# Zoom Chatbot (from Zoom Marketplace → Your App → Features → Chatbot)
ZOOM_CHATBOT_CLIENT_ID=your_client_id
ZOOM_CHATBOT_CLIENT_SECRET=your_client_secret
ZOOM_BOT_JID=v1xxxxx@xmpp.zoom.us

# Quiz data directory
QUIZ_DATA_DIR=outputs/your-topic-name

# Render WebSocket URL
RENDER_WS_URL=wss://rtms-webhook.onrender.com/ws
```

### Run the Chatbot Client

```bash
python backend/run_chatbot_client.py
```

This connects to Render via WebSocket and handles:
- `/makequiz` command → Sends quiz intro with Start/Cancel buttons
- Button clicks → Processes answers, sends feedback
- Wrong answers → Triggers video playback notification

## Step 4: Wiring into the Dashboard

### Auto-DM Students When Professor Clicks Button

To send quizzes to meeting participants when a professor triggers it from the dashboard:

```python
# In your dashboard backend (e.g., FastAPI endpoint)
from backend.services.zoom_chatbot_service import send_quiz_intro, get_user_jid
from backend.services.quiz_generator import load_quiz_from_json
from backend.services.quiz_session_manager import create_session

@app.post("/api/send-quiz-to-participants")
async def send_quiz_to_participants(meeting_id: str, quiz_path: str):
    """
    Called when professor clicks "Send Quiz" in dashboard.
    Sends quiz to all meeting participants via DM.
    """
    # 1. Get meeting participants from RTMS service
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{RTMS_SERVICE_URL}/api/participants/{meeting_id}")
        participants = resp.json()["participants"]

    # 2. Load the quiz
    quiz = load_quiz_from_json(quiz_path)

    # 3. Send quiz to each participant
    for participant in participants:
        email = participant["email"]
        user_jid = await get_user_jid(email)

        if user_jid:
            # Create session for this student
            create_session(
                student_jid=user_jid,
                account_id=ZOOM_ACCOUNT_ID,
                quiz=quiz,
                user_jid=user_jid
            )

            # Send quiz intro
            await send_quiz_intro(
                to_jid=user_jid,
                account_id=ZOOM_ACCOUNT_ID,
                topic=quiz.topic,
                num_questions=len(quiz.questions),
                user_jid=user_jid
            )

    return {"sent_to": len(participants)}
```

### Dashboard UI Integration

Add a button in your React/Electron dashboard:

```javascript
// Dashboard component
function QuizControl({ meetingId }) {
  const [quizzes, setQuizzes] = useState([]);

  useEffect(() => {
    // Load available quizzes from outputs/
    fetch('/api/available-quizzes')
      .then(r => r.json())
      .then(setQuizzes);
  }, []);

  const sendQuiz = async (quizPath) => {
    await fetch('/api/send-quiz-to-participants', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ meeting_id: meetingId, quiz_path: quizPath })
    });
  };

  return (
    <div>
      <h3>Send Quiz to Participants</h3>
      {quizzes.map(quiz => (
        <button key={quiz.path} onClick={() => sendQuiz(quiz.path)}>
          {quiz.name} ({quiz.questions} questions)
        </button>
      ))}
    </div>
  );
}
```

### Real-time Video Playback

When a student answers wrong, the system can trigger video playback in the dashboard:

```python
# In chatbot_ws_handler.py - already implemented
async def trigger_video_playback(student_jid: str, concept: str, video_path: str):
    """Sends WebSocket message to dashboard to play video."""
    await send_to_render({
        "type": "play_video",
        "data": {
            "student_jid": student_jid,
            "concept": concept,
            "video_path": video_path
        }
    })
```

```javascript
// In dashboard WebSocket handler
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  if (msg.type === 'play_video') {
    // Play the explainer video for this student
    playVideo(msg.data.video_path, msg.data.student_jid);
  }
};
```

## Project Structure

```
TreeHacks2026/
├── src/                          # Manim video pipeline
│   ├── pipeline.py               # Main orchestration
│   ├── downloader.py             # YouTube audio download
│   ├── transcribe.py             # Whisper transcription
│   ├── scene_splitter.py         # LLM-based scene planning
│   ├── clip_generator.py         # Manim code generation
│   ├── voice.py                  # TTS with voice cloning
│   └── stitcher.py               # Final video assembly
│
├── backend/                      # Python backend services
│   ├── app.py                    # FastAPI main app
│   ├── run_chatbot_client.py     # WebSocket client runner
│   └── services/
│       ├── render_ws_client.py   # Connects to Render WebSocket
│       ├── chatbot_ws_handler.py # Handles chatbot events
│       ├── quiz_generator.py     # Generates quiz questions
│       ├── quiz_session_manager.py # Tracks quiz state per student
│       └── zoom_chatbot_service.py # Zoom API calls
│
├── rtms-zoom-official/           # Node.js Render service
│   ├── index.js                  # Express server + webhook handling
│   └── frontendWss.js            # WebSocket broadcasting
│
├── outputs/                      # Generated content
│   └── {topic-name}/
│       ├── audio.mp3             # Downloaded audio
│       ├── transcript.txt        # Full transcript
│       ├── scene_plan.json       # Concept breakdown
│       ├── quiz_questions.json   # Quiz data
│       └── videos/
│           ├── scene_XXX_voiced.mp4
│           └── final.mp4
│
└── docs/
    └── QUIZ_INTEGRATION.md       # This file
```

## Data Flow Summary

1. **Video Generation**: YouTube → Transcript → Scene Plan → Manim Animations → Voiced Videos

2. **Quiz Creation**: Scene Plan → LLM generates questions → Links to videos

3. **Quiz Delivery**:
   - Zoom webhook → Render → WebSocket → Local Python
   - Python processes command → Zoom API sends cards
   - Student clicks button → webhook → process answer → feedback

4. **Video on Wrong Answer**:
   - Student answers wrong → Python sends "play_video" via WebSocket
   - Dashboard receives → plays explainer video
   - Student watches → continues quiz

## Key Integration Points

| Component | Connects To | Via |
|-----------|-------------|-----|
| Manim Pipeline | outputs/ folder | File system |
| Quiz Generator | scene_plan.json | JSON parsing |
| Chatbot Client | Render | WebSocket |
| Render | Zoom | HTTP webhooks |
| Python | Zoom API | REST calls |
| Dashboard | Render | WebSocket |

## Extending the System

### Add New Quiz Topic

1. Run pipeline on new YouTube video
2. Quiz questions auto-link to videos via scene index
3. Set `QUIZ_DATA_DIR` to new output folder
4. Restart chatbot client

### Custom Quiz Logic

Modify `backend/services/quiz_session_manager.py`:
- Change scoring rules
- Add time limits
- Implement adaptive difficulty
- Track learning analytics

### Multiple Simultaneous Quizzes

The session manager uses `student_jid` as key, so each student can have their own independent quiz session with any topic.
