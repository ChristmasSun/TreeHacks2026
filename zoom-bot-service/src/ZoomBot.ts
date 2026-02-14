/**
 * ZoomBot - Individual bot that joins Zoom meetings
 * Uses Puppeteer + Zoom Web SDK for headless meeting participation
 */
import { EventEmitter } from 'events';
import puppeteer, { Browser, Page } from 'puppeteer';
import path from 'path';
import { BotConfig, BotStatus, AudioChunk } from './types';
import { generateJWT } from './utils/signature';
import axios from 'axios';

export class ZoomBot extends EventEmitter {
  private botId: string;
  private config: BotConfig;
  private status: BotStatus;
  private zoomParticipantId?: string;
  private audioEnabled: boolean = false;
  private createdAt: Date;

  // Puppeteer browser and page
  private browser: Browser | null = null;
  private page: Page | null = null;

  constructor(botId: string, config: BotConfig) {
    super();
    this.botId = botId;
    this.config = config;
    this.status = BotStatus.INITIALIZING;
    this.createdAt = new Date();
  }

  /**
   * Join Zoom meeting using Puppeteer + Web SDK
   */
  async join(): Promise<void> {
    try {
      this.status = BotStatus.JOINING;
      this.emit('status-change', this.status);

      console.log(`[Bot ${this.botId}] Joining meeting ${this.config.meetingNumber}`);

      // Generate JWT signature
      const signature = generateJWT(
        process.env.ZOOM_SDK_KEY!,
        process.env.ZOOM_SDK_SECRET!,
        this.config.meetingNumber,
        0
      );

      // Launch headless browser
      console.log(`[Bot ${this.botId}] Launching Puppeteer...`);
      this.browser = await puppeteer.launch({
        headless: true,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-accelerated-2d-canvas',
          '--no-first-run',
          '--no-zygote',
          '--disable-gpu',
          '--use-fake-ui-for-media-stream', // Auto-allow media permissions
          '--use-fake-device-for-media-stream', // Use fake camera/mic
        ]
      });

      this.page = await this.browser.newPage();

      // Set viewport
      await this.page.setViewport({ width: 1280, height: 720 });

      // Enable console logging from browser
      this.page.on('console', (msg) => {
        const text = msg.text();
        if (text.startsWith('[Bot]')) {
          console.log(`[Bot ${this.botId}] ${text}`);
        }
      });

      // Load Zoom bot HTML page
      const htmlPath = path.join(__dirname, '../public/zoom-bot.html');
      await this.page.goto(`file://${htmlPath}`, {
        waitUntil: 'networkidle0'
      });

      console.log(`[Bot ${this.botId}] HTML loaded, joining meeting...`);

      // Join meeting via page script
      await this.page.evaluate((joinConfig) => {
        return (window as any).joinMeeting(joinConfig);
      }, {
        signature,
        sdkKey: process.env.ZOOM_SDK_KEY,
        meetingNumber: this.config.meetingNumber,
        userName: this.config.botName,
        password: this.config.passcode || ''
      });

      // Wait for join to complete
      await this.waitForBotStatus('joined', 30000);

      // Get participant ID
      const botState = await this.page.evaluate(() => (window as any).botState);
      this.zoomParticipantId = botState.participantId;

      this.status = BotStatus.JOINED;
      this.emit('status-change', this.status);
      this.emit('joined');

      console.log(`[Bot ${this.botId}] Successfully joined meeting`);

    } catch (error) {
      console.error(`[Bot ${this.botId}] Failed to join:`, error);
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

      if (!this.page) {
        throw new Error('Bot not connected to Zoom');
      }

      const result = await this.page.evaluate((roomId) => {
        return (window as any).joinBreakoutRoom(roomId);
      }, breakoutRoomId);

      if (!result.success) {
        throw new Error(result.error);
      }

      this.status = BotStatus.IN_BREAKOUT_ROOM;
      this.emit('status-change', this.status);
      this.emit('joined-breakout-room', breakoutRoomId);

      console.log(`[Bot ${this.botId}] Successfully joined breakout room`);

    } catch (error) {
      console.error(`[Bot ${this.botId}] Failed to join breakout room:`, error);
      this.emit('error', error);
      throw error;
    }
  }

  /**
   * Enable audio capture and streaming
   */
  async enableAudio(): Promise<void> {
    if (this.audioEnabled) return;

    console.log(`[Bot ${this.botId}] Enabling audio`);

    if (!this.page) {
      throw new Error('Bot not connected to Zoom');
    }

    // Unmute in Zoom
    const unmuteResult = await this.page.evaluate(() => {
      return (window as any).enableAudio();
    });

    if (!unmuteResult.success) {
      throw new Error(unmuteResult.error);
    }

    // Start audio capture
    const captureResult = await this.page.evaluate(() => {
      return (window as any).startAudioCapture();
    });

    if (!captureResult.success) {
      throw new Error(captureResult.error);
    }

    this.audioEnabled = true;
    this.emit('audio-enabled');

    // Start polling for audio chunks
    this.startAudioCapture();
  }

  /**
   * Play audio in Zoom (for HeyGen avatar responses)
   */
  async playAudio(audioData: Buffer): Promise<void> {
    if (!this.audioEnabled) {
      console.warn(`[Bot ${this.botId}] Audio not enabled, cannot play`);
      return;
    }

    if (!this.page) {
      throw new Error('Bot not connected to Zoom');
    }

    console.log(`[Bot ${this.botId}] Playing audio chunk (${audioData.length} bytes)`);

    const audioB64 = audioData.toString('base64');

    const result = await this.page.evaluate((audioBase64) => {
      return (window as any).playAudioData(audioBase64);
    }, audioB64);

    if (!result.success) {
      throw new Error(`Audio playback failed: ${result.error}`);
    }
  }

  /**
   * Leave meeting and cleanup
   */
  async leave(): Promise<void> {
    console.log(`[Bot ${this.botId}] Leaving meeting`);

    try {
      // Stop audio capture first
      if (this.page && this.audioEnabled) {
        await this.page.evaluate(() => {
          (window as any).stopAudioCapture();
        });
        this.audioEnabled = false;
      }

      if (this.page) {
        await this.page.evaluate(() => {
          return (window as any).leaveMeeting();
        });

        await this.page.close();
        this.page = null;
      }

      if (this.browser) {
        await this.browser.close();
        this.browser = null;
      }

      this.status = BotStatus.DISCONNECTED;
      this.emit('status-change', this.status);
      this.emit('disconnected');

      console.log(`[Bot ${this.botId}] Left meeting successfully`);

    } catch (error) {
      console.error(`[Bot ${this.botId}] Error during leave:`, error);
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
      heygenSessionId: this.config.heygenSessionId,
      createdAt: this.createdAt
    };
  }

  // ==================== Private Methods ====================

  /**
   * Wait for bot to reach specific status
   */
  private async waitForBotStatus(targetStatus: string, timeout: number): Promise<void> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      if (!this.page) {
        throw new Error('Page closed while waiting for status');
      }

      const botState = await this.page.evaluate(() => (window as any).botState);

      if (botState.status === targetStatus) {
        return;
      }

      if (botState.status === 'error') {
        throw new Error(`Bot error: ${botState.error}`);
      }

      await new Promise(resolve => setTimeout(resolve, 500));
    }

    throw new Error(`Timeout waiting for status: ${targetStatus}`);
  }

  /**
   * Start capturing audio from Zoom and emitting chunks
   */
  private startAudioCapture(): void {
    const pollInterval = setInterval(async () => {
      if (!this.audioEnabled || this.status === BotStatus.DISCONNECTED || !this.page) {
        clearInterval(pollInterval);
        return;
      }

      try {
        // Get audio chunks from page
        const chunks = await this.page.evaluate(() => {
          return (window as any).getAudioChunks();
        });

        // Process each chunk
        for (const chunk of chunks) {
          const audioBuffer = Buffer.from(chunk.data, 'base64');

          const audioChunk: AudioChunk = {
            roomId: this.config.roomId,
            audioData: audioBuffer,
            timestamp: chunk.timestamp,
            sampleRate: 16000,
            channels: 1
          };

          // Emit for transcription
          this.emit('audio-chunk', audioChunk);

          // Send to Python backend
          await this.sendAudioToBackend(audioChunk);
        }
      } catch (error) {
        console.error(`[Bot ${this.botId}] Audio capture error:`, error);
      }
    }, 1000); // Poll every second for real-time processing
  }

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
