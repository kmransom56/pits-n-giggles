# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

**Prerequisites**: Python 3.12–3.14, Node.js (for MCP Inspector testing).

```bash
# Install dependencies using Poetry (required for all Python work)
poetry install

# Verify installation
poetry run python --version
poetry run pytest --version
```

## Common Commands

### Testing
```bash
# Run full test suite (excludes live API tests and serial tests run sequentially)
poetry run pytest tests/

# Run tests by pattern (class, method, function, or keyword)
poetry run pytest tests/ -k "TestWatchDogTimerAsync"
poetry run pytest tests/ -k "test_initial_state_idle"

# Run only serial tests (real sockets/ports/processes — runs sequentially)
poetry run pytest tests/ -m serial

# Run only parallel-safe tests (excludes serial tests)
poetry run pytest tests/ -m "not serial"

# Run single test file
poetry run pytest tests/tests_version.py

# Live API integration tests (OpenF1 schema checks — requires network, excluded by default)
poetry run pytest tests/tests_openf1/tests_openf1_integration.py -m openf1 -v -n 0

# Run with coverage report
poetry run python scripts/coverage_ut.py
poetry run python scripts/coverage_integration_tests.py
```

### Linting & Code Quality
```bash
# Lint (uses pylint config in scripts/.pylintrc)
poetry run pylint --rcfile scripts/.pylintrc apps lib

# Check version consistency (single source of truth in meta/meta.py)
poetry run pytest tests/tests_version.py
```

### Building & Packaging
```bash
# Build standalone executable (Windows/macOS)
poetry run python scripts/build.py

# Uses PyInstaller spec (scripts/png.spec) — includes hidden imports for voice, MCP, Qt
```

## Running Apps

Each app is a Python module. Typically, **use the launcher** which starts all others as managed subprocesses. You can also run apps individually for debugging:

```bash
# Primary: GUI launcher (starts backend, HUD, broker, MCP server as subprocesses)
poetry run python -m apps.launcher

# Backend: Telemetry server (captures UDP/TCP from F1 game, broadcasts via Socket.IO + REST)
poetry run python -m apps.backend

# HUD: Always-on-top in-game overlay (Qt windows with live telemetry widgets)
poetry run python -m apps.hud

# Broker: ZeroMQ pub/sub broker (multi-client telemetry forwarding)
poetry run python -m apps.broker

# MCP Server: Exposes telemetry as MCP tools for AI integration (stdio or HTTP transport)
poetry run python -m apps.mcp_server              # stdio transport (for MCP Inspector)
poetry run python -m apps.mcp_server --managed   # HTTP transport (managed by launcher)

# Save Viewer: Web server for analyzing saved session JSON files
poetry run python -m apps.save_viewer

# Dev Tools: Telemetry replay for testing (uses saved .f1pcap files)
poetry run python -m apps.dev_tools.telemetry_replayer --file-name example.f1pcap
```

### Testing Apps with MCP Inspector

The MCP server can be tested independently without the full launcher stack:

```bash
# Start MCP server and open inspector (stdio transport)
npx @modelcontextprotocol/inspector poetry run python -m apps.mcp_server

# With debug logging
npx @modelcontextprotocol/inspector poetry run python -m apps.mcp_server -- --debug

# Or run server manually (HTTP transport) and connect inspector to http://localhost:4770/mcp
poetry run python -m apps.mcp_server --managed --debug
```

See `apps/mcp_server/README.md` for detailed MCP testing and debugging instructions.

## Architecture

**Pits n' Giggles** is a multi-process F1 telemetry suite. The F1 game broadcasts UDP telemetry; this app captures, parses, analyzes, and displays it via browser dashboards and an in-game overlay.

### Process Model

```
apps/launcher/     — Qt (PySide6) GUI; spawns and monitors all other processes via IPC
apps/backend/      — Core server: receives UDP/TCP from F1 game, runs analysis, serves WebSocket+REST
apps/hud/          — Always-on-top Qt overlay windows for in-game display
apps/broker/       — ZeroMQ pub/sub broker for multi-client telemetry forwarding
apps/save_viewer/  — Quart web server for analyzing saved session JSON files
apps/frontend/     — Vanilla JS/HTML/CSS browser UI (served by backend)
apps/dev_tools/    — Telemetry replayer and packet capture utilities
```

### Backend Layers (`apps/backend/`)

The backend is structured in four layers with clear separation of concerns:

1. **`telemetry_layer/`**
   - UDP/TCP socket reception (configurable via `png_config.json`)
   - Packet parsing for 16 F1 packet types (seasons 2023–2025 via `lib/f1_types/`)
   - Frame gating: throttles updates to avoid overwhelming clients
   - Uses `TelemetryManager` from `lib/telemetry_manager/`

