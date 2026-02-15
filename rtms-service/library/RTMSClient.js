/**
 * RTMSClient - Simplified RTMS WebSocket client
 * Handles signaling and media WebSocket connections for Zoom RTMS
 */
import { EventEmitter } from 'events';
import WebSocket from 'ws';
import crypto from 'crypto';

// Media type constants
export const MEDIA_TYPES = {
  AUDIO: 1,
  VIDEO: 2,
  SHARESCREEN: 4,
  TRANSCRIPT: 8,
  CHAT: 16,
  ALL: 32
};

// Default media params for transcription
export const MEDIA_PARAMS = {
  MEDIA_CONTENT_TYPE_RAW: 1,
  MEDIA_CONTENT_TYPE_RTP: 2,
  MEDIA_CONTENT_TYPE_TEXT: 3,
  AUDIO_SAMPLE_RATE_SR_8K: 0,
  AUDIO_SAMPLE_RATE_SR_16K: 1,
  AUDIO_SAMPLE_RATE_SR_24K: 2,
  AUDIO_SAMPLE_RATE_SR_32K: 3,
  AUDIO_SAMPLE_RATE_SR_44K: 4,
  AUDIO_SAMPLE_RATE_SR_48K: 5,
  AUDIO_CHANNEL_MONO: 1,
  AUDIO_CHANNEL_STEREO: 2,
  MEDIA_PAYLOAD_TYPE_L16: 1,
  MEDIA_PAYLOAD_TYPE_PCMU: 2,
  MEDIA_PAYLOAD_TYPE_PCMA: 3,
  MEDIA_DATA_OPTION_AUDIO_MIXED_STREAM: 1,
  MEDIA_DATA_OPTION_AUDIO_MULTI_STREAM: 2,
  LANGUAGE_ID_ENGLISH: 0,
  LANGUAGE_ID_CHINESE: 1,
  LANGUAGE_ID_JAPANESE: 2,
  LANGUAGE_ID_GERMAN: 3,
  LANGUAGE_ID_FRENCH: 4,
  LANGUAGE_ID_RUSSIAN: 5,
  LANGUAGE_ID_PORTUGUESE: 6,
  LANGUAGE_ID_SPANISH: 7,
  LANGUAGE_ID_KOREAN: 8,
};

export class RTMSClient extends EventEmitter {
  constructor(options = {}) {
    super();
    this.meetingUuid = options.meetingUuid;
    this.streamId = options.streamId;
    this.serverUrls = options.serverUrls;
    this.clientId = options.clientId;
    this.clientSecret = options.clientSecret;
    this.mediaTypes = options.mediaTypes || (MEDIA_TYPES.AUDIO | MEDIA_TYPES.TRANSCRIPT);
    this.mediaParams = options.mediaParams || this.getDefaultMediaParams();

    this.signalingWs = null;
    this.mediaWs = null;
    this.state = 'initialized';
    this.keepAliveInterval = null;
  }

  getDefaultMediaParams() {
    return {
      audio: {
        content_type: MEDIA_PARAMS.MEDIA_CONTENT_TYPE_RTP,
        sample_rate: MEDIA_PARAMS.AUDIO_SAMPLE_RATE_SR_16K,
        channel: MEDIA_PARAMS.AUDIO_CHANNEL_MONO,
        codec: MEDIA_PARAMS.MEDIA_PAYLOAD_TYPE_L16,
        data_opt: MEDIA_PARAMS.MEDIA_DATA_OPTION_AUDIO_MIXED_STREAM,
        send_rate: 100
      },
      transcript: {
        content_type: MEDIA_PARAMS.MEDIA_CONTENT_TYPE_TEXT,
        language: MEDIA_PARAMS.LANGUAGE_ID_ENGLISH
      }
    };
  }

  generateSignature() {
    const message = `${this.clientId},${this.meetingUuid},${this.streamId}`;
    return crypto.createHmac('sha256', this.clientSecret).update(message).digest('hex');
  }

  async connect() {
    console.log(`[RTMSClient] Connecting to RTMS for meeting ${this.meetingUuid}`);

    return new Promise((resolve, reject) => {
      try {
        // Connect to signaling WebSocket
        this.signalingWs = new WebSocket(this.serverUrls);

        this.signalingWs.on('open', () => {
          console.log('[RTMSClient] Signaling WebSocket connected');
          this.state = 'signaling_connected';

          // Send handshake
          const signature = this.generateSignature();
          const handshake = {
            msg_type: 1, // SIGNALING_HAND_SHAKE_REQ
            protocol_version: 1,
            meeting_uuid: this.meetingUuid,
            rtms_stream_id: this.streamId,
            signature: signature,
            media_type: this.mediaTypes,
            payload_encryption: true
          };

          console.log('[RTMSClient] Sending signaling handshake');
          this.signalingWs.send(JSON.stringify(handshake));
        });

        this.signalingWs.on('message', (data) => {
          this.handleSignalingMessage(data, resolve, reject);
        });

        this.signalingWs.on('error', (error) => {
          console.error('[RTMSClient] Signaling WebSocket error:', error);
          this.emit('error', error);
          reject(error);
        });

        this.signalingWs.on('close', () => {
          console.log('[RTMSClient] Signaling WebSocket closed');
          this.state = 'disconnected';
          this.emit('disconnected');
        });

      } catch (error) {
        console.error('[RTMSClient] Connection error:', error);
        reject(error);
      }
    });
  }

