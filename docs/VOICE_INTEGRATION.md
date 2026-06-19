# Voice Communication Integration

This document describes the two-way voice streaming integration for Pits n' Giggles, enabling real-time speech-to-text (STT) and text-to-speech (TTS) communication.

## Overview

The voice integration provides:

- **Speech-to-Text (STT)**: Capture microphone input, stream audio chunks to backend, get transcripts via OpenAI Whisper API
- **Text-to-Speech (TTS)**: Speak responses back to the user using browser Web Speech API
- **Real-time Audio Streaming**: WebSocket-based audio chunk transmission with minimal latency
- **Voice Configuration**: JSON-based settings for language, providers, timeouts, and audio formats

## Architecture

### Backend Voice Layer (`apps/backend/voice_layer/`)

The backend voice layer handles server-side voice processing:

```
apps/backend/voice_layer/
├── __init__.py
└── voice_handler.py        # Main voice handler (STT orchestration)
```

**VoiceHandler** (`voice_handler.py`):
- Accumulates audio chunks from client
- Converts float32 audio to PCM16 for transmission
- Calls OpenAI Whisper API for transcription
- Returns transcripts to client via Socket.IO events
- Handles audio resampling (any rate → 16kHz)

### Frontend Voice Handler (`apps/frontend/js/voiceHandler.js`)

Client-side audio handling:

```javascript
class VoiceHandler {
    // Microphone capture via Web Audio API
    async initialize()              // Request microphone permission, set up ScriptProcessor
    startRecording()                // Begin capturing audio
    stopRecording()                 // Finalize and send last chunk
    
    // Audio processing
    sendAudioChunk(audioData)       // Convert float32 → PCM16, accumulate chunks
    float32ToPCM16(float32Array)    // Audio format conversion
    _audio_to_wav_bytes(audio, sr)  // Create WAV file for API
    
    // Feedback
    speakTranscript(text)           // Use Web Speech API for TTS
    displayTranscript(text)         // Show transcript in UI
}
```

### Socket.IO Events

**Client → Server**:
- `voice-start` — Session start (client-side)
- `voice-audio-chunk` — Audio chunk with `{audio, is_final}` payload
- `voice-stop` — Session end (client-side)

**Server → Client**:
- `voice-transcript` — STT result `{text: "..."}` (one event per utterance)
- `voice-error` — Error message `{error: "..."}`

## Configuration

### JSON Configuration (`png_config.json`)

```json
{
    "Voice": {
        "enabled": false,                      // Enable/disable voice features
        "stt_provider": "openai",              // "openai", "google", "azure"
        "tts_provider": "web-speech-api",      // "web-speech-api", "google", "elevenlabs", "azure"
        "language": "en-US",                   // BCP 47 language code
        "sample_rate": 16000,                  // Audio sample rate (Hz)
        "chunk_duration_ms": 100,              // Audio chunk duration
        "audio_format": "pcm",                 // "pcm" or "wav"
        "vad_enabled": false,                  // Voice Activity Detection (future)
        "vad_threshold": 0.5,                  // VAD threshold (0.0-1.0)
        "api_key": "",                         // API key for provider (if needed)
        "timeout_seconds": 10,                 // STT processing timeout
        "auto_announce_enabled": true,         // Auto-speak transcripts
        "min_confidence": 0.7                  // Minimum confidence threshold
    }
}
```

### Pydantic Schema (`lib/config/schema/voice.py`)

```python
class VoiceSettings(ConfigDiffMixin, BaseModel):
    enabled: bool                              # Feature flag
    stt_provider: Literal["openai", "google", "azure"]
    tts_provider: Literal["web-speech-api", "google", "elevenlabs", "azure"]
    language: str                              # e.g., "en-US", "fr-FR"
    sample_rate: int                           # Typically 16000
    chunk_duration_ms: int                     # Milliseconds per chunk
    audio_format: Literal["wav", "pcm"]
    vad_enabled: bool
    vad_threshold: float                       # 0.0 to 1.0
    api_key: str
    timeout_seconds: int
    auto_announce_enabled: bool
    min_confidence: float                      # 0.0 to 1.0
```

## Setup & Usage

### Prerequisites

- Python 3.12+
- OpenAI API key (for Whisper STT)
- Poetry dependencies installed

### Enable Voice Features

1. **Set up OpenAI API Key**:
   ```bash
   # Get your API key from https://platform.openai.com/api-keys
   # Add to png_config.json:
   {
       "Voice": {
           "enabled": true,
           "api_key": "sk-..."
       }
   }
   ```

2. **Start the application**:
   ```bash
   poetry run python -m apps.launcher
   ```

3. **Access the UI**:
   - Open http://localhost:4768 in your browser
   - Look for the microphone button (🎤) in the top-right header

### Recording Workflow

1. **Click Microphone Button** — Starts microphone capture (turns red, shows "Recording...")
2. **Speak Your Query** — Audio is streamed to backend in 100ms chunks
3. **Release/Stop** — Click button again to stop and process
4. **View Transcript** — Result appears at bottom-left of screen
5. **Auto-Speak Response** — Browser speaks the transcript back (if enabled)

## Implementation Details

### Audio Capture (Client)

