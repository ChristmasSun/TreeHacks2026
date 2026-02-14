/**
 * HTTP API Server for Zoom Bot Service
 * Provides REST API for Python backend to control bots
 */
import express, { Request, Response } from 'express';
import cors from 'cors';
import { BotManager } from './BotManager';
import { CreateBotRequest, CreateBotResponse, BotStatus } from './types';

export function createServer(botManager: BotManager) {
  const app = express();

  // Middleware
  app.use(cors());
  app.use(express.json({ limit: '10mb' })); // For audio data

  // Health check
  app.get('/health', (req: Request, res: Response) => {
    res.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      active_bots: botManager.getActiveBotCount()
    });
  });

  // ==================== Bot Management ====================

  /**
   * POST /bots/create
   * Create a new bot and join meeting
   */
  app.post('/bots/create', async (req: Request, res: Response) => {
    try {
      const request: CreateBotRequest = req.body;

      // Validate request
      if (!request.meeting_number || !request.bot_name || request.room_id === undefined) {
        return res.status(400).json({
          error: 'Missing required fields: meeting_number, bot_name, room_id'
        });
      }

      console.log(`[API] Creating bot for meeting ${request.meeting_number}`);

      // Create bot
      const botId = await botManager.createBot({
        meetingNumber: request.meeting_number,
        passcode: request.passcode,
        botName: request.bot_name,
        roomId: request.room_id,
        heygenSessionId: request.heygen_session_id
      });

      const response: CreateBotResponse = {
        bot_id: botId,
        status: BotStatus.JOINED,
        message: 'Bot created and joined meeting successfully'
      };

      res.status(201).json(response);

    } catch (error: any) {
      console.error('[API] Error creating bot:', error);
      res.status(500).json({
        error: 'Failed to create bot',
        message: error.message
      });
    }
  });

  /**
   * GET /bots
   * Get all bots
   */
  app.get('/bots', (req: Request, res: Response) => {
    const bots = botManager.getAllBots();
    res.json({
      bots,
      count: bots.length
    });
  });

  /**
   * GET /bots/:bot_id
   * Get bot info
   */
  app.get('/bots/:bot_id', (req: Request, res: Response) => {
    const botId = req.params.bot_id;
    const botInfo = botManager.getBotInfo(botId);

    if (!botInfo) {
      return res.status(404).json({
        error: 'Bot not found'
      });
    }

    res.json(botInfo);
  });

  /**
   * POST /bots/:bot_id/join-breakout-room
   * Move bot to breakout room
   */
  app.post('/bots/:bot_id/join-breakout-room', async (req: Request, res: Response) => {
    try {
      const botId = req.params.bot_id;
      const { breakout_room_id } = req.body;

      if (!breakout_room_id) {
        return res.status(400).json({
          error: 'Missing required field: breakout_room_id'
        });
      }

      await botManager.moveBotToBreakoutRoom(botId, breakout_room_id);

      res.json({
        message: 'Bot moved to breakout room successfully',
        bot_id: botId,
        breakout_room_id
      });

    } catch (error: any) {
      console.error('[API] Error moving bot to breakout room:', error);
      res.status(500).json({
        error: 'Failed to move bot to breakout room',
        message: error.message
      });
    }
  });

  /**
   * POST /bots/:bot_id/play-audio
   * Play audio through bot (HeyGen avatar response)
   */
  app.post('/bots/:bot_id/play-audio', async (req: Request, res: Response) => {
    try {
      const botId = req.params.bot_id;
      const { audio_data } = req.body; // base64 encoded

      if (!audio_data) {
        return res.status(400).json({
          error: 'Missing required field: audio_data'
        });
      }

      // Decode base64 audio
      const audioBuffer = Buffer.from(audio_data, 'base64');

      await botManager.playAudioThroughBot(botId, audioBuffer);

      res.json({
        message: 'Audio queued for playback',
        bytes_received: audioBuffer.length
      });

    } catch (error: any) {
      console.error('[API] Error playing audio:', error);
      res.status(500).json({
        error: 'Failed to play audio',
        message: error.message
      });
    }
  });

  /**
   * DELETE /bots/:bot_id
   * Stop and remove bot
   */
  app.delete('/bots/:bot_id', async (req: Request, res: Response) => {
    try {
      const botId = req.params.bot_id;

      await botManager.removeBot(botId);

      res.json({
        message: 'Bot removed successfully',
        bot_id: botId
      });

    } catch (error: any) {
      console.error('[API] Error removing bot:', error);
      res.status(500).json({
        error: 'Failed to remove bot',
        message: error.message
      });
    }
  });

  /**
   * DELETE /bots
   * Remove all bots (cleanup)
   */
  app.delete('/bots', async (req: Request, res: Response) => {
    try {
      await botManager.removeAllBots();

      res.json({
        message: 'All bots removed successfully'
      });

    } catch (error: any) {
      console.error('[API] Error removing all bots:', error);
      res.status(500).json({
        error: 'Failed to remove all bots',
        message: error.message
      });
    }
  });

  // ==================== Utilities ====================

  /**
   * POST /generate-signature
   * Generate Zoom SDK signature for testing
   */
  app.post('/generate-signature', (req: Request, res: Response) => {
    const { meetingNumber, role } = req.body;

    if (!meetingNumber) {
      return res.status(400).json({ error: 'Missing meetingNumber' });
    }

    const { generateJWT } = require('./utils/signature');
    const signature = generateJWT(
      process.env.ZOOM_SDK_KEY!,
      process.env.ZOOM_SDK_SECRET!,
      meetingNumber,
      role || 0
    );

    res.json({ signature });
  });

  /**
   * POST /test-auto
   * Automated test: Creates a meeting and joins it
   */
  app.post('/test-auto', async (req: Request, res: Response) => {
    try {
      const axios = require('axios');

      // Check OAuth credentials
      if (!process.env.ZOOM_ACCOUNT_ID || !process.env.ZOOM_CLIENT_ID || !process.env.ZOOM_CLIENT_SECRET) {
        return res.status(400).json({
          error: 'Missing OAuth credentials',
          setup_instructions: {
            step1: 'Go to https://marketplace.zoom.us/develop/create',
            step2: 'Create a Server-to-Server OAuth app',
            step3: 'Add scopes: meeting:write, meeting:read',
            step4: 'Add to .env: ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET'
          }
        });
      }

      // Get OAuth token
      const authString = Buffer.from(`${process.env.ZOOM_CLIENT_ID}:${process.env.ZOOM_CLIENT_SECRET}`).toString('base64');
      const tokenResponse = await axios.post(
        `https://zoom.us/oauth/token?grant_type=account_credentials&account_id=${process.env.ZOOM_ACCOUNT_ID}`,
        {},
        { headers: { 'Authorization': `Basic ${authString}` } }
      );

      const accessToken = tokenResponse.data.access_token;

      // Create meeting
      const meetingResponse = await axios.post(
        'https://api.zoom.us/v2/users/me/meetings',
        {
          topic: 'Bot Auto-Test Meeting',
          type: 1,
          settings: {
            join_before_host: true,
            waiting_room: false,
            mute_upon_entry: false
          }
        },
        { headers: { 'Authorization': `Bearer ${accessToken}` } }
      );

      const meeting = {
        id: meetingResponse.data.id.toString(),
        password: meetingResponse.data.password,
        join_url: meetingResponse.data.join_url
      };

      // Create bot to join
      const botId = await botManager.createBot({
        meetingNumber: meeting.id,
        passcode: meeting.password,
        botName: 'Auto-Test Bot',
        roomId: 0
      });

      res.json({
        message: 'Auto-test started',
        meeting,
        bot_id: botId,
        status: 'Check /bots/' + botId + ' for status'
      });

    } catch (error: any) {
      console.error('[API] Auto-test error:', error);
      res.status(500).json({
        error: 'Auto-test failed',
        message: error.message,
        details: error.response?.data
      });
    }
  });

  // ==================== Statistics ====================

  /**
   * GET /stats
   * Get service statistics
   */
  app.get('/stats', (req: Request, res: Response) => {
    const allBots = botManager.getAllBots();

    const stats = {
      total_bots: allBots.length,
      by_status: {
        initializing: botManager.getBotsByStatus(BotStatus.INITIALIZING).length,
        joining: botManager.getBotsByStatus(BotStatus.JOINING).length,
        joined: botManager.getBotsByStatus(BotStatus.JOINED).length,
        in_breakout_room: botManager.getBotsByStatus(BotStatus.IN_BREAKOUT_ROOM).length,
        error: botManager.getBotsByStatus(BotStatus.ERROR).length,
        disconnected: botManager.getBotsByStatus(BotStatus.DISCONNECTED).length
      },
      uptime_seconds: process.uptime(),
      memory_usage: process.memoryUsage()
    };

    res.json(stats);
  });

  // Error handling
  app.use((err: Error, req: Request, res: Response, next: any) => {
    console.error('[API] Unhandled error:', err);
    res.status(500).json({
      error: 'Internal server error',
      message: err.message
    });
  });

  return app;
}