  handleSignalingMessage(data, resolve, reject) {
    try {
      const msg = JSON.parse(data.toString());
      console.log('[RTMSClient] Signaling message type:', msg.msg_type);

      switch (msg.msg_type) {
        case 2: // SIGNALING_HAND_SHAKE_RESP
          if (msg.status_code === 0) {
            console.log('[RTMSClient] Signaling handshake successful');
            // Connect to media WebSocket
            if (msg.media_server?.server_urls) {
              this.connectToMedia(msg.media_server.server_urls, resolve, reject);
            }
          } else {
            console.error('[RTMSClient] Signaling handshake failed:', msg.reason);
            reject(new Error(`Signaling handshake failed: ${msg.reason}`));
          }
          break;

        case 6: // KEEP_ALIVE_REQ
          this.signalingWs.send(JSON.stringify({
            msg_type: 7, // KEEP_ALIVE_RESP
            timestamp: msg.timestamp
          }));
          break;

        case 8: // STREAM_STATE_UPDATE
          console.log('[RTMSClient] Stream state update:', msg);
          this.emit('stream_state', msg);
          break;

        default:
          console.log('[RTMSClient] Unknown signaling message:', msg.msg_type);
      }
    } catch (error) {
      console.error('[RTMSClient] Error parsing signaling message:', error);
    }
  }

  connectToMedia(mediaServerUrl, resolve, reject) {
    console.log('[RTMSClient] Connecting to media server:', mediaServerUrl);

    this.mediaWs = new WebSocket(mediaServerUrl);

    this.mediaWs.on('open', () => {
      console.log('[RTMSClient] Media WebSocket connected');
      this.state = 'media_connected';

      // Send media handshake
      const mediaHandshake = {
        msg_type: 3, // DATA_HAND_SHAKE_REQ
        protocol_version: 1,
        meeting_uuid: this.meetingUuid,
        rtms_stream_id: this.streamId,
        signature: this.generateSignature(),
        media_type: this.mediaTypes,
        payload_encryption: true,
        media_params: this.mediaParams
      };

      console.log('[RTMSClient] Sending media handshake');
      this.mediaWs.send(JSON.stringify(mediaHandshake));
    });

    this.mediaWs.on('message', (data) => {
      this.handleMediaMessage(data, resolve);
    });

    this.mediaWs.on('error', (error) => {
      console.error('[RTMSClient] Media WebSocket error:', error);
      this.emit('error', error);
    });

    this.mediaWs.on('close', () => {
      console.log('[RTMSClient] Media WebSocket closed');
      this.cleanup();
    });
  }

  handleMediaMessage(data, resolve) {
    try {
      const msg = JSON.parse(data.toString());

      switch (msg.msg_type) {
        case 4: // DATA_HAND_SHAKE_RESP
          if (msg.status_code === 0) {
            console.log('[RTMSClient] Media handshake successful - streaming!');
            this.state = 'streaming';

            // Confirm stream ready
            this.signalingWs.send(JSON.stringify({
              msg_type: 7, // MEDIA_DATA_RCV_START
              rtms_stream_id: this.streamId
            }));

            this.emit('connected');
            if (resolve) resolve();
          } else {
            console.error('[RTMSClient] Media handshake failed:', msg.reason);
          }
          break;

        case 12: // KEEP_ALIVE_REQ
          this.mediaWs.send(JSON.stringify({
            msg_type: 13, // KEEP_ALIVE_RESP
            timestamp: msg.timestamp
          }));
          break;

        case 14: // AUDIO
          if (msg.content?.data) {
            const audioBuffer = Buffer.from(msg.content.data, 'base64');
            this.emit('audio', {
              userId: msg.content.user_id,
              userName: msg.content.user_name || 'Unknown',
              data: audioBuffer,
              timestamp: msg.content.timestamp
            });
          }
          break;

        case 17: // TRANSCRIPT
          if (msg.content?.data) {
            console.log(`[RTMSClient] Transcript: ${msg.content.user_name}: ${msg.content.data}`);
            this.emit('transcript', {
              userId: msg.content.user_id,
              userName: msg.content.user_name || 'Unknown',
              text: msg.content.data,
              timestamp: msg.content.timestamp
            });
          }
          break;

        case 18: // CHAT
          if (msg.content?.data) {
            this.emit('chat', {
              userId: msg.content.user_id,
              userName: msg.content.user_name || 'Unknown',
              text: msg.content.data,
              timestamp: msg.content.timestamp
            });
          }
          break;

        default:
          // Ignore other message types
          break;
      }
    } catch (error) {
      console.error('[RTMSClient] Error parsing media message:', error);
    }
  }

  disconnect() {
    console.log('[RTMSClient] Disconnecting...');
    this.cleanup();
  }

  cleanup() {
    if (this.keepAliveInterval) {
      clearInterval(this.keepAliveInterval);
      this.keepAliveInterval = null;
    }

    if (this.mediaWs) {
      this.mediaWs.close();
      this.mediaWs = null;
    }

    if (this.signalingWs) {
      this.signalingWs.close();
      this.signalingWs = null;
    }

    this.state = 'disconnected';
  }
}

export default RTMSClient;
