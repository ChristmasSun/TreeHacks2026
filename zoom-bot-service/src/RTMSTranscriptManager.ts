/**
 * RTMS Transcript Manager
 * Handles Zoom RTMS connections and forwards transcript data to Python backend
 */
import rtms from '@zoom/rtms';
import { EventEmitter } from 'events';
import fetch from 'node-fetch';

interface RTMSConfig {
  clientId: string;
  clientSecret: string;
  pythonBackendUrl: string;
}

interface TranscriptData {
  meeting_uuid: string;
  speaker_name: string;
  text: string;
  timestamp: number;
  user_id?: string;
}

export class RTMSTranscriptManager extends EventEmitter {
  private config: RTMSConfig;
  private activeClients: Map<string, any> = new Map(); // meeting_uuid -> rtms.Client
  private meetingRoomMap: Map<string, number> = new Map(); // meeting_uuid -> room_id

  constructor(config: RTMSConfig) {
    super();
    this.config = config;
    console.log('📝 RTMS Transcript Manager initialized');
  }

  /**
   * Handle RTMS webhook event
   * Called when meeting.rtms_started or meeting.rtms_stopped events are received
   */
  async handleWebhookEvent(event: string, payload: any, roomId?: number): Promise<void> {
    console.log(`[RTMS] Webhook event: ${event}`, payload);

    const RTMS_START_EVENTS = [
      'meeting.rtms_started',
      'webinar.rtms_started',
      'session.rtms_started'
    ];

    const RTMS_STOP_EVENTS = [
      'meeting.rtms_stopped',
      'webinar.rtms_stopped',
      'session.rtms_stopped'
    ];

    if (RTMS_START_EVENTS.includes(event)) {
      await this.startTranscription(payload, roomId);
    } else if (RTMS_STOP_EVENTS.includes(event)) {
      await this.stopTranscription(payload);
    }
  }

  /**
   * Start RTMS transcription for a meeting
   */
  private async startTranscription(payload: any, roomId?: number): Promise<void> {
    const meetingUuid = payload.meeting_uuid || payload.session_id;
    const rtmsStreamId = payload.rtms_stream_id;

    if (!meetingUuid || !rtmsStreamId) {
      console.error('[RTMS] Missing required fields in webhook payload');
      return;
    }

    console.log(`[RTMS] Starting transcription for meeting ${meetingUuid}`);

    // Store room mapping if provided
    if (roomId) {
      this.meetingRoomMap.set(meetingUuid, roomId);
    }

    try {
      // Create RTMS client
      const client = new rtms.Client();

      // Set up event handlers BEFORE joining
      client.onJoinConfirm((reason: number) => {
        console.log(`[RTMS] Successfully joined session with code: ${reason}`);
        this.emit('rtms-joined', { meeting_uuid: meetingUuid, room_id: roomId });
      });

      client.onTranscriptData((data: Buffer, timestamp: number, metadata: any) => {
        const text = data.toString('utf8');
        const transcriptData: TranscriptData = {
          meeting_uuid: meetingUuid,
          speaker_name: metadata.userName || 'Unknown',
          text: text,
          timestamp: timestamp,
          user_id: metadata.userId
        };

        console.log(`[RTMS] Transcript: ${metadata.userName}: ${text}`);

        // Forward to backend
        this.forwardTranscript(transcriptData, roomId);

        // Emit local event
        this.emit('transcript', transcriptData);
      });

      client.onAudioData((data: Buffer, timestamp: number, metadata: any) => {
        // Optional: Handle audio data if needed for Whisper integration
        this.emit('audio', {
          meeting_uuid: meetingUuid,
          audio_data: data,
          timestamp: timestamp,
          metadata: metadata
        });
      });

      // Join the RTMS session
      await client.join(payload);

      // Store client reference
      this.activeClients.set(meetingUuid, client);

      // Notify backend that session started
      await this.notifyBackendSessionStart(meetingUuid, rtmsStreamId, roomId);

    } catch (error) {
      console.error(`[RTMS] Failed to start transcription:`, error);
      this.emit('rtms-error', { meeting_uuid: meetingUuid, error });
    }
  }

  /**
   * Stop RTMS transcription for a meeting
   */
  private async stopTranscription(payload: any): Promise<void> {
    const meetingUuid = payload.meeting_uuid || payload.session_id;

    console.log(`[RTMS] Stopping transcription for meeting ${meetingUuid}`);

    const client = this.activeClients.get(meetingUuid);
    if (client) {
      try {
        await client.leave();
        this.activeClients.delete(meetingUuid);

        // Notify backend
        await this.notifyBackendSessionStop(meetingUuid);

        // Clean up mapping
        this.meetingRoomMap.delete(meetingUuid);
      } catch (error) {
        console.error(`[RTMS] Error stopping transcription:`, error);
      }
    } else {
      console.warn(`[RTMS] No active client found for meeting ${meetingUuid}`);
    }
  }

  /**
   * Forward transcript to Python backend
   */
  private async forwardTranscript(transcript: TranscriptData, roomId?: number): Promise<void> {
    try {
      const response = await fetch(`${this.config.pythonBackendUrl}/api/rtms/transcript`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...transcript,
          room_id: roomId || this.meetingRoomMap.get(transcript.meeting_uuid)
        })
      });

      if (!response.ok) {
        console.error(`[RTMS] Failed to forward transcript: ${response.statusText}`);
      }
    } catch (error) {
      console.error('[RTMS] Error forwarding transcript to backend:', error);
    }
  }

  /**
   * Notify backend that RTMS session started
   */
  private async notifyBackendSessionStart(
    meetingUuid: string,
    rtmsStreamId: string,
    roomId?: number
  ): Promise<void> {
    try {
      await fetch(`${this.config.pythonBackendUrl}/api/rtms/session-start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          meeting_uuid: meetingUuid,
          rtms_stream_id: rtmsStreamId,
          room_id: roomId
        })
      });
    } catch (error) {
      console.error('[RTMS] Error notifying backend of session start:', error);
    }
  }

  /**
   * Notify backend that RTMS session stopped
   */
  private async notifyBackendSessionStop(meetingUuid: string): Promise<void> {
    try {
      await fetch(`${this.config.pythonBackendUrl}/api/rtms/session-stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ meeting_uuid: meetingUuid })
      });
    } catch (error) {
      console.error('[RTMS] Error notifying backend of session stop:', error);
    }
  }

  /**
   * Get active sessions
   */
  getActiveSessions(): string[] {
    return Array.from(this.activeClients.keys());
  }

  /**
   * Check if session is active
   */
  isSessionActive(meetingUuid: string): boolean {
    return this.activeClients.has(meetingUuid);
  }

  /**
   * Stop all active sessions
   */
  async stopAllSessions(): Promise<void> {
    console.log('[RTMS] Stopping all active sessions');
    const promises = Array.from(this.activeClients.keys()).map(meetingUuid =>
      this.stopTranscription({ meeting_uuid: meetingUuid })
    );
    await Promise.all(promises);
  }
}
