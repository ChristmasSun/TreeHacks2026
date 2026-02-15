import { createClient } from '@deepgram/sdk';
import dotenv from 'dotenv';

dotenv.config();

// Initialize Deepgram client (optional - only if API key is provided)
let deepgram = null;
if (process.env.DEEPGRAM_API_KEY) {
  deepgram = createClient(process.env.DEEPGRAM_API_KEY);
  console.log('Deepgram TTS enabled');
} else {
  console.log('Deepgram TTS disabled (no API key)');
}

/**
 * Convert text to speech using Deepgram's TTS API
 * @param {string} text - The text to convert to speech
 * @param {Object} options - TTS options
 * @returns {Promise<Buffer>} - Audio buffer in the specified format
 */
export async function textToSpeech(text, options = {}) {
  if (!deepgram) {
    console.log('Deepgram not configured, skipping TTS');
    return null;
  }
  try {
    const {
      model = 'aura-asteria-en',
      encoding = 'linear16',
      sample_rate = 24000,
      container = 'wav'
    } = options;

    console.log('🎤 Converting text to speech:', text.substring(0, 50) + '...');

    const response = await deepgram.speak.request(
      { text },
      {
        model,
        encoding,
        sample_rate,
        container
      }
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
    console.log('✅ Text-to-speech conversion completed, audio size:', audioBuffer.length, 'bytes');
    
    return audioBuffer;

  } catch (error) {
    console.error('❌ Error in text-to-speech conversion:', error);
    throw error;
  }
}

/**
 * Convert text to speech and return as base64
 * @param {string} text - The text to convert to speech
 * @param {Object} options - TTS options
 * @returns {Promise<string>} - Base64 encoded audio
 */
export async function textToSpeechBase64(text, options = {}) {
  try {
    const audioBuffer = await textToSpeech(text, options);
    return audioBuffer.toString('base64');
  } catch (error) {
    console.error('❌ Error converting text to speech (base64):', error);
    throw error;
  }
}
