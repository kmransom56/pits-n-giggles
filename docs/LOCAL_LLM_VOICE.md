# Local LLM Voice Integration Guide

This guide shows how to run Pits n' Giggles with **completely local voice processing** — no cloud APIs needed. Perfect for privacy and offline operation.

## Overview

The voice layer now supports multiple **pluggable providers** for STT/TTS:

| Component | Cloud Option | Local Option | Cost |
|-----------|--------------|--------------|------|
| **STT** (Speech-to-Text) | OpenAI Whisper | faster-whisper | $0.02/min vs Free |
| **TTS** (Text-to-Speech) | ElevenLabs, Google | pyttsx3, XTTS-v2 | $$ vs Free |
| **LLM** (Command Processing) | GPT-4, Claude | Mistral-7B, Llama2-7B | $$ vs Free |

## Hardware Requirements

Your **dual Tesla K80s** (24GB VRAM each) are **perfect** for this:

- ✅ **faster-whisper** (base model): ~2GB VRAM
- ✅ **Mistral-7B** or **Llama2-7B**: ~14-16GB VRAM (each K80)
- ✅ Can run STT + LLM in parallel on separate GPUs

**Memory Layout**:
```
GPU 0 (K80, 24GB)           GPU 1 (K80, 24GB)
├─ faster-whisper (2GB)     ├─ LLM: Mistral-7B (15GB)
├─ Ollama runtime (5GB)     ├─ Ollama runtime (5GB)
└─ Headroom (17GB)          └─ Headroom (4GB)
```

## Quick Setup: Local Only (No Cloud)

### Step 1: Choose STT Provider

**Option A: faster-whisper (Recommended)**
```json
// png_config.json
{
    "Voice": {
        "enabled": true,
        "stt_provider": "faster-whisper",
        "whisper_model_size": "base",
        "whisper_device": "cuda",
        "tts_provider": "pyttsx3"
    }
}
```

**Why faster-whisper?**
- Same quality as OpenAI Whisper API
- ~10x faster with GPU (K80 optimized)
- No API key needed
- $0 cost vs $0.02/min

### Step 2: Start Pits n' Giggles

```bash
poetry run python -m apps.launcher
```

**First run**: faster-whisper will download the model (~140MB for "base")

### Step 3: Test Voice

1. Open http://localhost:4768
2. Click 🎤 microphone button
3. Say: "Hello"
4. Transcript appears (processed locally on GPU)
5. Audio plays back (pyttsx3)

**That's it!** No cloud dependencies. ✅

---

## Advanced Setup: STT + LLM Pipeline

For **command processing** (e.g., "Show Leclerc pit strategy" → parsed intent → response):

### Step 1: Install Ollama (Local LLM Runtime)

**macOS/Windows**:
```bash
# Download from https://ollama.ai
# Ollama bundles llama2, mistral, etc.
ollama pull mistral
```

**Linux** (Docker):
```bash
docker run -d -p 11434:11434 ollama/ollama
docker exec ollama ollama pull mistral
```

### Step 2: Update Configuration

```json
{
    "Voice": {
        "enabled": true,
        "stt_provider": "faster-whisper",
        "whisper_device": "cuda",
        "tts_provider": "pyttsx3",
        "auto_announce_enabled": true,
        "llm_enabled": true,
        "llm_provider": "ollama",
        "llm_model": "mistral",
        "llm_base_url": "http://localhost:11434"
    }
}
```

### Step 3: Enable LLM Processing

Once Ollama is running with a model loaded, the voice handler will:

1. **Transcribe** via faster-whisper (GPU 0)
2. **Parse intent** via Mistral-7B (GPU 1)
3. **Generate response** based on F1 telemetry context
4. **Speak** via pyttsx3

**Example Flow**:
```
You: "What's the pit strategy for Leclerc?"
    ↓
[GPU 0] faster-whisper: "What's the pit strategy for Leclerc?"
    ↓
[GPU 1] Mistral-7B processes intent + race context
    ↓
Response: "Leclerc is on a medium-soft strategy, pit stop expected lap 35"
    ↓
[TTS] pyttsx3 speaks response
```

---

## Provider Options

### STT Providers

#### 1. **faster-whisper** ⭐ (Recommended)
```json
{
    "stt_provider": "faster-whisper",
    "whisper_model_size": "base",  // tiny, base, small, medium, large
    "whisper_device": "cuda"       // cuda or cpu
}
```

**Models**:
| Size | Speed | Accuracy | VRAM |
|------|-------|----------|------|
| tiny | ⚡⚡⚡ | ⭐⭐ | 1GB |
| base | ⚡⚡ | ⭐⭐⭐ | 2GB |
| small | ⚡ | ⭐⭐⭐⭐ | 3GB |
| medium | 🐢 | ⭐⭐⭐⭐⭐ | 5GB |
| large | 🐢🐢 | ⭐⭐⭐⭐⭐ | 10GB |

**For K80s**: Use "base" for best speed/accuracy tradeoff.

#### 2. **OpenAI Whisper** (Cloud fallback)
```json
{
    "stt_provider": "openai",
    "api_key": "sk-..."
}
```

**Cost**: $0.02/min of audio (~$0.033 per 100 utterances)

