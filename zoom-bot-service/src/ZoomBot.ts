/**
 * ZoomBot - Individual bot that joins Zoom meetings
 * Uses Zoom Rivet SDK for headless bot participation
 */
import { EventEmitter } from 'events';
import { BotConfig, BotStatus, AudioChunk } from './types';
import { generateJWT } from './utils/signature';
import axios from 'axios';
import { RivetClient } from '@zoom/rivet';

export class ZoomBot extends EventEmitter {
  private botId: string;
  private config: BotConfig;
  private status: BotStatus;
  private zoomParticipantId?: string;
  private audioEnabled: boolean = false;
  private rivetClient: RivetClient | null = null;

  constructor(botId: string, config: BotConfig) {
    super();
    this.botId = botId;
    this.config = config;
    this.status = BotStatus.INITIALIZING;
  }

  /**
   * Join Zoom meeting using Rivet SDK
   */
  async join(): Promise<void> {
    try {
      this.status = BotStatus.JOINING;
      this.emit('status-change', this.status);

      console.log(`[Bot ${this.botId}] Joining meeting ${this.config.meetingNumber}`);

      const signature = generateJWT(
        process.env.ZOOM_SDK_KEY!,
        process.env.ZOOM_SDK_SECRET!,
        this.config.meetingNumber,
        0
      );

      this.rivetClient = new RivetClient({
        sessionName: this.config.botName,
        sessionPasscode: this.config.passcode || '',
      });

      this.rivetClient.on('connected', () => {
        console.log(`[Bot ${this.botId}] Connected to Zoom via Rivet`);
        this.zoomParticipantId = this.rivetClient?.getParticipantId();
      });

      this.rivetClient.on('peer-video-state-change', (payload: any) => {
        console.log(`[Bot ${this.botId}] Peer video state changed:`, payload);
      });

      this.rivetClient.on('active-speaker', (payload: any) => {
        console.log(`[Bot ${this.botId}] Active speaker:`, payload);
      });

      this.rivetClient.on('error', (error: Error) => {
        console.error(`[Bot ${this.botId}] Rivet error:`, error);
        this.emit('error', error);
      });

      await this.rivetClient.join({
        meetingNumber: this.config.meetingNumber,
        signature: signature,
        sdkKey: process.env.ZOOM_SDK_KEY!,
        userName: this.config.botName,
        password: this.config.passcode
      });

      this.status = BotStatus.JOINED;
      this.emit('status-change', this.status);
      this.emit('joined');

      console.log(`[Bot ${this.botId}] Successfully joined meeting`);

    } catch (error) {
      this.status = BotStatus.ERROR;
      this.emit('status-change', this.status);
      this.emit('error', error);
      throw error;
    }
  }

  /**
   * Join a specific breakout room
   */
  async joinBreakoutRoom(breakoutRoomId: string): Promise<void> {
    try {
      console.log(`[Bot ${this.botId}] Joining breakout room ${breakoutRoomId}`);

      if (!this.rivetClient) {
        throw new Error('Bot not connected to Zoom');
      }

      await this.rivetClient.joinBreakoutRoom(breakoutRoomId);

      this.status = BotStatus.IN_BREAKOUT_ROOM;
      this.emit('status-change', this.status);
      this.emit('joined-breakout-room', breakoutRoomId);

      console.log(`[Bot ${this.botId}] Successfully joined breakout room`);

    } catch (error) {
      this.emit('error', error);
      throw error;
    }
  }

  /**
   * Enable audio capture and streaming using Rivet
   */
  async enableAudio(): Promise<void> {
    if (this.audioEnabled) return;

    console.log(`[Bot ${this.botId}] Enabling audio`);

    if (!this.rivetClient) {
      throw new Error('Bot not connected to Zoom');
    }

    this.rivetClient.subscribeToAudio();

    this.rivetClient.on('audio-data', (audioData: ArrayBuffer) => {
      const chunk: AudioChunk = {
        roomId: this.config.roomId,
        audioData: Buffer.from(audioData),
        timestamp: Date.now(),
        sampleRate: 16000,
        channels: 1
      };

      this.emit('audio-chunk', chunk);
    });

    await this.rivetClient.unmuteAudio();

    this.audioEnabled = true;
    this.emit('audio-enabled');
  }

  /**
   * Play audio in Zoom (for HeyGen avatar responses)
   */
  async playAudio(audioData: Buffer): Promise<void> {
    if (!this.audioEnabled) {
      console.warn(`[Bot ${this.botId}] Audio not enabled, cannot play`);
      return;
    }

    if (!this.rivetClient) {
      throw new Error('Bot not connected to Zoom');
    }

    console.log(`[Bot ${this.botId}] Playing audio chunk (${audioData.length} bytes)`);

    await this.rivetClient.sendAudio(audioData);
  }

  /**
   * Leave meeting and cleanup Rivet connection
   */
  async leave(): Promise<void> {
    console.log(`[Bot ${this.botId}] Leaving meeting`);

    try {
      if (this.rivetClient) {
        await this.rivetClient.leave();
        this.rivetClient.destroy();
        this.rivetClient = null;
      }

      this.status = BotStatus.DISCONNECTED;
      this.emit('status-change', this.status);
      this.emit('disconnected');

      console.log(`[Bot ${this.botId}] Left meeting successfully`);

    } catch (error) {
      this.emit('error', error);
      throw error;
    }
  }

  /**
   * Get current bot status
   */
  getStatus(): BotStatus {
    return this.status;
  }

  /**
   * Get bot info
   */
  getInfo() {
    return {
      botId: this.botId,
      meetingNumber: this.config.meetingNumber,
      botName: this.config.botName,
      roomId: this.config.roomId,
      status: this.status,
      zoomParticipantId: this.zoomParticipantId,
      heygenSessionId: this.config.heygenSessionId
    };
  }

  // ==================== Private Methods ====================

  /**
   * Send audio to Python backend for processing
   */
  private async sendAudioToBackend(audioChunk: AudioChunk): Promise<void> {
    try {
      await axios.post(
        `${process.env.PYTHON_BACKEND_URL}/api/audio/process`,
        {
          room_id: audioChunk.roomId,
          audio_data: audioChunk.audioData.toString('base64'),
          timestamp: audioChunk.timestamp,
          sample_rate: audioChunk.sampleRate
        }
      );
    } catch (error) {
      console.error(`[Bot ${this.botId}] Failed to send audio to backend:`, error);
    }
  }
}
