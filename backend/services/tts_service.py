"""
Text-to-Speech Service
Supports OpenAI TTS and ElevenLabs (add your cloned voice)
"""
import os
import logging
import base64
import uuid
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

# Audio storage (in production, use S3/cloud storage)
AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)


async def text_to_speech(
    text: str,
    voice_id: Optional[str] = None,
    provider: str = "openai"  # "openai" or "elevenlabs"
) -> dict:
    """
    Convert text to speech audio file
    
    Args:
        text: Text to convert to speech
        voice_id: Voice ID (for OpenAI: alloy, echo, fable, onyx, nova, shimmer)
                  (for ElevenLabs: your cloned voice ID)
        provider: TTS provider to use
    
    Returns:
        dict with audio_url and audio_base64
    """
    if provider == "elevenlabs":
        return await elevenlabs_tts(text, voice_id)
    else:
        return await openai_tts(text, voice_id)


async def openai_tts(text: str, voice: Optional[str] = None) -> dict:
    """Generate speech using OpenAI TTS"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    
    voice = voice or "nova"  # Default to nova (friendly female voice)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "tts-1",
                "input": text,
                "voice": voice,
                "response_format": "mp3"
            }
        )
        response.raise_for_status()
        
        # Save audio file
        audio_id = str(uuid.uuid4())
        audio_path = os.path.join(AUDIO_DIR, f"{audio_id}.mp3")
        
        with open(audio_path, "wb") as f:
            f.write(response.content)
        
        # Return both URL and base64
        audio_base64 = base64.b64encode(response.content).decode("utf-8")
        
        logger.info(f"Generated OpenAI TTS audio: {audio_id}")
        
        return {
            "audio_id": audio_id,
            "audio_url": f"/static/audio/{audio_id}.mp3",
            "audio_base64": audio_base64,
            "content_type": "audio/mpeg"
        }


async def elevenlabs_tts(text: str, voice_id: Optional[str] = None) -> dict:
    """
    Generate speech using ElevenLabs (supports cloned voices)
    
    To use your cloned voice:
    1. Go to elevenlabs.io and create an Instant Voice Clone
    2. Copy the voice ID 
    3. Set ELEVENLABS_VOICE_ID env var or pass it here
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not set")
    
    # Use provided voice_id, env var, or default
    voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM"  # Rachel default
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json"
            },
            json={
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
        )
        response.raise_for_status()
        
        # Save audio file
        audio_id = str(uuid.uuid4())
        audio_path = os.path.join(AUDIO_DIR, f"{audio_id}.mp3")
        
        with open(audio_path, "wb") as f:
            f.write(response.content)
        
        audio_base64 = base64.b64encode(response.content).decode("utf-8")
        
        logger.info(f"Generated ElevenLabs TTS audio: {audio_id}")
        
        return {
            "audio_id": audio_id,
            "audio_url": f"/static/audio/{audio_id}.mp3",
            "audio_base64": audio_base64,
            "content_type": "audio/mpeg"
        }
