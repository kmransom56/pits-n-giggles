# MCP Server Integration for Pits n' Giggles Voice

**Model Context Protocol (MCP) server exposing F1 telemetry voice operations to Claude, ChatGPT, and other AI assistants.**

## Overview

The Pits n' Giggles MCP server makes voice transcription, speech synthesis, and command processing available as **tools** that AI assistants can call. This enables:

- 🎤 **AI-Assisted Voice Commands**: Claude processes voice input and controls the app
- 🧠 **LLM-Powered Analysis**: Voice queries analyzed with race context
- 🔄 **Two-Way Integration**: Chat interface with voice input/output
- 🚀 **Extensible Tools**: MCP tools can trigger remote actions (Fortinet, network systems)

## Quick Start

### 1. Launch MCP Server

```bash
# Using launcher script
poetry run python -m apps.backend.mcp_server.launcher \
    --stt-provider faster-whisper \
    --whisper-device cuda \
    --tts-provider web-speech-api

# Or directly
poetry run python apps/backend/mcp_server/launcher.py
```

**Output:**
```
======================================================================
🎤 Pits n' Giggles Voice MCP Server
======================================================================
STT Provider: faster-whisper
TTS Provider: web-speech-api
Whisper Device: cuda
Whisper Model: base

MCP Protocol: stdio (standard input/output)
Tools available: 7
  • transcribe_audio - Speech-to-text via configurable STT
  • synthesize_speech - Text-to-speech via configurable TTS
  • list_stt_providers - Query available STT providers
  • list_tts_providers - Query available TTS providers
  • process_voice_command - Process voice commands with LLM context
  • list_voice_config - Get current voice system configuration
  • get_voice_status - Monitor voice system health

Starting MCP server on stdio transport...
======================================================================
```

### 2. Connect Claude to MCP Server

In **Claude Code** (or any MCP-compatible tool):

1. Open Claude Code settings
2. Add MCP server under "Model Context Protocol" settings
3. Set command: `poetry run python -m apps.backend.mcp_server.launcher`
4. Set working directory: `/home/keith/pits-n-giggles`

Or programmatically:

```python
from mcp import ClientSession
import subprocess

# Start MCP server
process = subprocess.Popen(
    ["poetry", "run", "python", "-m", "apps.backend.mcp_server.launcher"],
    cwd="/home/keith/pits-n-giggles",
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

# Connect client
session = ClientSession(process.stdin, process.stdout)
await session.initialize()

# List available tools
tools = await session.list_tools()
```

## MCP Tools API

### 🎤 `transcribe_audio`

Convert audio (base64 encoded) to text.

**Parameters:**
- `audio_data_base64` (str): Base64-encoded audio data (PCM 16kHz)
- `provider` (str): STT provider - "faster-whisper" (local GPU) or "openai" (cloud)
- `language` (str): Language code (default "en")

**Returns:**
```json
{
  "transcript": "Show Leclerc's tire wear",
  "provider": "faster-whisper",
  "confidence": 0.95,
  "language": "en",
  "duration_seconds": 2.5
}
```

**Example:**
```python
# In Claude Code or any AI assistant
result = await client.call_tool("transcribe_audio", {
    "audio_data_base64": "//uRRJ...",  # Base64 WAV audio
    "provider": "faster-whisper",
    "language": "en"
})

print(f"Transcribed: {result['transcript']}")
```

### 🔊 `synthesize_speech`

Convert text to audio (WAV format, base64 encoded).

**Parameters:**
- `text` (str): Text to convert to speech
- `provider` (str): TTS provider - "web-speech-api" (browser) or "pyttsx3" (local)
- `language` (str): Language/voice (default "en-US")

**Returns:**
```json
{
  "audio_base64": "UklGRi4gAABX...",  // WAV audio data
  "provider": "pyttsx3",
  "duration_seconds": 3.2,
  "format": "WAV",
  "text": "Charles Leclerc's tire wear is at 85 percent"
}
```

