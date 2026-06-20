# 🎤 Dynamic Voice Responses

No more "canned answers" — Pits n' Giggles voice now provides intelligent, strategic F1 race engineering advice.

---

## What Changed

### Before (Templated Responses)
```
You: "What's the tyre wear?"
System: "Tyre wear is 45%, 48%, 46%, 47%"
```

### After (Dynamic Strategy Analysis)
```
You: "What's the tyre wear?"
System: "Front-left is wearing 3% faster than the rear — could be a brake balance issue.
         You're at 45% average wear, so you've got 15-20 laps left before considering a pit stop."
```

---

## How It Works

### 1. **Race Strategy Analyzer**
Analyzes live telemetry and identifies strategic situations:

| Metric | Thresholds | Action |
|--------|-----------|--------|
| **Tyre wear** | >90% (critical), >70% (warning), >50% (monitoring) | Pit window opens, setup issues, degradation cliff |
| **Fuel** | <1.5 laps (critical), <2.5 laps (warning) | Pit immediately, begin pit planning |
| **Pace gaps** | <0.5s (competitive), >3s (concerning) | Push harder, maintain, defensive strategy |
| **Damage** | Engine >50%, wing damage | Pit for inspection, performance impact |

### 2. **Enriched Context**
Voice handler builds comprehensive race context:

```
=== RACE CONTEXT ===
Session: race at Silverstone
You: P2 (Lewis Hamilton - Mercedes)
Tyre wear: 45% avg (soft compound)
Fuel: 3.2 laps remaining
Conditions: Clear (Track 52°C, Air 21°C)

=== STRATEGIC ANALYSIS ===
[INFO] You're on pace with the leader — maintain current strategy
[WARNING] P2 is closing in +2.1s — be careful on errors
```

### 3. **Intelligent LLM Synthesis**
Enhanced system prompt drives F1-focused responses:

- **Explains the why:** "pit now because..." not "pit"
- **Professional tone:** Race engineer language, not generic AI
- **Correlates data:** Combines tyre wear + pit history + pace gap
- **Strategic:** Recommends actions, not just reports metrics
- **Conversational:** Natural language, not templated

---

## Example Voice Queries & Dynamic Responses

### Tyre Management
```
You: "Show my tyre status"

System: "Your tyres are at 45% average wear on a soft compound.
        The rear is degrading 2% slower than the front —
        suggests slight understeer compensation in setup.
        Pit window opens in 10-15 laps when wear hits 70%."
```

### Fuel Strategy
```
You: "How much fuel do I have?"

System: "3.2 laps of fuel at your current burn rate (1.7kg/lap).
        You're running lean mix — consider switching to standard in 5 laps
        if you want to extend the stint without pit. Current pace is solid."
```

### Pace Analysis
```
You: "How close is the leader?"

System: "P1 has a 2.1-second gap — manageable but widening slightly.
        They just pitted so their tyres are fresh. Consider attacking
        in the next 3-4 laps while your tyres warm up, then manage."
```

### Car Damage
```
You: "Do I have any damage?"

System: "Minor wing damage on the rear from lap 8 contact.
        You're losing about 0.3 seconds per lap on straights.
        Not critical yet, but consider pitting if there's a pit stop window."
```

### Pit Window Analysis
```
You: "What's my pit strategy?"

System: "You're optimal for a two-stop. First stop in 12 laps when
        tyres hit 70% wear. Take mediums. Second stop around lap 45
        for softs. Fuel allows it with standard fuel mix."
```

---

## Implementation

### Files Modified

| File | Change |
|------|--------|
| `apps/backend/voice_layer/strategy_analyzer.py` | **NEW** — Strategic analysis engine |
| `apps/backend/voice_layer/voice_handler.py` | Added `build_enriched_context()` method |
| `apps/backend/voice_layer/providers.py` | Enhanced Ollama LLM system prompt |
| `apps/backend/mcp_server/voice_mcp.py` | Integrated enriched context into `process_voice_command` |

### Architecture

```
Voice Input (User speaks)
  ↓
STT (faster-whisper)
  ↓
Intent Classification (VoiceToolRouter)
  ↓
SessionState Fetch (MCP tools)
  ↓
ENRICHMENT: RaceStrategyAnalyzer.analyze_*()
  ↓
Enriched Context Build (race state + strategic advice)
  ↓
LLM Synthesis (Ollama with F1 engineer prompt)
  ↓
Dynamic Response (strategic, conversational)
  ↓
TTS (pyttsx3)
  ↓
Audio Playback
```

---

## Strategy Detection Examples

### Tyre Wear Analysis
Detects:
- Critical wear (>90%) → pit immediately
- High wear (>70%) → pit soon
- Uneven wear (front/rear variance >15%) → setup issue suggestion

### Fuel Management
Detects:
- Critical fuel (<1.5 laps) → pit for fuel
- Warning level (<2.5 laps) → plan pit window
- Burn rate trend → extrapolates remaining laps

### Pace Analysis
Detects:
- Gap closing (<0.5s) → competitive, push
- Gap stable (0.5-2s) → manage gap
- Gap extending (>3s) → review strategy or push harder
- Leader advantage → assess pit strategy impact

### Car Damage
Detects:
- Engine damage >50% → risk of failure
- Wing damage → aerodynamic loss quantified
- Brake damage → performance impact noted

---

## Configuration

Voice dynamic responses are enabled by default. Configure in `png_config.json`:

```json
{
  "Voice": {
    "enabled": true,
    "stt_provider": "faster-whisper",
    "llm_provider": "ollama",
    "llm_model": "mistral",
    "tts_provider": "pyttsx3"
  }
}
```

---

## Performance

| Component | Latency |
|-----------|---------|
| STT (faster-whisper) | 1-2s |
| Intent classification | <100ms |
| Data fetch (SessionState) | <100ms |
| Strategy analysis | <50ms |
| LLM synthesis (Ollama) | 2-5s |
| TTS (pyttsx3) | ~500ms |
| **Total end-to-end** | **4-9 seconds** |

---

## Testing Dynamic Responses

```bash
# 1. Start the app
poetry run python -m apps.launcher

# 2. Open http://localhost:4768
# 3. Click 🎤 Voice button
# 4. Try strategic questions:

"Pit analysis"          # Get full pit strategy
"Tyre degradation?"     # Tyre wear + extrapolation
"Fuel plan"             # Remaining laps + strategy
"Pace report"           # Gap analysis + recommendations
"Damage check"          # Vehicle status + impact
"My race position"      # Championship context (if available)
```

---

## Extending Strategy Analysis

Add new strategic advisors by extending `RaceStrategyAnalyzer`:

```python
@staticmethod
def analyze_tire_degradation(tyre_data: dict, laps_completed: int) -> Optional[StrategyAdvice]:
    """Custom strategy analyzer."""
    # Your logic here
    return StrategyAdvice(
        priority="warning",
        category="pit_window",
        advice="...",
        reasoning="...",
    )
```

Then call in `VoiceHandler.build_enriched_context()`:

```python
advice = RaceStrategyAnalyzer.analyze_tire_degradation(...)
if advice:
    advice_list.append(advice)
```

---

## See Also

- [VOICE_COMMAND_REFERENCE.md](VOICE_COMMAND_REFERENCE.md) — All voice commands
- [F1_VOICE_ENGINEERING_REFERENCE.md](F1_VOICE_ENGINEERING_REFERENCE.md) — F1 strategy frameworks
- [VOICE_INTEGRATION.md](VOICE_INTEGRATION.md) — Architecture & setup
