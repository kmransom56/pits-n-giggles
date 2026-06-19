# SessionState Integration in MCP Server

## Overview

The MCP server now supports injection of live F1 race telemetry via `SessionState`. This eliminates hardcoded mock data and enables real-time queries of driver data, tire wear, fuel levels, pit strategy, and other race telemetry.

## Changes Made

### 1. Updated `create_mcp_server()` Function

**Before:**
```python
def create_mcp_server(voice_config: Optional[VoiceSettings] = None) -> FastMCP:
```

**After:**
```python
def create_mcp_server(
    voice_config: Optional[VoiceSettings] = None, 
    session_state: Optional[SessionState] = None
) -> FastMCP:
```

### 2. Voice State Dictionary

The internal `voice_state` dict now contains session_state for tool access:

```python
voice_state = {
    "handler": voice_handler,
    "config": voice_config,
    "session_state": session_state  # NEW: Optional live telemetry
}
```

### 3. Replaced `search_race_data` Implementation

**Old Behavior:** Returned hardcoded mock driver data

**New Behavior:**
- If `session_state` is None: Returns empty results with note "No live race session available"
- If `session_state` provided: Queries `session_state.m_driver_data` for live telemetry

#### Supported Search Types

| Type | Data | Source |
|------|------|--------|
| `general` | All drivers with position, tire compound, tire wear, fuel | `DataPerDriver.m_driver_info`, `m_tyre_info`, `m_car_info` |
| `tires` | Driver name, average tire wear, pit recommendation | Calculated from individual tire wear values |
| `fuel` | Driver name, fuel remaining in liters | `DataPerDriver.m_car_info.m_fuel_in_tank` |
| `strategy` | Driver name, compound, pit stop history | `DataPerDriver.m_pit_info`, `m_tyre_info` |

#### Tire Wear Recommendation Logic

```python
if tire_wear_avg > 70:
    recommendation = "pit_soon"
elif tire_wear_avg > 50:
    recommendation = "monitor"
else:
    recommendation = "continue"
```

### 4. Driver Number Filtering

All search types support optional `driver_number` parameter:

```python
# Get tire wear for specific driver
results = await search_race_data(
    query="Leclerc tire wear",
    search_type="tires",
    driver_number=16
)
```

## Usage Examples

### Without SessionState (Default)

```python
from apps.backend.mcp_server.voice_mcp import create_mcp_server
from lib.config.schema.voice import VoiceSettings

config = VoiceSettings(enabled=True)
server = create_mcp_server(config)  # No live telemetry
server.run()
```

Result: `search_race_data` returns empty results with source="no_session"

### With SessionState (Live Telemetry)

```python
from apps.backend.mcp_server.voice_mcp import create_mcp_server
from apps.backend.state_mgmt_layer.session_state import SessionState
from lib.config.schema.voice import VoiceSettings

# Load F1 telemetry (from file, UDP stream, etc.)
session_state = SessionState()
# ... populate session_state with driver data ...

config = VoiceSettings(enabled=True)
server = create_mcp_server(config, session_state=session_state)
server.run()
```

Result: `search_race_data` queries live driver data and returns real telemetry

## Data Access Pattern

The implementation uses this pattern to safely access nested driver attributes:

```python
# Example: Extract tire wear
if hasattr(driver_data.m_tyre_info, 'm_tyre_wear'):
    tw = driver_data.m_tyre_info.m_tyre_wear
    if tw:
        tire_wear = {
            "fl": int(tw.m_front_left) if hasattr(tw, 'm_front_left') else 0,
            "fr": int(tw.m_front_right) if hasattr(tw, 'm_front_right') else 0,
            "rl": int(tw.m_rear_left) if hasattr(tw, 'm_rear_left') else 0,
            "rr": int(tw.m_rear_right) if hasattr(tw, 'm_rear_right') else 0,
        }
```

This provides:
- **Graceful degradation** if attributes missing
- **Type safety** with hasattr checks
- **Safe defaults** (0 values for missing data)

## Error Handling

```python
# If SessionState unavailable
{
    "results": [],
    "query_type": "general",
    "result_count": 0,
    "note": "No live race session available"
}

# If SessionState available but query fails
{
    "results": [],
    "query_type": "general",
    "error": "Error querying SessionState: [details]",
    "result_count": 0
}
```

## Integration with Process Voice Command

The `process_voice_command` tool with `auto_search=True` will now:

1. Call `search_race_data` with auto-detected search_type
2. Receive live telemetry from SessionState (if available)
3. Pass real driver data to LLM context
4. Generate contextually-aware responses based on current race state

## Files Modified

- `apps/backend/mcp_server/voice_mcp.py` — Added session_state parameter, replaced mock search_race_data
- `docs/MCP_INTEGRATION.md` — Added SessionState integration guide

## Testing

Run verification tests:

```bash
cd /home/keith/pits-n-giggles
poetry run python -c "
from apps.backend.mcp_server.voice_mcp import create_mcp_server
from lib.config.schema.voice import VoiceSettings
import inspect

# Test: Parameter present
sig = inspect.signature(create_mcp_server)
params = list(sig.parameters.keys())
assert 'session_state' in params
print('✓ SessionState parameter present')

# Test: Server creation
config = VoiceSettings(enabled=True)
server = create_mcp_server(config)
print('✓ Server created successfully')
"
```

## Next Steps

1. **Live F1 Data**: Integrate with actual F1 telemetry parser
2. **Performance**: Monitor query latency with 20+ drivers
3. **Caching**: Consider caching frequently-accessed driver data
4. **Extended Search**: Add "weather", "standings", "lap_times" search types
5. **LLM Integration**: Complete LLMProvider implementation for live responses