**Example:**
```python
result = await client.call_tool("synthesize_speech", {
    "text": "Pit stop recommended lap 35",
    "provider": "pyttsx3"
})

audio_bytes = base64.b64decode(result['audio_base64'])
# Play audio or send to browser
```

### 📋 `list_stt_providers`

Query available Speech-to-Text providers and capabilities.

**Returns:**
```json
{
  "providers": [
    {
      "name": "faster-whisper",
      "type": "local",
      "description": "GPU-optimized local Whisper",
      "speed": "10x faster than cloud",
      "cost": "$0/month",
      "offline": true,
      "vram_required_gb": 2,
      "quality": "Excellent (same model as OpenAI)"
    },
    {
      "name": "openai",
      "type": "cloud",
      "description": "OpenAI Whisper API",
      "cost": "$0.02/minute",
      "offline": false,
      "requires_api_key": true
    }
  ],
  "recommended": "faster-whisper (local GPU, 10x faster, $0 cost)",
  "current_config": {
    "provider": "faster-whisper",
    "model_size": "base",
    "device": "cuda"
  }
}
```

### 🔈 `list_tts_providers`

Query available Text-to-Speech providers.

**Returns:**
```json
{
  "providers": [
    {
      "name": "web-speech-api",
      "type": "browser-native",
      "quality": "Excellent (natural sounding)",
      "cost": "$0",
      "latency": "~500ms"
    },
    {
      "name": "pyttsx3",
      "type": "local",
      "quality": "Good (robotic but clear)",
      "cost": "$0",
      "latency": "~800ms"
    }
  ],
  "recommended": "web-speech-api (excellent quality, zero cost)"
}
```

### 🧠 `process_voice_command`

Process voice transcription through LLM with race context.

**Parameters:**
- `transcription` (str): Transcribed voice command
- `race_context` (dict, optional): Race telemetry data (driver info, lap times, etc.)
- `llm_provider` (str): LLM provider - "ollama", "lmstudio", or "openai"

**Returns:**
```json
{
  "response": "Charles Leclerc is on medium-soft compound, pit stop expected lap 35",
  "provider": "ollama",
  "processing_time_ms": 2150,
  "context_used": true,
  "status": "processing"
}
```

**Example with Race Context:**
```python
result = await client.call_tool("process_voice_command", {
    "transcription": "Show Leclerc pit strategy",
    "race_context": {
        "driver": "Charles Leclerc",
        "position": 2,
        "tire_compound": "soft",
        "tire_wear": {"fl": 85, "fr": 82, "rl": 65, "rr": 68},
        "fuel_remaining": 45,
        "laps_completed": 30,
        "current_lap": 31
    },
    "llm_provider": "ollama"
})

print(f"Response: {result['response']}")
```

### ⚙️ `list_voice_config`

Get current voice system configuration.

**Returns:**
```json
{
  "voice_enabled": true,
  "stt_provider": "faster-whisper",
  "tts_provider": "web-speech-api",
  "stt_options": {
    "providers": ["faster-whisper", "openai"],
    "model_sizes": ["tiny", "base", "small", "medium", "large"],
    "current_model": "base",
    "devices": ["cuda", "cpu"],
    "current_device": "cuda"
  },
  "audio_settings": {
    "sample_rate": 16000,
    "language": "en-US",
    "timeout_seconds": 10
  },
  "hardware_info": {
    "k80_optimized": true,
    "recommended_vram_usage": "STT 2GB (GPU 0) + LLM 14GB (GPU 1)"
  }
}
```

### 🔍 `get_voice_status`

Monitor voice system health and provider status.

**Returns:**
```json
{
  "system_online": true,
  "stt_provider": {
    "name": "faster-whisper",
    "status": "ready",
    "initialized": true
  },
  "tts_provider": {
    "name": "web-speech-api",
    "status": "ready",
    "initialized": false
  },
  "audio_buffer": {
    "status": "empty",
    "recording": false
  },
  "mcp_server": {
    "status": "online",
    "version": "1.0.0",
    "tools_available": 7
  },
  "timestamp": "2025-06-19T12:34:56.789Z"
}
```

