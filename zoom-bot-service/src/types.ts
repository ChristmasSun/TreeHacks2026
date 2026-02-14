/**
 * Type definitions for Zoom Bot Service
 */

export interface BotConfig {
  meetingNumber: string;
  passcode?: string;
  botName: string;
  roomId: number;
  heygenSessionId?: string;
  breakoutRoomId?: string;
}

export interface BotInfo {
  botId: string;
  meetingNumber: string;
  botName: string;
  roomId: number;
  status: BotStatus;
  zoomParticipantId?: string;
  heygenSessionId?: string;
  createdAt: Date;
}

export enum BotStatus {
  INITIALIZING = 'initializing',
  JOINING = 'joining',
  JOINED = 'joined',
  IN_BREAKOUT_ROOM = 'in_breakout_room',
  ERROR = 'error',
  DISCONNECTED = 'disconnected'
}

export interface AudioChunk {
  roomId: number;
  audioData: Buffer;
  timestamp: number;
  sampleRate: number;
  channels: number;
}

export interface CreateBotRequest {
  meeting_number: string;
  passcode?: string;
  bot_name: string;
  room_id: number;
  heygen_session_id?: string;
}

export interface CreateBotResponse {
  bot_id: string;
  status: BotStatus;
  message: string;
}
