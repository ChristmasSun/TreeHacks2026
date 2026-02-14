/**
 * WebSocket client for Python backend communication
 */
import WebSocket from 'ws';
import { EventEmitter } from 'events';

export class WebSocketClient extends EventEmitter {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectInterval: number = 5000;
  private reconnectTimeout: NodeJS.Timeout | null = null;

  constructor(url: string) {
    super();
    this.url = url;
  }

  connect() {
    console.log(`Connecting to backend: ${this.url}`);

    this.ws = new WebSocket(this.url);

    this.ws.on('open', () => {
      console.log('WebSocket connected to backend');
      this.emit('connected');

      // Clear any pending reconnect
      if (this.reconnectTimeout) {
        clearTimeout(this.reconnectTimeout);
        this.reconnectTimeout = null;
      }

      // Send ping to confirm connection
      this.send('PING', {});
    });

    this.ws.on('message', (data: WebSocket.Data) => {
      try {
        const message = JSON.parse(data.toString());
        console.log('Received from backend:', message.type);
        this.emit('message', message);
      } catch (error) {
        console.error('Failed to parse message:', error);
      }
    });

    this.ws.on('close', () => {
      console.log('WebSocket disconnected');
      this.emit('disconnected');
      this.scheduleReconnect();
    });

    this.ws.on('error', (error) => {
      console.error('WebSocket error:', error);
      this.emit('error', error);
    });
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(type: string, payload: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = { type, payload };
      this.ws.send(JSON.stringify(message));
      console.log('Sent to backend:', type);
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout) {
      return; // Already scheduled
    }

    console.log(`Reconnecting in ${this.reconnectInterval}ms...`);
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectTimeout = null;
      this.connect();
    }, this.reconnectInterval);
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}
