/**
 * HeyGen Bridge
 * Forwards RTMS transcripts to Python backend for HeyGen avatar context updates
 */
import fetch from 'node-fetch';

export class HeyGenBridge {
  constructor(pythonBackendUrl) {
    this.backendUrl = pythonBackendUrl || 'http://localhost:8000';
    this.activeSessions = new Map(); // meetingUuid -> { roomId, streamId }
  }

  /**
   * Notify backend that RTMS session started
   */
  async notifySessionStart(meetingUuid, streamId, roomId = null) {
    try {
      const response = await fetch(`${this.backendUrl}/api/rtms/session-start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          meeting_uuid: meetingUuid,
          rtms_stream_id: streamId,
          room_id: roomId
        })
      });

      if (response.ok) {
        this.activeSessions.set(meetingUuid, { streamId, roomId });
        console.log(`[HeyGenBridge] Session started: ${meetingUuid}`);
      } else {
        console.error(`[HeyGenBridge] Failed to notify session start: ${response.statusText}`);
      }
    } catch (error) {
      console.error('[HeyGenBridge] Error notifying session start:', error);
    }
  }

  /**
   * Notify backend that RTMS session stopped
   */
  async notifySessionStop(meetingUuid) {
    try {
      await fetch(`${this.backendUrl}/api/rtms/session-stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ meeting_uuid: meetingUuid })
      });

      this.activeSessions.delete(meetingUuid);
      console.log(`[HeyGenBridge] Session stopped: ${meetingUuid}`);
    } catch (error) {
      console.error('[HeyGenBridge] Error notifying session stop:', error);
    }
  }

  /**
   * Forward transcript to Python backend
   */
  async forwardTranscript(meetingUuid, userName, text, timestamp) {
    try {
      const session = this.activeSessions.get(meetingUuid);
      const roomId = session?.roomId;

      const response = await fetch(`${this.backendUrl}/api/rtms/transcript`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          meeting_uuid: meetingUuid,
          speaker_name: userName,
          text: text,
          timestamp: timestamp,
          room_id: roomId
        })
      });

      if (!response.ok) {
        console.error(`[HeyGenBridge] Failed to forward transcript: ${response.statusText}`);
      }
    } catch (error) {
      console.error('[HeyGenBridge] Error forwarding transcript:', error);
    }
  }

  /**
   * Get session info
   */
  getSession(meetingUuid) {
    return this.activeSessions.get(meetingUuid);
  }

  /**
   * Check if session is active
   */
  isSessionActive(meetingUuid) {
    return this.activeSessions.has(meetingUuid);
  }
}

export default HeyGenBridge;
