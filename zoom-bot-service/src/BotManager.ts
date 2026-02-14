/**
 * BotManager - Manages multiple Zoom bots
 */
import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import { ZoomBot } from './ZoomBot';
import { BotConfig, BotInfo, BotStatus } from './types';

export class BotManager extends EventEmitter {
  private bots: Map<string, ZoomBot> = new Map();

  constructor() {
    super();
    console.log('[BotManager] Initialized');
  }

  /**
   * Create and start a new bot
   */
  async createBot(config: BotConfig): Promise<string> {
    const botId = uuidv4();

    console.log(`[BotManager] Creating bot ${botId} for meeting ${config.meetingNumber}`);

    const bot = new ZoomBot(botId, config);

    // Set up event listeners
    this.setupBotListeners(bot, botId);

    // Store bot
    this.bots.set(botId, bot);

    // Join meeting
    try {
      await bot.join();

      // Enable audio if this is for a breakout room
      if (config.roomId) {
        await bot.enableAudio();
      }

      console.log(`[BotManager] Bot ${botId} successfully created and joined`);

      return botId;

    } catch (error) {
      console.error(`[BotManager] Failed to create bot ${botId}:`, error);
      this.bots.delete(botId);
      throw error;
    }
  }

  /**
   * Get bot by ID
   */
  getBot(botId: string): ZoomBot | undefined {
    return this.bots.get(botId);
  }

  /**
   * Get all bots
   */
  getAllBots(): BotInfo[] {
    return Array.from(this.bots.values()).map(bot => bot.getInfo());
  }

  /**
   * Get bot info by ID
   */
  getBotInfo(botId: string): BotInfo | null {
    const bot = this.bots.get(botId);
    return bot ? bot.getInfo() : null;
  }

  /**
   * Move bot to breakout room
   */
  async moveBotToBreakoutRoom(botId: string, breakoutRoomId: string): Promise<void> {
    const bot = this.bots.get(botId);
    if (!bot) {
      throw new Error(`Bot ${botId} not found`);
    }

    console.log(`[BotManager] Moving bot ${botId} to breakout room ${breakoutRoomId}`);

    await bot.joinBreakoutRoom(breakoutRoomId);
  }

  /**
   * Play audio through bot (HeyGen avatar response)
   */
  async playAudioThroughBot(botId: string, audioData: Buffer): Promise<void> {
    const bot = this.bots.get(botId);
    if (!bot) {
      throw new Error(`Bot ${botId} not found`);
    }

    await bot.playAudio(audioData);
  }

  /**
   * Stop and remove a bot
   */
  async removeBot(botId: string): Promise<void> {
    const bot = this.bots.get(botId);
    if (!bot) {
      console.warn(`[BotManager] Bot ${botId} not found`);
      return;
    }

    console.log(`[BotManager] Removing bot ${botId}`);

    try {
      await bot.leave();
    } catch (error) {
      console.error(`[BotManager] Error while removing bot ${botId}:`, error);
    }

    this.bots.delete(botId);
    this.emit('bot-removed', botId);

    console.log(`[BotManager] Bot ${botId} removed successfully`);
  }

  /**
   * Remove all bots (cleanup)
   */
  async removeAllBots(): Promise<void> {
    console.log(`[BotManager] Removing all bots (${this.bots.size})`);

    const removePromises = Array.from(this.bots.keys()).map(botId =>
      this.removeBot(botId)
    );

    await Promise.allSettled(removePromises);

    console.log('[BotManager] All bots removed');
  }

  /**
   * Get count of active bots
   */
  getActiveBotCount(): number {
    return this.bots.size;
  }

  /**
   * Get bots by status
   */
  getBotsByStatus(status: BotStatus): BotInfo[] {
    return Array.from(this.bots.values())
      .filter(bot => bot.getStatus() === status)
      .map(bot => bot.getInfo());
  }

  // ==================== Private Methods ====================

  /**
   * Set up event listeners for a bot
   */
  private setupBotListeners(bot: ZoomBot, botId: string): void {
    bot.on('status-change', (status: BotStatus) => {
      console.log(`[BotManager] Bot ${botId} status changed to ${status}`);
      this.emit('bot-status-change', { botId, status });
    });

    bot.on('joined', () => {
      console.log(`[BotManager] Bot ${botId} joined meeting`);
      this.emit('bot-joined', botId);
    });

    bot.on('joined-breakout-room', (roomId: string) => {
      console.log(`[BotManager] Bot ${botId} joined breakout room ${roomId}`);
      this.emit('bot-joined-breakout-room', { botId, roomId });
    });

    bot.on('audio-enabled', () => {
      console.log(`[BotManager] Bot ${botId} audio enabled`);
      this.emit('bot-audio-enabled', botId);
    });

    bot.on('audio-chunk', (chunk: any) => {
      // Forward audio chunks to Python backend
      this.emit('audio-chunk', { botId, ...chunk });
    });

    bot.on('error', (error: Error) => {
      console.error(`[BotManager] Bot ${botId} error:`, error);
      this.emit('bot-error', { botId, error: error.message });
    });

    bot.on('disconnected', () => {
      console.log(`[BotManager] Bot ${botId} disconnected`);
      this.emit('bot-disconnected', botId);
    });
  }
}