2. **`state_mgmt_layer/`**
   - `SessionState` aggregates all parsed telemetry data
   - Runs race analysis: overtake detection, collision tracking, tyre wear extrapolation
   - Per-driver and per-session managers (`lib/race_ctrl/`)
   - Lap delta calculations (`lib/delta/`)
   - Tracks vehicle damage, fuel burn, ERS deployment per driver
   - Data source for MCP server tools and voice context enrichment

3. **`intf_layer/`**
   - Quart async web server + Socket.IO WebSocket support
   - Pushes live state updates to browser clients and HUD via Socket.IO events
   - Exposes REST API for lap history, driver info, session events
   - HTTPS support configurable via `png_config.json`

4. **`voice_layer/`**
   - Two-way voice communication (STT → LLM → TTS pipeline)
   - **Default STT**: `faster-whisper` (local, GPU-accelerated, free) — switched from OpenAI Whisper
   - **LLM providers**: OpenAI, Ollama (local), Anthropic
   - **TTS providers**: Web Speech API (free, browser-side), Google Cloud, ElevenLabs, Azure
   - **Enriched context**: Injects live telemetry + `RaceStrategyAnalyzer` insights (strategic advice on tyres, fuel, pace gaps, damage)
   - **Disabled by default** — enable via `png_config.json` `voice.enabled=true`
   - See `apps/backend/voice_layer/voice_handler.py` and `lib/config/schema/voice.py`

### Shared Library (`lib/`)

Reusable modules consumed by multiple apps:

- **`f1_types/`** — Packet dataclass definitions for F1 2023–2025 seasons (16 packet types)
- **`telemetry_manager/`** — Async UDP/TCP receiver manager and packet parser factory
- **`socket_receiver/`** — Base, UDP, TCP receiver implementations
- **`config/`** — Config loading from `png_config.json`/`app_settings.ini`; Pydantic validation models
- **`ipc/`** — ZeroMQ-based IPC with three patterns: pub/sub (`IpcPubSubBroker`, `IpcPublisherAsync`, `IpcSubscriber*`), req/rep (`IpcServer*`, `IpcClientSync`), and router/dealer (`IpcRouter`, `IpcDealerClient`, `IpcDealerAsync`); also provides `PngAppId` for app identity
- **`race_ctrl/`** — Race control event tracking: pit stops, car damage, tyre/wing changes; per-driver and per-session managers
- **`tyre_wear_extrapolator/`** — Linear regression tyre wear prediction
- **`delta/`** — Lap delta calculations
- **`openf1/`** — Integration with the external OpenF1 API
- **`wdt/`** — Watchdog timer for async task health monitoring (sync and async variants)
- **`web_server/`** — Shared async web server base (`BaseWebServer`) and uvicorn socket helper used by backend and save_viewer
- **`assets_loader/`** — Loads fonts and icons (team logos, tyre compounds) for Qt HUD
- **`event_counter/`** — Rate/count statistics tracking for telemetry performance metrics
- **`track_segment_info/`** — Track segment metadata and per-circuit sector boundary database

### Data Flow

```
F1 Game (UDP/TCP)
  → TelemetryManager (lib/telemetry_manager) parses packets
  → SessionState (state_mgmt_layer) aggregates and runs analysis
  → TelemetryWebServer (intf_layer) broadcasts via Socket.IO
  → Browser dashboard (apps/frontend) + HUD overlay (apps/hud)
```

### Configuration Management

**`png_config.json`** (auto-generated on first run by launcher) — single source of runtime config:

```json
{
  "capture": {
    "mode": "udp",              // "udp" or "tcp"
    "port": 20777
  },
  "telemetry_server": {
    "port": 8080,               // Backend HTTP/WebSocket port
    "https": false
  },
  "mcp": {
    "mcp_http_port": 4770       // MCP server HTTP transport port
  },
  "hud": {
    "enabled": true,            // Launch in-game overlay
    "selected_overlays": ["tyre_status", "lap_timer", "car_damage"]
  },
  "voice": {
    "enabled": false,           // Set to true to activate voice
    "stt_provider": "faster-whisper",  // "faster-whisper" (default), "openai", "google", "azure"
    "tts_provider": "web-speech-api",  // "web-speech-api" (default/free), "google", "elevenlabs", "azure"
    "llm_provider": "openai",          // "openai", "ollama", "anthropic"
    "api_key": "<YOUR_API_KEY>"        // Only needed for cloud STT/TTS/LLM
  }
}
```

