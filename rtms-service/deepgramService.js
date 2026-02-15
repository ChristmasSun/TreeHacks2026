/**
 * Deepgram TTS Service
 * Converts text to speech using Deepgram's API
 */
import { createClient } from '@deepgram/sdk';
import dotenv from 'dotenv';

dotenv.config();

let deepgram = null;

// Initialize Deepgram client lazily
function getClient() {
  if (!deepgram && process.env.DEEPGRAM_API_KEY) {
    deepgram = createClient(process.env.DEEPGRAM_API_KEY);
  }
  return deepgram;
}

/**
 * Convert text to speech using Deepgram's TTS API
 * @param {string} text - The text to convert to speech
 * @param {Object} options - TTS options
 * @returns {Promise<Buffer>} - Audio buffer
 */
export async function textToSpeech(text, options = {}) {
  const client = getClient();
  if (!client) {
    throw new Error('Deepgram API key not configured');
  }

  try {
    const {
      model = 'aura-asteria-en',
      encoding = 'linear16',
      sample_rate = 24000,
      container = 'wav'
    } = options;

    console.log('[Deepgram] Converting text to speech:', text.substring(0, 50) + '...');

    const response = await client.speak.request(
      { text },
      { model, encoding, sample_rate, container }
    );

    const stream = await response.getStream();
    if (!stream) {
      throw new Error('No audio stream received from Deepgram');
    }

    // Convert stream to buffer
    const chunks = [];
    const reader = stream.getReader();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
    }

    const audioBuffer = Buffer.concat(chunks);
    console.log('[Deepgram] TTS completed, audio size:', audioBuffer.length, 'bytes');

    return audioBuffer;
  } catch (error) {
    console.error('[Deepgram] TTS error:', error);
    throw error;
  }
}

/**
 * Convert text to speech and return as base64
 * @param {string} text - The text to convert
 * @param {Object} options - TTS options
 * @returns {Promise<string>} - Base64 encoded audio
 */
export async function textToSpeechBase64(text, options = {}) {
  const audioBuffer = await textToSpeech(text, options);
  return audioBuffer.toString('base64');
}

export default { textToSpeech, textToSpeechBase64 };
