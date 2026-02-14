#!/usr/bin/env python3
"""
Demo: Breakout Room Trigger Script

This shows how a professor/admin would trigger breakout rooms,
which then notifies registered students to show their HeyGen avatars.

ZOOM BREAKOUT ROOM API (for reference):
- POST /meetings/{meetingId}/breakout_rooms - Create breakout rooms during live meeting
- PATCH /meetings/{meetingId}/breakout_rooms/{roomId} - Assign/move participants
- GET /meetings/{meetingId}/breakout_rooms - List breakout rooms

ZOOM WEBHOOKS (for real-time detection):
- meeting.participant_joined_breakout_room
- meeting.participant_left_breakout_room  
- meeting.participant_moved_to_breakout_room

HOW IT WORKS:
1. Professor starts Zoom meeting
2. Students join (each has our Electron app running in background)
3. Professor clicks "Create Breakout Rooms" in Zoom (or via API)
4. We detect this via:
   a) Zoom webhook if we have a registered app, OR
   b) Manual trigger via this script for demo purposes
5. Our backend notifies all registered students
6. Each student's Electron app expands and shows HeyGen avatar
"""

import asyncio
import aiohttp
import sys

BACKEND_URL = "http://127.0.0.1:8000"


async def trigger_breakout_demo():
    """
    Trigger breakout rooms for all registered students.
    
    In production, this would be called by:
    - Zoom webhook (meeting.participant_joined_breakout_room)
    - OR professor's dashboard button
    """
    print("\n" + "="*60)
    print("🎓 AI TUTOR - Breakout Room Demo")
    print("="*60 + "\n")
    
    # Simulate session info
    session_id = "demo-session-" + str(int(asyncio.get_event_loop().time()))
    
    print(f"📋 Session ID: {session_id}")
    print(f"🔗 Backend URL: {BACKEND_URL}\n")
    
    # Check backend health
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BACKEND_URL}/health") as resp:
                health = await resp.json()
                print(f"✅ Backend healthy: {health['active_connections']} connected clients")
        except Exception as e:
            print(f"❌ Backend not responding: {e}")
            print("\nMake sure to start the backend first:")
            print("  cd backend && python -m uvicorn app:app --reload --port 8000")
            return
    
    print("\n" + "-"*60)
    print("📣 Triggering breakout rooms...")
    print("-"*60 + "\n")
    
    # Trigger breakout via REST API
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{BACKEND_URL}/api/trigger-breakout",
                json={"session_id": session_id}
            ) as resp:
                result = await resp.json()
                
                if resp.status == 200:
                    print(f"✅ Breakout triggered!")
                    print(f"   Students notified: {result.get('students_notified', 0)}")
                    
                    if result.get('students_notified', 0) == 0:
                        print("\n⚠️  No students registered yet!")
                        print("   Open the Electron app and register first.\n")
                else:
                    print(f"❌ Error: {result}")
                    
        except Exception as e:
            print(f"❌ Failed to trigger breakout: {e}")


async def list_registered_students():
    """Check who's registered"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BACKEND_URL}/health") as resp:
                health = await resp.json()
                print(f"\n📊 Connected clients: {health['active_connections']}")
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║           AI Professor Tutor - Demo Script                 ║
║                                                            ║
║  This simulates a professor triggering breakout rooms.     ║
║  In production, this would happen via Zoom webhooks.       ║
╚════════════════════════════════════════════════════════════╝

STEPS TO TEST:
1. Start backend:    cd backend && python -m uvicorn app:app --reload --port 8000
2. Start Electron:   npm run build && npx electron-vite dev
3. Register in app:  Click "Setup", enter name/email, click "Register"
4. Run this script:  python scripts/demo_breakout.py
5. Watch the Electron app expand with HeyGen avatar!

""")

    asyncio.run(trigger_breakout_demo())
    
    print("""
═══════════════════════════════════════════════════════════════

REAL ZOOM INTEGRATION (future):

To actually detect breakout rooms from Zoom, you'd:

1. Create a Zoom App at marketplace.zoom.us
2. Add webhook subscription for:
   - meeting.participant_joined_breakout_room
   - meeting.participant_left_breakout_room

3. When webhook fires, call our API:
   POST /api/trigger-breakout
   {
     "session_id": "zoom-meeting-12345",
     "room_name": "Breakout Room 1",
     "participants": ["student@email.com", ...]
   }

4. Our backend notifies matching students via WebSocket
5. Their Electron apps expand to show HeyGen

═══════════════════════════════════════════════════════════════
""")


if __name__ == "__main__":
    main()