## Usage Examples

### Example 1: Complete Voice Transcription Pipeline

```python
# In Claude or any MCP client
import base64

# 1. Get available STT providers
providers = await client.call_tool("list_stt_providers", {})
print(f"Using: {providers['recommended']}")

# 2. Transcribe audio
audio_bytes = get_microphone_audio()  # Get 16kHz PCM audio
audio_base64 = base64.b64encode(audio_bytes).decode()

transcript_result = await client.call_tool("transcribe_audio", {
    "audio_data_base64": audio_base64,
    "provider": "faster-whisper"
})

print(f"✓ Transcribed: {transcript_result['transcript']}")

# 3. Process with LLM
response = await client.call_tool("process_voice_command", {
    "transcription": transcript_result['transcript'],
    "race_context": get_current_race_data(),
    "llm_provider": "ollama"
})

print(f"Response: {response['response']}")

# 4. Synthesize speech response
audio_result = await client.call_tool("synthesize_speech", {
    "text": response['response'],
    "provider": "web-speech-api"
})

play_audio(base64.b64decode(audio_result['audio_base64']))
```

### Example 2: Voice-First F1 Engineer Workflow

```python
# Scenario: During race, engineer needs tire strategy while watching telemetry

async def voice_query_f1_data(voice_audio_bytes):
    """Process voice query and return spoken response."""
    
    # Step 1: Transcribe
    audio_b64 = base64.b64encode(voice_audio_bytes).decode()
    transcript = await client.call_tool("transcribe_audio", {
        "audio_data_base64": audio_b64,
        "provider": "faster-whisper"
    })
    
    # Step 2: Process with race context
    race_data = fetch_current_telemetry()
    response = await client.call_tool("process_voice_command", {
        "transcription": transcript['transcript'],
        "race_context": race_data,
        "llm_provider": "ollama"
    })
    
    # Step 3: Speak response
    audio_response = await client.call_tool("synthesize_speech", {
        "text": response['response'],
        "provider": "web-speech-api"
    })
    
    return audio_response['audio_base64']

# Usage
voice_input = record_voice_input()  # ~2-3 seconds
audio_output = await voice_query_f1_data(voice_input)
play_audio_in_browser(audio_output)  # Response heard in headphones
```

## Configuration

### Launch Flags

```bash
# Custom STT provider
poetry run python -m apps.backend.mcp_server.launcher \
    --stt-provider openai \
    --whisper-device cuda

# CPU-only (no GPU)
poetry run python -m apps.backend.mcp_server.launcher \
    --whisper-device cpu \
    --stt-provider faster-whisper

# Custom TTS
poetry run python -m apps.backend.mcp_server.launcher \
    --tts-provider pyttsx3

# Debug logging
poetry run python -m apps.backend.mcp_server.launcher \
    --debug
```

### MCP Client Configuration