**Pydantic validation** (via `lib/config/schema/`) ensures config correctness. See `.claude/commands/add-config-field.md` when adding new fields.

### Key Files

- **`meta/meta.py`** — Single source of version truth (`APP_VERSION`, `APP_NAME_SNAKE`)
- **`pyproject.toml`** — Poetry dependencies; Python 3.12–3.14; conditional imports for voice (`openai`, `librosa`, `soundfile`, `faster-whisper`)
- **`scripts/png.spec`** — PyInstaller spec (entry point, hidden imports, version injection)
- **`scripts/.pylintrc`** — Linting rules for pylint
- **`apps/backend/voice_layer/voice_handler.py`** — `VoiceHandler` orchestrator; STT/LLM/TTS pipeline
- **`apps/backend/voice_layer/strategy_analyzer.py`** — `RaceStrategyAnalyzer` enriches voice context with F1-specific race advice
- **`lib/config/schema/voice.py`** — `VoiceSettings` Pydantic model (all voice configuration fields)
- **`apps/mcp_server/mcp_server.py`** — `MCPBridge` (FastMCP server); registers tools
- **`apps/mcp_server/mcp_server/tools/`** — Individual tool implementations (one file per tool)

## Testing Strategy

### Test Organization

Tests are organized by module and test type:

```
tests/
├── tests_<module>.py           — Unit tests for core modules (run in parallel)
├── tests_openf1/
│   └── tests_openf1_integration.py  — Live API integration tests (marked with @pytest.mark.openf1)
└── tests_<feature>_serial.py   — Serial tests (sockets, processes, IPC; marked with @pytest.mark.serial)
```

### Test Markers & Markers Config

Defined in `pyproject.toml`:
- `@pytest.mark.serial` — Tests using real sockets, ports, or processes; **must run sequentially** (e.g., IPC tests, telemetry receiver tests)
- `@pytest.mark.openf1` — Tests that make real calls to OpenF1 API; **excluded by default** (network-dependent)

### Test Patterns

**Async tests** auto-marked with `asyncio_mode = "auto"`. Use `async def test_*()` directly:

```python
async def test_voice_handler_initialization():
    handler = VoiceHandler(config, session_state)
    assert handler.stt_provider is not None
```

**Serial tests** (IPC, sockets):

```python
@pytest.mark.serial
def test_ipc_pub_sub():
    # Uses real ZeroMQ sockets — must not run in parallel
    ...
```

**Fixtures** in `conftest.py` provide mocks and real instances:
- `voice_config` — VoiceSettings fixture
- `session_state` — Mock SessionState
- `test_telemetry_file` — Sample F1 packet capture

### Common Test Commands

```bash
# Full suite (parallel-safe, no OpenF1 tests)
poetry run pytest tests/

# Serial tests only (slower, but safe)
poetry run pytest tests/ -m serial

# Specific test by keyword
poetry run pytest tests/ -k "test_tyre_wear_extrapolation"

# Watch mode (re-run on file changes)
poetry run pytest tests/ --lf  # Last failed
poetry run pytest tests/ -x    # Stop at first failure

# Coverage by module
poetry run python scripts/coverage_ut.py      # Unit tests only
poetry run python scripts/coverage_integration_tests.py  # Serial + integration
```

## Development Procedures

These files define step-by-step procedures for common dev tasks. Read the relevant file before starting the task.

- `.claude/commands/perf-report.md` — Generate a performance metrics report from launcher logs. Use when analyzing latency, packet loss, or throughput.
- `.claude/commands/add-packet-type.md` — Scaffold a new F1 packet type (e.g., new season support). Wires across `lib/f1_types/` and `lib/telemetry_manager/`.
- `.claude/commands/new-overlay.md` — Scaffold a new HUD overlay widget. Use when adding a new in-game display panel.
- `.claude/commands/release-notes.md` — Generate user-facing release notes from git commits since last tag.
- `.claude/commands/add-mcp-tool.md` — Scaffold a new MCP tool in `apps/mcp_server/`. Includes registration and testing.
- `.claude/commands/add-config-field.md` — Add a new field to `png_config.json`. Includes Pydantic schema, validation, subsystem wiring, and tests.

## Common Patterns & Architecture

### IPC Communication

`lib/ipc/` provides three ZeroMQ patterns for inter-process communication:

