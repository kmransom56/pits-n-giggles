# 🎤 MCP Voice Integration Quick Start

**Use Pits n' Giggles voice tools from Claude Code and other AI assistants.**

## 30-Second Setup

### 1. Start MCP Server

```bash
cd /home/keith/pits-n-giggles
poetry run python -m apps.backend.mcp_server.launcher
```

You should see:
```
======================================================================
🎤 Pits n' Giggles Voice MCP Server
======================================================================
Starting MCP server on stdio transport...
======================================================================
```

### 2. Connect to Claude Code (or other MCP client)

In Claude Code settings:
1. Settings → Model Context Protocol
2. Add MCP Server
3. Set command: `poetry run python -m apps.backend.mcp_server.launcher`
4. Set working directory: `/home/keith/pits-n-giggles`
5. Click "Add"

Claude will now have access to 7 voice tools! ✓

## Available Tools

| Tool | Purpose |
|------|---------|
| `transcribe_audio` | Convert audio (base64) to text |
| `synthesize_speech` | Convert text to audio (base64) |
| `list_stt_providers` | Query STT provider capabilities |
| `list_tts_providers` | Query TTS provider capabilities |
| `process_voice_command` | Process voice with LLM + race context |
| `list_voice_config` | Get current voice configuration |
| `get_voice_status` | Monitor system health |

## Usage Example in Claude

**Try this prompt in Claude Code:**

```
Use the "transcribe_audio" MCP tool to show me how the STT system works. 
First, list the available STT providers and their capabilities.
Then explain what audio format is expected.
```

Claude will automatically:
1. Call `list_stt_providers` 
2. Parse the response
3. Explain the available options

## Common Tasks

### Configure STT Provider

**Local GPU (Recommended):**
```bash
poetry run python -m apps.backend.mcp_server.launcher \
    --stt-provider faster-whisper \
    --whisper-device cuda
```

**Cloud (OpenAI):**
```bash
poetry run python -m apps.backend.mcp_server.launcher \
    --stt-provider openai \
    --api-key sk-your-key
```

### Configure TTS Provider

**Browser (High Quality):**
```bash
poetry run python -m apps.backend.mcp_server.launcher \
    --tts-provider web-speech-api
```

**Local (Instant):**
```bash
poetry run python -m apps.backend.mcp_server.launcher \
    --tts-provider pyttsx3
```

### Debug Mode

```bash
poetry run python -m apps.backend.mcp_server.launcher --debug
```

## Architecture

```
Your Code/Claude                    MCP Server (stdio)
    │                                      │
    ├─ transcribe_audio ────────────────→ Voice Handler
    ├─ synthesize_speech ───────────────→ Voice Handler
    ├─ process_voice_command ──────────→ Voice + LLM
    └─ list_*_providers ───────────────→ Config Reader
```

## Performance Targets

**Tesla K80 Hardware:**
- Transcription: 1-2 seconds (faster-whisper)
- LLM Processing: 2-5 seconds (Ollama local)
- TTS Generation: ~500ms (Web Speech API)
- **Total end-to-end: 3-8 seconds** ⚡

## Troubleshooting

**Server won't start:**
```bash
# Verify dependencies
poetry install --no-root

# Check Python version
python --version  # Must be 3.12+

# Try with debug output
poetry run python -m apps.backend.mcp_server.launcher --debug
```

**Claude can't find tools:**
1. Restart Claude Code
2. Check MCP server is running (should see startup message)
3. Verify working directory is `/home/keith/pits-n-giggles`

**Transcription fails:**
```bash
# Test with CPU if GPU unavailable
poetry run python -m apps.backend.mcp_server.launcher \
    --whisper-device cpu
```

## Real-World Example

Ask Claude:
```
I need to transcribe some audio and process it as an F1 engineer voice command.
The command is about tire strategy. Show me how the MCP tools would handle this.
```

Claude will:
1. Explain the transcribe_audio tool
2. Show process_voice_command usage
3. Demonstrate race_context parameters
4. Explain how LLM would analyze the command

## Next Steps

- 📖 Full documentation: `docs/MCP_INTEGRATION.md`
- 🚀 Advanced configuration: See launcher flags
- 🔧 Integration guide: See voice_layer module documentation

## Quick Links

- **MCP Spec**: https://modelcontextprotocol.io
- **Pits n' Giggles**: https://github.com/ashwin-nat/pits-n-giggles
- **FastMCP**: https://github.com/jlowin/fastmcp
- **faster-whisper**: https://github.com/guillaumekln/faster-whisper

---

**🎤 Ready to use voice with AI? Start the MCP server and connect Claude!**

```bash
cd /home/keith/pits-n-giggles && poetry run python -m apps.backend.mcp_server.launcher
```
