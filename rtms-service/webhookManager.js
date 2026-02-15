/**
 * WebhookManager - Handles Zoom RTMS webhooks
 */
import express from 'express';
import crypto from 'crypto';
import { EventEmitter } from 'events';

export class WebhookManager extends EventEmitter {
  constructor(options = {}) {
    super();
    this.config = options.config || {};
    this.app = options.app || null;
  }

  setup() {
    if (!this.app) {
      console.warn('[WebhookManager] No Express app provided');
      return;
    }

    this.app.use(express.json());

    this.app.post(this.config.webhookPath, this.handleWebhook.bind(this));
    console.log(`[WebhookManager] Webhook route set up at ${this.config.webhookPath}`);
  }

  async handleWebhook(req, res) {
    const { event, payload } = req.body;
    console.log('[WebhookManager] Received event:', event);

    // Handle Zoom webhook validation
    if (event === 'endpoint.url_validation' && payload?.plainToken) {
      const hash = crypto
        .createHmac('sha256', this.config.zoomSecretToken)
        .update(payload.plainToken)
        .digest('hex');

      return res.json({
        plainToken: payload.plainToken,
        encryptedToken: hash
      });
    }

    // Respond immediately (important for Zoom webhooks!)
    res.sendStatus(200);

    // Log important RTMS events
    if (event?.includes('rtms')) {
      console.log('[WebhookManager] RTMS event:', event, JSON.stringify(payload, null, 2));
    }

    // Emit event for processing
    this.emit('event', event, payload);
  }
}

export default WebhookManager;
