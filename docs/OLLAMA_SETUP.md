# Ollama LLM Integration Setup

**Complete voice pipeline with local LLM inference on K80 GPU 1.**

## Installation

### 1. Download Ollama

```bash
# Download from https://ollama.ai
# Or via package manager:
curl https://ollama.ai/install.sh | sh
```

### 2. Pull Mistral Model (Recommended for K80)

```bash
# Pull mistral:7b-instruct (14GB, fits on K80)
ollama pull mistral:7b-instruct

# Verify pull completed
ollama list
# Output should show: mistral:7b-instruct [size] [timestamp]
```

### 3. Configure for GPU 1 (K80 Setup)

```bash
# Set OLLAMA_NUM_PARALLEL to limit memory
export OLLAMA_NUM_PARALLEL=1

# Force GPU 1 if using dual K80s
export CUDA_VISIBLE_DEVICES=1

# Start Ollama server
ollama serve
```

**Expected output:**
```
time=2025-06-19T12:00:00.000Z level=INFO source=main.go:104 msg="Starting Ollama server"
time=2025-06-19T12:00:00.000Z level=INFO source=app.go:97 msg="Listening on 127.0.0.1:11434 (version 0.1.0)"
```

## MCP Server Integration

### Voice Pipeline

```
Voice Command (transcribed text)
        ↓
MCP process_voice_command tool
        ↓
STT: (already done)
        ↓
auto_search: search_race_data (live telemetry)
        ↓
LLM: OllamaLLMProvider.process_command()
        ├─ Connect to Ollama @ localhost:11434
        ├─ Call mistral:7b-instruct with race context
        └─ Return response
        ↓
TTS: pyttsx3 or Web Speech API
        ↓
Spoken Response
```

### Example Voice Command

```
Input: "What's Leclerc's tire wear?"

Flow:
1. STT: Transcribe audio → "What's Leclerc's tire wear?"
2. auto_search: search_race_data("tires", driver_number=16)
   → Returns: [{"driver": "Charles Leclerc", "tire_wear": 78.5, ...}]
3. LLM: Process with mistral:7b-instruct + context
   → "Charles Leclerc's front left tire has 78.5% wear, recommend pit soon"
4. TTS: Synthesize to speech
5. Output: Spoken response

Total latency: 4-9s (K80 hardware)
```

## Configuration

### VoiceSettings (config/schema/voice.py)

The `VoiceSettings` Pydantic model now supports LLM configuration:

```python
class VoiceSettings(BaseModel):
    # ... existing fields ...
    llm_provider: str = "ollama"
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "mistral:7b-instruct"
```

### MCP Server Usage

```bash
# Start with Ollama LLM
poetry run python -m apps.backend.mcp_server.launcher \
  --stt-provider faster-whisper \
  --whisper-device cuda:0 \
  --tts-provider pyttsx3

# Behind the scenes, process_voice_command will:
# 1. Connect to Ollama at localhost:11434
# 2. Use mistral:7b-instruct model
# 3. Process commands with race context
```

## Troubleshooting

### Ollama Server Not Running

```bash
# Check if server is listening
curl http://localhost:11434/api/tags

# Expected output:
{"models":[{"name":"mistral:7b-instruct:latest","modified_at":"2025-06-19T12:00:00.000Z","size":7000000000}]}

# If no response, start server:
export CUDA_VISIBLE_DEVICES=1
ollama serve
```

### Model Not Pulled

```bash
# List available models
ollama list

# Pull mistral if missing
ollama pull mistral:7b-instruct

# Use quantized version if VRAM issues (8GB instead of 14GB)
ollama pull mistral:7b-instruct-q4
# Then update config to use: mistral:7b-instruct-q4
```

### Connection Refused

```bash
# Verify Ollama listening on correct port
netstat -tlnp | grep 11434
# or
ss -tlnp | grep 11434

# If not listening, check Ollama logs
journalctl -u ollama -f  # if installed as service
# or
tail -f ~/.ollama/logs/server.log
```

### Slow Responses (>10s)

**Check:**
1. Is GPU loaded properly? `nvidia-smi`
2. Is CPU maxed out? `top`
3. Is disk slow? `iostat`

**Solutions:**
- Reduce batch size: `export OLLAMA_NUM_PARALLEL=1`
- Use smaller/quantized model: `mistral:7b-instruct-q4`
- Verify GPU 1 is used: `CUDA_VISIBLE_DEVICES=1 ollama serve`

## Performance Targets

| Metric | K80 Target | Notes |
|--------|-----------|-------|
| STT (transcribe) | 1-2s | On GPU 0 |
| Search race data | ~100ms | RAM-based |
| LLM (mistral:7b) | 2-5s | On GPU 1 |
| TTS (pyttsx3) | ~500ms | CPU |
| **Total** | **4-9s** | End-to-end ⭐ |

## systemd Service (Optional)

**File: `/etc/systemd/system/ollama.service`**

```ini
[Unit]
Description=Ollama Service
After=network.target

[Service]
Type=simple
User=ollama
WorkingDirectory=/home/ollama
Environment="CUDA_VISIBLE_DEVICES=1"
Environment="OLLAMA_NUM_PARALLEL=1"

ExecStart=/usr/bin/ollama serve

Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

**Enable:**
```bash
sudo systemctl enable ollama
sudo systemctl start ollama
sudo journalctl -u ollama -f
```

## Next: Monitoring & Production

Phase 4 will add:
- Prometheus metrics (LLM latency, errors, token usage)
- Grafana dashboards (P95 latency tracking)
- Health checks (Ollama server connectivity)
- Error alerts (model failures, VRAM exhaustion)