- **Pub/Sub** — `IpcPublisherAsync` broadcasts; `IpcSubscriberAsync`/`IpcSubscriberSync` consume. **Used by launcher** to fan out state updates to all child processes (backend → HUD, MCP server, etc.).
- **Req/Rep** — `IpcClientSync` sends requests; `IpcServerSync`/`IpcServerAsync` handle them. Used for synchronous control commands (launcher → child process kill/restart).
- **Router/Dealer** — `IpcRouter` (server-side) paired with `IpcDealerClient`/`IpcDealerAsync` (client-side) for async many-to-one messaging.

**App identity**: `PngAppId` enum identifies each app (launcher, backend, hud, broker, mcp_server, save_viewer).

**Port allocation**: `get_free_tcp_port()` dynamically allocates free ports at runtime; all ports configured in `png_config.json`.

### Data Flow Patterns

**Telemetry ingestion** (F1 game → browser):
```
F1 Game (UDP/20777)
  → TelemetryManager (socket reception + parsing)
  → SessionState (aggregation + analysis)
  → Socket.IO event broadcast
  → Browser dashboard + HUD overlay
  → MCP server (subscribers get state updates)
```

**Voice pipeline** (user query → intelligent response):
```
Browser (voice_audio_final)
  → VoiceHandler (STT: faster-whisper/openai)
  → RaceStrategyAnalyzer (enriches with telemetry + advice)
  → LLM Provider (generates response)
  → VoiceToolRouter (routes to MCP tools if needed)
  → TTS Provider (synthesizes audio)
  → Browser TTS playback
```

### ConfigProvider Pattern

Configuration is centralized via `lib/config/config_loader.py` → `png_config.json`. Schema validation via Pydantic models in `lib/config/schema/`:

```python
# Load config (auto-validates against schema)
from lib.config.config_loader import config_loader
config = config_loader.get_config()

# Type-safe access with defaults
voice_enabled = config.voice.enabled if config.voice else False
mcp_port = config.mcp.mcp_http_port if config.mcp else 4770
```

When adding new config fields, use `.claude/commands/add-config-field.md` to ensure:
1. Schema validation in Pydantic model
2. Defaults in `png_config.json`
3. Subsystem wiring (apps that read this field)
4. Unit tests

### Telemetry State Management

`SessionState` in `apps/backend/state_mgmt_layer/session_state.py` is the single source of truth for all F1 telemetry:

- Aggregates parsed packets (position, motion, car status, lap data, etc.)
- Runs analysis: overtake detection, tyre wear prediction, damage tracking
- Publishes updates via ZeroMQ to HUD, MCP server, external clients
- Queried by REST API, MCP tools, voice handler

**Common pattern**: Apps subscribe to `SessionState` updates via IPC PubSub, or query it directly (backend only).

### Provider Pattern (Voice STT/TTS/LLM)

`apps/backend/voice_layer/providers.py` implements factory pattern:

```python
# STT provider factory
stt_provider = STTProviderFactory.create(provider_name, config)
transcript = await stt_provider.transcribe(audio_buffer)

# TTS provider factory
tts_provider = TTSProviderFactory.create(provider_name, config)
audio_bytes = await tts_provider.synthesize("Hello, racer!")

# LLM provider factory
llm_provider = LLMProviderFactory.create(provider_name, config)
response = await llm_provider.generate(messages, system_prompt)
```

Supported providers pluggable via config; new providers added by extending base classes and registering in factories.

## Development Workflow

### Before Opening a PR

1. **Run tests locally**: `poetry run pytest tests/ -m "not serial"` (fast check)
2. **Check serial tests**: `poetry run pytest tests/ -m serial` (if modifying IPC or telemetry)
3. **Lint**: `poetry run pylint --rcfile scripts/.pylintrc apps lib`
4. **Test the app**: `poetry run python -m apps.launcher` (or specific app)
5. **Verify version**: Check `meta/meta.py` updated if version bump needed

### Debugging Tips

**View live telemetry state**:
```bash
# Start backend in debug mode
poetry run python -m apps.backend --debug
# Open http://localhost:8080/debug or use MCP Inspector
```

**Check MCP tools**: `npx @modelcontextprotocol/inspector poetry run python -m apps.mcp_server -- --debug`

**Watch voice pipeline**: Enable logging in `apps/backend/voice_layer/voice_handler.py`

**Replay saved sessions**: Use `telemetry_replayer` to debug offline with real F1 data

### Contribution Guidelines

- **Small changes**: Direct PR (typos, minor fixes, docs)
- **Non-trivial changes**: Discuss first via GitHub Issues or Discord
- **Keep PRs focused**: Single concern, independently mergeable
- **Include tests**: Any new feature or fix should have test coverage

See `CONTRIBUTING.md` for full guidelines.

## Voice Integration