**In Claude Code (`claude-code/settings.json`):**
```json
{
  "mcp_servers": [
    {
      "name": "pits-n-giggles-voice",
      "command": "poetry run python -m apps.backend.mcp_server.launcher",
      "working_directory": "/home/keith/pits-n-giggles",
      "args": [
        "--stt-provider", "faster-whisper",
        "--whisper-device", "cuda",
        "--tts-provider", "web-speech-api"
      ]
    }
  ]
}
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Code / AI                       │
│                    (or other MCP client)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ MCP Protocol (stdio)
                       │
┌──────────────────────▼──────────────────────────────────────┐
│          FastMCP Server (voice_mcp.py)                      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐    │
│  │ STT Tools    │  │ TTS Tools    │  │  LLM Tools    │    │
│  ├──────────────┤  ├──────────────┤  ├───────────────┤    │
│  │ transcribe   │  │ synthesize   │  │ process_      │    │
│  │_audio        │  │_speech       │  │  voice_cmd    │    │
│  │              │  │              │  │               │    │
│  │ list_stt_    │  │ list_tts_    │  │ (LLM context) │    │
│  │ providers    │  │ providers    │  │               │    │
│  └──────────────┘  └──────────────┘  └───────────────┘    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ Config Tools │  │ Status Tools │                        │
│  ├──────────────┤  ├──────────────┤                        │
│  │ list_voice   │  │ get_voice    │                        │
│  │ _config      │  │ _status      │                        │
│  └──────────────┘  └──────────────┘                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐   ┌──────────┐
   │ STT     │   │  TTS     │   │   LLM    │
   │ Layer   │   │  Layer   │   │  Layer   │
   └────┬────┘   └────┬─────┘   └────┬─────┘
        │             │              │
        ▼             ▼              ▼
   ┌────────────┬──────────────┬──────────────┐
   │ faster-    │ Web Speech   │   Ollama /   │
   │ whisper    │ API (browser)│  LM Studio   │
   │ (GPU)      │   OR         │   (local)    │
   │            │ pyttsx3      │              │
   │            │ (local)      │   OR OpenAI  │
   └────────────┴──────────────┴──────────────┘
```

## Performance

### Latency (Tesla K80)

```
Complete Voice Pipeline:
  Transcription:     1-2 seconds (faster-whisper GPU)
  LLM Processing:    2-5 seconds (Ollama local LLM)
  TTS Generation:    ~500ms (Web Speech API)
  ─────────────────────────
  Total end-to-end:  3-8 seconds

vs Cloud-only:
  OpenAI STT:        5-10 seconds (network latency)
  GPT-4 Processing:  10-30 seconds (inference)
  ElevenLabs TTS:    2-5 seconds (quality premium)
  ─────────────────────────
  Total:             17-45 seconds ❌
```

### Cost

```
Local Setup (K80):
  Per 100 queries: $0
  Monthly (10/day): $0
  Yearly: $0 (one-time K80 cost only)

Cloud Setup:
  STT 100 queries: $2-5
  TTS 100 queries: $1.50+
  LLM 100 queries: $30-50
  ─────────────────
  Monthly: $60-100
  Yearly: $720-1,200+ 💸
```

## Troubleshooting

### MCP Server Won't Start

```bash
# Check poetry environment
poetry shell
poetry run python -m apps.backend.mcp_server.launcher

# Debug mode for verbose output
poetry run python -m apps.backend.mcp_server.launcher --debug

# Verify dependencies installed
poetry install --no-root
```

### Tools Not Available in Claude

1. **Verify server is running:**
   ```bash
   # Should see "Starting MCP server on stdio transport..."
   ```

2. **Check MCP configuration:**
   - Claude Code → Settings → Model Context Protocol
   - Command path correct?
   - Working directory correct?

3. **Restart Claude:**
   - Close and reopen Claude Code
   - MCP servers reload on startup

### Audio Transcription Failing

```bash
# Check GPU availability
nvidia-smi

# Test with CPU fallback
poetry run python -m apps.backend.mcp_server.launcher \
    --whisper-device cpu
```

## Next Steps

1. ✅ MCP server with 7 voice tools
2. 🚧 LLMProviderFactory implementation (Ollama, LM Studio support)
3. 🚧 Race context integration (telemetry system connection)
4. 🚧 Voice command parsing and F1-specific intent recognition
5. 🚧 Multi-language support with auto-detection
6. 🚧 Remote MCP tool invocation (Fortinet device control via voice)

## Resources

- **MCP Protocol**: https://modelcontextprotocol.io
- **Pits n' Giggles**: https://github.com/ashwin-nat/pits-n-giggles
- **FastMCP**: https://github.com/jlowin/fastmcp
- **faster-whisper**: https://github.com/guillaumekln/faster-whisper
- **Ollama**: https://ollama.ai

---

**Built with 🎤 FastMCP + Pits n' Giggles Voice Layer**