### TTS Providers

#### 1. **pyttsx3** ⭐ (Local, Free)
```json
{
    "tts_provider": "pyttsx3",
    "tts_rate": 150  // words per minute
}
```

**Pros**: Fast, offline, free, cross-platform
**Cons**: Lower quality voice

#### 2. **Web Speech API** (Browser default)
```json
{
    "tts_provider": "web-speech-api"
}
```

**Pros**: High quality, runs in browser
**Cons**: May conflict with other audio

#### 3. **XTTS-v2** (Coming soon)
```json
{
    "tts_provider": "xtts-v2",
    "xtts_model": "gpt-sovits"
}
```

**Pros**: High-quality local synthesis
**Cons**: Requires GPU, slower

### LLM Providers

#### 1. **Ollama** (Recommended)
```json
{
    "llm_provider": "ollama",
    "llm_model": "mistral",  // mistral, llama2, neural-chat, etc.
    "llm_base_url": "http://localhost:11434"
}
```

**Available Models**:
```bash
ollama pull mistral      # 7.3B, good for commands
ollama pull llama2       # 7B/13B, general purpose
ollama pull neural-chat  # 7B, optimized for chat
```

#### 2. **LM Studio** (Desktop GUI)
```json
{
    "llm_provider": "lmstudio",
    "llm_base_url": "http://localhost:1234"
}
```

#### 3. **OpenAI GPT** (Cloud fallback)
```json
{
    "llm_provider": "openai",
    "llm_model": "gpt-4",
    "api_key": "sk-..."
}
```

---

## Troubleshooting

### "faster-whisper not installed"
```bash
cd /home/keith/pits-n-giggles
poetry install  # Downloads faster-whisper (14 new packages)
```

### "Transcription hangs"
**Symptom**: "Processing..." for 10+ seconds

**Causes**:
- Model still downloading (first run only)
- GPU out of memory
- Ollama not running (if using LLM)

**Fixes**:
```bash
# Check faster-whisper model cache
ls -lh ~/.cache/huggingface/hub/

# Free GPU memory
nvidia-smi  # Check VRAM usage
```

### "No transcription, only silence"
- Microphone volume too low
- Background noise detected as silence
- Model needs louder/clearer speech

### "LLM responses are slow"
- Mistral-7B takes 2-5s per token on K80
- Use smaller model (neural-chat: 7B) or reduce context size
- Increase `timeout_seconds` in config

---

## Performance Tuning for K80s

### Maximize Parallel Processing

Run STT and LLM on **separate GPUs**:

**K80 GPU 0**: faster-whisper (2GB) + headroom for OS
**K80 GPU 1**: Mistral-7B (14GB) + Ollama runtime

```bash
# Set CUDA device for voice handler (GPU 0)
CUDA_VISIBLE_DEVICES=0 poetry run python -m apps.backend

# In separate terminal, run Ollama on GPU 1
CUDA_VISIBLE_DEVICES=1 ollama serve
```

### Quantization

For **Mistral on K80**, use 4-bit quantization:

```bash
ollama pull mistral:7b-instruct-q4_K_M  # 4-bit quantized
```

**Before**: 14GB VRAM usage
**After**: 4-5GB VRAM usage

---

## Costs: Local vs Cloud

| Service | Local | Cloud |
|---------|-------|-------|
| STT | Free (faster-whisper) | $0.02/min (OpenAI) |
| TTS | Free (pyttsx3) | $0.015/1K chars (ElevenLabs) |
| LLM | Free (Ollama) | $0.03-$0.30/1K tokens (OpenAI) |
| **100 queries** | $0 | ~$50 |
| **Yearly (10 queries/day)** | $0 | ~$18,250 |

**Total Savings with Local**: $0-$18k/year 💰

---

## Files Modified

**New Files**:
- `apps/backend/voice_layer/providers.py` — Provider abstractions

**Modified Files**:
- `lib/config/schema/voice.py` — Added provider options
- `apps/backend/voice_layer/voice_handler.py` — Now uses provider factory
- `png_config.json` — Added local provider defaults
- `pyproject.toml` — Added faster-whisper, pyttsx3

---

## Next Steps

- [x] Phase 1: Local STT via faster-whisper
- [x] Phase 2: Local TTS via pyttsx3
- [ ] Phase 3: Local LLM via Ollama (coming next)
- [ ] Phase 4: Voice commands from race data context

---

## FAQs

**Q: Can I mix cloud and local?**
A: Yes! STT=faster-whisper, TTS=ElevenLabs. Mix and match as needed.

**Q: Will this work on my laptop?**
A: Probably not well. K80s are ideal. Laptops need quantized models (4-bit).

**Q: How much internet is needed?**
A: Zero during operation. Only for initial model downloads (150MB).

**Q: Can I use this offline?**
A: Completely offline once models are downloaded.

**Q: How do I switch providers mid-race?**
A: Edit `png_config.json` and restart the backend.

---

## Resources

- **faster-whisper**: https://github.com/guillaumekln/faster-whisper
- **Ollama**: https://ollama.ai
- **Mistral**: https://mistral.ai
- **LM Studio**: https://lmstudio.ai

Enjoy local, private, free voice for Pits n' Giggles! 🎤🏁