Complete two-way voice pipeline: **STT → LLM → TTS** with MCP tool integration. Disabled by default.

### Architecture

```
Browser (Web Audio API)
  → PCM chunks over WebSocket (voice_audio_chunk / voice_audio_final events)
  → VoiceHandler (apps/backend/voice_layer/voice_handler.py) accumulates buffer
  → STT Provider (faster-whisper/openai/google/azure) transcribes to text
  → RaceStrategyAnalyzer enriches context with live telemetry + strategic advice
  → LLM Provider (OpenAI/Ollama/Anthropic) generates response
  → VoiceToolRouter routes to MCP tools (get_session_info, get_race_table, etc.)
  → TTS Provider (Web Speech API/Google/ElevenLabs/Azure) synthesizes audio
  → Browser TTS speaks response
```

### Dynamic Voice Responses

**Before** (templated): "Tyre wear is 45%, 48%, 46%, 47%"

**After** (intelligent):
- Analyzes wear patterns + degradation rates
- Correlates with setup (brake balance, aerodynamics)
- Estimates pit window (laps remaining at current rate)
- Recommends strategic actions
- Response: "Front-left wearing 3% faster than rear — brake balance issue. You're at 45% average, so 15-20 laps before pit window."

See `DYNAMIC_VOICE_RESPONSES.md` for detailed examples and thresholds.

### MCP Tool Integration with Voice

8 tools registered in `apps/mcp_server/mcp_server/tools/`:
- `get_session_info` — current race, position, conditions
- `get_race_table` — driver standings with pace gaps
- `get_drivers_list` — all drivers in session
- `get_driver_lap_times` — lap-by-lap history
- `get_session_events_for_driver` — tyre changes, pit stops, damage
- `get_player_driver_info` — player position, fuel, damage
- `get_car_damage` — detailed damage breakdown
- `get_tyre_status` — wear, compound, temps

**VoiceToolRouter** in voice handler automatically routes voice queries to relevant tools.

### Configuration

Key `VoiceSettings` in `png_config.json`:
- `enabled` — `false` by default; `true` to activate
- `stt_provider` — `"faster-whisper"` (default, local GPU), `"openai"`, `"google"`, `"azure"`
- `tts_provider` — `"web-speech-api"` (default, free), `"google"`, `"elevenlabs"`, `"azure"`
- `llm_provider` — `"openai"`, `"ollama"` (local), `"anthropic"`
- `api_key` — API key for cloud providers
- `auto_announce_enabled` — TTS announces telemetry updates automatically
- `faster_whisper_model` — `"base"` (default), `"small"`, `"medium"`, `"large"`
- `faster_whisper_device` — `"cuda"` (GPU), `"cpu"` (default if no GPU)

### Enabling Voice

```json
{
  "voice": {
    "enabled": true,
    "stt_provider": "faster-whisper",    // Local, free, GPU-accelerated
    "tts_provider": "web-speech-api",    // Free, browser-side
    "llm_provider": "openai",
    "api_key": "<OPENAI_API_KEY>"
  }
}
```

For **local-only** (no API keys):
```json
{
  "voice": {
    "enabled": true,
    "stt_provider": "faster-whisper",
    "tts_provider": "web-speech-api",
    "llm_provider": "ollama",            // Requires local Ollama server
    "ollama_base_url": "http://localhost:11434"
  }
}
```

### WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `voice_audio_chunk` | Browser → Backend | Streaming PCM audio chunk |
| `voice_audio_final` | Browser → Backend | Last chunk; triggers pipeline |
| `voice_transcript` | Backend → Browser | Transcribed user text |
| `voice_response` | Backend → Browser | LLM-generated response text |

### Performance Notes

- **STT**: `faster-whisper` (~2–5s per 30s audio on GPU), OpenAI Whisper API (~1–2s but costs ~$0.02/min)
- **TTS**: `web-speech-api` (instant, in-browser), cloud TTS (1–3s)
- **LLM**: Ollama local (~5–10s, depends on model size), OpenAI API (~2–3s)

### Documentation

- `VOICE_QUICKSTART.md` — Quick enable guide
- `DYNAMIC_VOICE_RESPONSES.md` — Strategy analyzer details and thresholds
- `VOICE_COMMAND_REFERENCE.md` — All 8 MCP tools with examples
- `VOICE_INTEGRATION.md` — Full technical reference
- `LOCAL_LLM_QUICKSTART.md` — Ollama setup for local LLM inference

### Python Dependencies

`openai`, `librosa`, `soundfile`, `faster-whisper` — only loaded when `voice.enabled = true`
