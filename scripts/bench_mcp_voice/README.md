# MCP and voice benchmark harness

Supports the [architecture audit](../../docs/architecture-audit/README.md). Run all commands from the repository root with Python 3.12 and the project dependencies installed.

## Prerequisites

- Piper voice: `models/piper/en_GB-alan-medium.onnx` and `.onnx.json`
- Whisper models: downloaded into `models/whisper/` by faster-whisper (`tiny.en`, `base.en`, `small.en`)
- Ollama on `127.0.0.1:11434` with `qwen2.5:1.5b`, `llama3.2:3b` and `llama3.1:8b` pulled
- Set `PNG_BENCH_HOME` if the `models/` directory lives somewhere other than the repository root

The MCP harness binds ports 55835, 55836, 55838 and 4770. Stop a running Pits n' Giggles instance first, or edit the constants at the top of `bench_mcp.py`.

## Commands

```bash
python scripts/bench_mcp_voice/bench_mcp.py                          # full MCP/IPC suite at 5 Hz
RATE_HZ=20 python scripts/bench_mcp_voice/bench_mcp.py               # same suite at 20 Hz
VOICE_ONLY=1 RATE_HZ=10 python scripts/bench_mcp_voice/bench_mcp.py  # voice coherence test only
HF_HUB_OFFLINE=1 python scripts/bench_mcp_voice/bench_voice.py       # Piper, Whisper, Ollama
python scripts/bench_mcp_voice/bench_prefix.py                       # selector prompt-order cache test
python scripts/bench_mcp_voice/chart.py                              # regenerate the chart
```

Results are written to `scripts/bench_mcp_voice/results/`. The committed results come from a 2 vCPU Intel Xeon @ 2.9 GHz with no GPU (19 November 2026). The race-table data is synthetic: 20 cars, 38 KB per message.