```javascript
// Web Audio API ScriptProcessor runs every 100ms
processor.onaudioprocess = (event) => {
    if (isRecording) {
        const audioData = event.inputBuffer.getChannelData(0);  // Float32
        sendAudioChunk(audioData);  // Send accumulated chunks every 500ms
    }
};
```

**Audio Format**:
- **Capture**: Float32 (±1.0 range), 16kHz sample rate
- **Transmission**: PCM16 (signed 16-bit integer), binary over Socket.IO
- **Processing**: Librosa resamples if needed, then converts to WAV for Whisper API

### STT Processing (Backend)

```python
async def process_audio_chunk(audio_bytes: bytes, is_final: bool) -> Optional[str]:
    # 1. Accumulate chunks
    self.audio_buffer = np.concatenate([audio_buffer, audio_bytes])
    
    # 2. Only process when is_final=True
    if not is_final:
        return None
    
    # 3. Resample to 16kHz
    audio_16k = librosa.resample(self.audio_buffer, target_sr=16000)
    
    # 4. Convert to WAV bytes
    wav_bytes = soundfile.write(audio_16k, sr=16000, format="WAV")
    
    # 5. Call Whisper API
    response = await openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=wav_bytes,
        language="en"
    )
    
    return response.text
```

### TTS Output (Client)

Using Web Speech API (browser-native, no API key required):

```javascript
speakTranscript(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.2;  // 20% faster
    speechSynthesis.speak(utterance);
}
```

## Troubleshooting

### Microphone Permission Denied
- **Symptom**: "Microphone error" message appears
- **Solution**: Check browser permissions. In browser settings, allow microphone for localhost:4768

### STT Timeout
- **Symptom**: "Processing..." hangs for 10+ seconds
- **Solution**: 
  - Check OpenAI API key is valid
  - Verify network connectivity to api.openai.com
  - Increase `timeout_seconds` in config if network is slow

### No Transcript Appears
- **Symptom**: Audio sent but no transcript received
- **Solution**:
  - Verify `Voice.enabled: true` in png_config.json
  - Check backend logs: `grep -i voice logs/backend.log`
  - Ensure audio contains clear speech (not silence)

### Audio Quality Issues
- **Symptom**: Transcripts are garbled or incomplete
- **Solution**:
  - Check microphone hardware and volume
  - Enable echo cancellation (enabled by default)
  - Reduce background noise
  - Verify sample rate matches config (default 16000 Hz)

## API Costs

### OpenAI Whisper
- **Cost**: $0.02 per minute of audio
- **Estimate**: ~$0.033 per 100 utterances (assuming 1.5s avg)
- **Limit**: None (pro-rata billing)

### Web Speech API (TTS)
- **Cost**: Free (browser-native, no API calls)
- **Voices**: Limited (OS-dependent)

## Future Enhancements

### Phase 2: Server-side TTS
- Add Google Cloud TTS or ElevenLabs support
- Stream audio response back to client via Socket.IO chunks
- Client-side Web Audio API playback

### Phase 3: Advanced Features
- Voice Activity Detection (VAD) to auto-stop at silence
- Voice commands ("show me pit strategy for Leclerc")
- Context-aware responses (telemetry-aware TTS)
- Multi-language support with auto-detection

### Phase 4: Command Recognition
- Parse transcripts as voice commands
- Execute actions based on speech patterns
- Integration with race strategy layer

## Testing

### Enable Debug Logging
```bash
# Backend logs voice events
poetry run python -m apps.backend --replay-server 2>&1 | grep -i voice
```

### Test Manually
1. Start backend: `poetry run python -m apps.backend --replay-server`
2. Open http://localhost:4768
3. Click 🎤 button
4. Speak: "Hello Pits n' Giggles"
5. Watch console for transcript and Socket.IO events

### Test with Replay
```bash
# Send F1 telemetry data while testing voice
poetry run python -m apps.dev_tools.telemetry_replayer --file-name example.f1pcap
```

## Files Added/Modified

### New Files
- `lib/config/schema/voice.py` — VoiceSettings Pydantic model
- `apps/backend/voice_layer/__init__.py` — Voice layer module
- `apps/backend/voice_layer/voice_handler.py` — STT handler
- `apps/frontend/js/voiceHandler.js` — Client-side audio capture
- `apps/frontend/js/voiceInit.js` — Voice initialization
- `apps/frontend/css/voice.css` — Voice UI styling
- `docs/VOICE_INTEGRATION.md` — This document

### Modified Files
- `lib/config/schema/png.py` — Added Voice field to PngSettings
- `apps/backend/intf_layer/telemetry_web_server.py` — Added voice Socket.IO handlers
- `apps/frontend/html/driver-view.html` — Added voice button and script loads
- `png_config.json` — Added Voice configuration section
- `pyproject.toml` — Added openai, librosa, soundfile dependencies

## Security Considerations

⚠️ **API Key Storage**:
- Never commit API keys to git
- Use environment variables or secure config files
- Voice feature disabled by default (enable explicitly)

⚠️ **Audio Privacy**:
- Audio chunks are sent to OpenAI Whisper API
- Review OpenAI's data retention policy: https://openai.com/privacy
- Consider disabling auto-announce for sensitive environments

⚠️ **Microphone Permissions**:
- Browser prompts user before accessing microphone
- User can revoke permission at any time in browser settings
