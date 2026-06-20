# 🎤 Voice Command Reference

Complete guide to voice commands available in Pits n' Giggles with full MCP tool integration.

## Quick Examples

Try saying any of these commands into the microphone:

```
"What's the tyre wear?"
"How much fuel is left?"
"Who's in the lead?"
"Show me the grid"
"What drivers are racing?"
"Do I have any penalties?"
"What's the track temperature?"
"Show the damage report"
"What's my position?"
"Tell me my lap time"
```

---

## Command Categories

### 🛞 Tyre & Compound (get_player_tyre_wear / get_tyre_wear)

**Intent Keywords:** tyre, tire, wear, compound, stint

**What it does:** Fetches current tyre wear percentage, age, and compound.

**Voice commands:**
- "What's the tyre wear?"
- "Show my tyre compound"
- "How old are my tyres?"
- "Are my tyres wearing evenly?"
- "What's the tyre age?"

**Response includes:**
- Tyre compound (soft, medium, hard)
- Tyre age (laps on current set)
- Wear % for each corner (FL, FR, RL, RR)
- Average wear rate

---

### ⛽ Fuel Management (get_player_fuel_info / get_fuel_info)

**Intent Keywords:** fuel, burn, laps remaining, fuel load

**What it does:** Fetches remaining fuel, tank capacity, and burn rate.

**Voice commands:**
- "How much fuel is left?"
- "How many laps can I do?"
- "What's the fuel burn rate?"
- "Do I need to pit?"
- "How much fuel can I carry?"

**Response includes:**
- Fuel remaining (kg)
- Laps remaining at current burn rate
- Tank capacity
- Last lap burn rate
- Current burn rate

---

### 🏁 Race Standings (get_race_table)

**Intent Keywords:** position, gap, delta, standings, leader

**What it does:** Fetches current race standings with time gaps.

**Voice commands:**
- "What are the standings?"
- "Who's in the lead?"
- "How far back is P2?"
- "What's the gap to the leader?"
- "Show me the top 5"

**Response includes:**
- Position (1-20)
- Driver name
- Team
- Time gap to leader
- Championship points

---

### 👥 Drivers List (get_drivers_list)

**Intent Keywords:** drivers list, grid, who's racing, field

**What it does:** Lists all drivers currently in the session.

**Voice commands:**
- "Who's in this race?"
- "Show the full grid"
- "How many drivers are racing?"
- "List all competitors"

**Response includes:**
- Driver name
- Team
- Car number
- Current status (racing, retired, dnf)

---

### ⏱️ Lap Times (get_driver_lap_times)

**Intent Keywords:** lap time, sector, fastest lap

**What it does:** Fetches lap history with sector times.

**Voice commands:**
- "What's my lap time?"
- "How fast was my last lap?"
- "What's my best lap?"
- "Show me my sector times"
- "How am I doing on pace?"

**Response includes:**
- Current lap number
- Last lap time
- Best lap time
- Sector 1, 2, 3 times
- Personal best per sector

---

### 📍 Player Info (get_player_driver_info)

**Intent Keywords:** driver info, my info, player info, who am I

**What it does:** Fetches your current status.

**Voice commands:**
- "What's my info?"
- "Who am I?"
- "What's my position?"
- "How many points do I have?"
- "What team am I on?"

**Response includes:**
- Your name
- Team
- Current position
- Championship points
- Status (racing, retired, etc.)

---

### 🚗 Car Damage (get_car_damage)

**Intent Keywords:** damage, wing, floor, gearbox, engine, broken, puncture

**What it does:** Fetches current vehicle damage status.

**Voice commands:**
- "Do I have damage?"
- "What's the damage report?"
- "Is my wing damaged?"
- "Check engine status"
- "Do I have a puncture?"

**Response includes:**
- Tyre damage
- Brake damage
- Engine damage
- Wing damage (front/rear)
- Other component status

---

### 🚦 Race Events (get_session_events_for_driver)

**Intent Keywords:** session event, penalty, safety car, pit stop, incident

**What it does:** Fetches penalties, pit stop count, and incidents.

**Voice commands:**
- "Do I have any penalties?"
- "How many pit stops?"
- "What incidents have I had?"
- "Show my warnings"

**Response includes:**
- Active penalties
- Total incident count
- Pit stop count
- Race control messages

---

### 🌡️ Session Info (get_session_info)

**Intent Keywords:** weather, temperature, rain, track temp, conditions

**What it does:** Fetches track and weather conditions.

**Voice commands:**
- "What's the weather?"
- "How hot is the track?"
- "What's the air temperature?"
- "Are we in the rain?"
- "What are the conditions?"

**Response includes:**
- Circuit name
- Session type (race, qualify, practice)
- Air temperature
- Track temperature
- Weather (clear, rain, cloudy, etc.)

---

## Voice + MCP Integration

The voice system uses `VoiceToolRouter` to intelligently classify your speech and fetch data directly from SessionState:

```
You speak: "What's the tyre wear?"
    ↓
STT: Transcribes to text
    ↓
Router: Classifies intent as "tyre_wear"
    ↓
SessionState: Fetches `m_tyre_wear_data` from player driver
    ↓
LLM: "Your tyres are wearing at 45% average with medium compound..."
    ↓
TTS: Speaks response
```

**No API calls needed** — all queries fetch from **live in-memory SessionState**, no cloud latency.

---

## Configuration

Enable voice in `png_config.json`:

```json
{
  "Voice": {
    "enabled": true,
    "stt_provider": "faster-whisper",
    "whisper_device": "cuda",
    "tts_provider": "pyttsx3",
    "llm_provider": "ollama",
    "llm_base_url": "http://localhost:11434",
    "llm_model": "mistral"
  }
}
```

---

## Performance

| Metric | Value |
|--------|-------|
| STT latency | 1-2s (faster-whisper on GPU) |
| Data fetch | <100ms (SessionState in-memory) |
| LLM response | 2-5s (Ollama Mistral-7B on GPU) |
| TTS latency | ~500ms (pyttsx3) |
| **Total end-to-end** | **4-9 seconds** |

---

## Troubleshooting

### "Intent not recognized"
→ The router didn't match keywords; falls back to `search_race_data`
→ Try rephrasing with keywords from the command list above

### "No session data"
→ SessionState is empty (no live telemetry)
→ Make sure a race session is running in the F1 game

### "Audio playback error"
→ Backend didn't synthesize audio
→ Check backend logs: `grep "synthesize" <log>`

### "Microphone permission denied"
→ Browser blocked microphone access
→ Allow in Privacy → Microphone in browser settings

---

## Advanced: Custom Queries

Add new query keywords by editing `VoiceToolRouter.INTENT_MAP` in:
- `apps/backend/mcp_server/voice_mcp.py`

Example — add "fuel load" as fuel query:
```python
(["fuel", "burn", "laps remaining", "fuel load"], "fuel"),
```

---

## See Also

- [VOICE_QUICKSTART.md](VOICE_QUICKSTART.md) — 5-minute setup guide
- [VOICE_INTEGRATION.md](VOICE_INTEGRATION.md) — Full architecture
- [MCP_QUICKSTART.md](MCP_QUICKSTART.md) — MCP server testing with Inspector
