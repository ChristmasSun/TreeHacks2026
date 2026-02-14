Fair enough, let me dig into what's actually dropped recently.Alright, here's a much more current picture of what's actually shipping and worth looking at:

---

## The Big Recent Drops (late 2025 – Feb 2026)

**Kyutai Pocket TTS** (January 2026) — A 100M-parameter TTS model that runs in real-time on laptop CPUs without GPU acceleration. Generates audio at 6x real-time speed on a MacBook Air M4 using two CPU cores, with voice cloning from 5 seconds of audio. The key technical innovation is **CALM (Continuous Audio Language Models)** — instead of converting audio to discrete tokens (lossy, expensive), it predicts continuous audio representations directly, eliminating the computational bottleneck that made previous TTS models GPU-dependent. It replaces diffusion with a consistency model that maps noisy inputs to clean outputs in one step. Install is literally `pip install pocket-tts`. This is probably the most exciting thing to drop recently if you care about local/edge deployment — would run great on your M4 Pro.

**Nari Labs Dia2** (Nov 2025) — A streaming dialogue TTS model that doesn't need the entire text to produce audio — it starts generating from the first few words. 1B and 2B checkpoints, English only, up to 2 minutes of generation. Features streaming generation suitable for real-time conversational agents and speech-to-speech pipelines, with emotion/tone control via nonverbal tags like (laughs), (coughs), (gasps). Apache 2.0 licensed. Built by two undergrad students with zero funding. ~10GB VRAM.

**Microsoft VibeVoice family** — This has been rolling out in waves:
- VibeVoice-TTS (Aug 2025): Long-form multi-speaker TTS, up to 90 minutes with 4 speakers. 1.5B and 7B variants. Uses ultra-low 7.5Hz tokenizers + next-token diffusion. Microsoft pulled the code briefly due to misuse concerns, but a community fork preserved it and added fine-tuning support.
- VibeVoice-Realtime-0.5B (Dec 2025): Real-time streaming TTS with experimental multilingual voices in 9 languages.
- VibeVoice-ASR (Jan 2026): 60-minute single-pass speech-to-text with speaker diarization and timestamps.

**NeuTTS Air** (Neuphonic) — The first on-device, super-realistic TTS model with instant voice cloning. 0.5B-parameter LLM backbone, distributed in GGUF/GGML format for consumer hardware. Clones from as little as 3 seconds of reference audio. English-only for now. All generated audio includes imperceptible watermarks.

**Fish Audio S1 / S1-mini** — S1 is a 4B TTS model with RLHF training that jointly models semantic and acoustic information. S1-mini is a 0.5B distilled open-source version. The emotion tag system (inject `(excited)`, `(whisper)`, etc.) is still unique. 10-15 seconds of reference audio for cloning.

**Sesame CSM-1B** (March 2025) — Still very relevant. An end-to-end conversational speech model that processes text and audio context together, producing natural pauses, "ums," chuckles, and tone changes on the fly. They trained 1B, 3B, and 8B variants but only open-sourced the 1B. The demos (Maya and Miles voices) are still some of the most human-sounding voice AI out there. Apache 2.0.

**Kokoro** — Just 82M parameters, Apache 2.0, runs on modest hardware. Built on StyleTTS2 and ISTFTNet — avoids encoders and diffusion entirely for fast generation. Great quality for the size. Good baseline if you need something dead simple.

**Chatterbox-Turbo** (Resemble AI) — A streamlined 350M-parameter model that significantly lowers compute and VRAM requirements while maintaining high-fidelity output. Open-source, production-grade.

---

## Commercial APIs (latest state)

**ElevenLabs** — Still the quality leader for English, now at $330M ARR. 32+ languages, cloning from minutes of audio. The catch remains their aggressive data licensing terms.

**Fish Audio** — Best emotion control via tags, 15 seconds for cloning, 8+ languages with strong cross-language performance.

**Resemble AI** — Best for developers wanting API control + ethics (watermarking, consent, you own your data).

---

## What I'd actually recommend for your setup

Given your 4090s and M4 Pro:

- **For local/edge experimentation**: Pocket TTS is a no-brainer to try first — it literally runs on CPU and the quality is surprisingly good. Then Dia2 or Kokoro if you want GPU-accelerated quality.
- **For real-time conversational voice**: Dia2 (streaming) or VibeVoice-Realtime-0.5B
- **For highest quality cloning, self-hosted**: Sesame CSM-1B or Fish S1-mini on your 4090s
- **For long-form multi-speaker content**: VibeVoice 1.5B/7B
- **If you just need an API and don't care about self-hosting**: ElevenLabs or Fish Audio

Want me to dig into the architecture of any of these in more detail?

message.txt
5 KB
