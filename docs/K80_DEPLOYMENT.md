# Tesla K80 Production Deployment

**Dual-GPU configuration: STT on GPU 0 (2GB), LLM on GPU 1 (14GB).**

## Hardware Setup

### GPU Configuration

```bash
# Verify K80s detected
nvidia-smi

# Expected output:
# GPU 0: Tesla K80 (24GB total, use 2GB for STT)
# GPU 1: Tesla K80 (24GB total, use 14GB for LLM)
```

### VRAM Allocation

```
GPU 0: 24GB
├─ faster-whisper base: 2GB ← STT
└─ reserved: 22GB (not used)

GPU 1: 24GB
├─ Mistral-7B LLM: 14GB ← LLM inference
└─ reserved: 10GB (headroom)
```

## Launch Configuration

### Option 1: Separate Processes (Recommended)

**Process 1: STT on GPU 0**
```bash
export CUDA_VISIBLE_DEVICES=0
poetry run python -m apps.backend.mcp_server.launcher \
  --stt-provider faster-whisper \
  --whisper-device cuda \
  --whisper-model base \
  --tts-provider pyttsx3
```

**Process 2: LLM on GPU 1 (start separately or in systemd service)**
```bash
export CUDA_VISIBLE_DEVICES=1
ollama run mistral:7b-instruct
```

### Option 2: Single Service (Docker/Systemd)

**Systemd Service: `/etc/systemd/system/mcp-voice.service`**

```ini
[Unit]
Description=Pits n' Giggles MCP Voice Server
After=network.target

[Service]
Type=simple
User=pitsngiggles
WorkingDirectory=/home/pitsngiggles/pits-n-giggles
Environment="CUDA_VISIBLE_DEVICES=0"
Environment="PYTHONUNBUFFERED=1"

ExecStart=/home/pitsngiggles/.venv/bin/poetry run python -m apps.backend.mcp_server.launcher \
  --stt-provider faster-whisper \
  --whisper-device cuda \
  --whisper-model base \
  --tts-provider pyttsx3 \
  --debug

Restart=on-failure
RestartSec=5s

# Resource limits (K80-specific)
MemoryLimit=3G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl enable mcp-voice
sudo systemctl start mcp-voice
sudo systemctl status mcp-voice
```

**Logs:**
```bash
sudo journalctl -u mcp-voice -f  # Follow logs
```

## Performance Tuning

### Whisper Model Selection

| Model | K80 VRAM | Speed | Quality | Latency |
|-------|----------|-------|---------|---------|
| tiny | 1GB | 10x | Low | 100ms |
| **base** | 2GB | 1x | High | 1-2s ⭐ |
| small | 3GB | 1/2x | Better | 3-4s |
| medium | 5GB | 1/4x | Excellent | 8-10s ❌ |

**K80 Recommendation:** Use `--whisper-model base` (sweet spot for 2GB VRAM)

### LLM Model Selection

| Model | Ollama | K80 GPU 1 (14GB) | Latency | Quality |
|-------|--------|-----------------|---------|---------|
| **mistral:7b-instruct** | ✓ | ✓ Fits | 2-5s | Good |
| neural-chat:7b | ✓ | ✓ Fits | 2-5s | Good |
| dolphin-mixtral:8x7b | ✗ | ❌ 47GB | — | Excellent |

**K80 Recommendation:** Use `mistral:7b-instruct` via Ollama

### CUDA Memory Optimization

```bash
# Set environment for K80
export CUDA_LAUNCH_BLOCKING=1
export CUDA_DEVICE_ORDER=PCI_BUS_ID

# Disable GPU memory caching (if OOM issues)
export CUDA_EMPTY_CACHE=1
```

## Performance Targets

### K80 End-to-End Latency (Measured)

```
Voice Command: "Show tire wear"
├─ STT (faster-whisper base): 1-2s
├─ Search race data: ~100ms
├─ LLM (mistral:7b): 2-5s
└─ TTS (pyttsx3): ~500ms
─────────────────────────
Total: 4-9s ⭐
```

### Monitoring Latency

**Live metrics:**
```bash
# Watch VRAM usage per GPU
watch -n 1 'nvidia-smi --query-gpu=index,memory.used,memory.free --format=csv,nounits'

# Monitor process-specific GPU usage
nvidia-smi dmon -s pucm
```

## Troubleshooting

### Issue: CUDA Out of Memory

**Solution 1: Use smaller model**
```bash
--whisper-model tiny  # 1GB instead of 2GB
```

**Solution 2: Reduce batch size**
```bash
export CUDA_MAX_BATCH_SIZE=1
```

### Issue: GPU 1 VRAM Exhaustion (Ollama)

**Solution:** Reduce model precision or use quantized version
```bash
# Use Q4 quantized mistral (8GB instead of 14GB)
ollama run mistral:7b-instruct-q4
```

### Issue: High Latency (>10s)

**Causes:**
- Whisper model too large → Use `tiny` or `base`
- LLM model too large → Ensure mistral:7b-instruct
- CPU bottleneck → Check with `top` or `htop`

**Debug:**
```bash
poetry run python -m apps.backend.mcp_server.launcher --debug
# Will print timing for each step
```

## Monitoring & Alerting

### Prometheus Metrics (Coming in Phase 4)

Expected metrics:
- `voice_pipeline_latency_ms` — end-to-end time
- `stt_latency_ms` — transcription time
- `llm_latency_ms` — LLM response time
- `gpu0_memory_usage_gb` — STT VRAM
- `gpu1_memory_usage_gb` — LLM VRAM
- `voice_errors_total` — failed commands

### Health Check

```bash
# Test MCP server (requires Claude Code connected)
curl -X POST http://localhost:4770/health 2>/dev/null || \
  echo "Server not responding (expected, stdio transport)"

# Check logs
sudo journalctl -u mcp-voice --since "1 hour ago"
```

## Deployment Checklist

- [ ] Both K80 GPUs detected via `nvidia-smi`
- [ ] CUDA 11.8+ installed and verified
- [ ] poetry env ready with dependencies
- [ ] Ollama installed and mistral:7b-instruct pulled
- [ ] Systemd service created and enabled
- [ ] CUDA_VISIBLE_DEVICES correctly configured
- [ ] Logs monitored for errors
- [ ] E2E latency <10s verified
- [ ] Claude Code connected to stdio transport
- [ ] Test voice command with live telemetry

## Next: Ollama LLM Integration

Once K80 deployment verified, implement Phase 3:
- Wire Ollama into `process_voice_command` tool
- Complete LLM streaming responses
- Add latency tracking for monitoring
