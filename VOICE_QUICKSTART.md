# 🎤 Voice Features Quick Start Guide

## What Is This?

Two-way voice communication for Pits n' Giggles! Speak to your F1 racing app, get transcripts, and hear responses.

## 5-Minute Setup

### Step 1: Get an OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-`)

### Step 2: Enable Voice in Config

Edit `png_config.json`:

Find this section:
```json
{
    "Voice": {
        "enabled": false,
```

Change to:
```json
{
    "Voice": {
        "enabled": true,
        "api_key": "sk-your-api-key-here",
```

### Step 3: Start the App

```bash
poetry run python -m apps.launcher
```

Or just the backend:
```bash
poetry run python -m apps.backend --replay-server
```

### Step 4: Use Voice

1. Open http://localhost:4768 in Chrome or Safari
2. Look for the **🎤 microphone button** in the top-right header
3. Click it to **start recording** (button turns red)
4. **Speak your message** (e.g., "What's Leclerc's fuel load?")
5. Click again to **stop recording**
6. See your **transcript appear** at the bottom-left
7. **Hear the response spoken** back to you

## Features

✨ **Speech-to-Text**: Converts your voice to text using OpenAI Whisper
🔊 **Text-to-Speech**: Speaks the transcript back using browser Web Speech API
⚡ **Real-time Streaming**: Audio sent to backend in 100ms chunks
🎨 **Beautiful UI**: Red pulsing button, status messages, smooth animations
📱 **Works Everywhere**: Any browser with microphone support

## Configuration Options

Edit `png_config.json` to customize:

```json
"Voice": {
    "enabled": true,                      // Turn on/off
    "language": "en-US",                  // Language (en-US, fr-FR, etc.)
    "sample_rate": 16000,                 // Audio quality (Hz)
    "auto_announce_enabled": true,        // Auto-speak responses
    "timeout_seconds": 10,                // Max processing time
    "api_key": "sk-..."                   // Your OpenAI key
}
```

## Cost Estimate

- **~$0.02 per minute** of audio sent to OpenAI
- Typical usage: ~15 seconds per query = ~$0.005 per question
- Test for free with small audio samples

## Troubleshooting

### "Microphone error: Permission denied"
→ Browser blocked microphone access
→ Solution: Check browser settings → Privacy → Microphone → Allow localhost:4768

### "Processing..." for 10+ seconds
→ OpenAI API is slow or unreachable
→ Solution: Check API key is correct, verify internet connection

### Transcript is garbled
→ Microphone picking up background noise
→ Solution: Reduce background noise, speak clearly

### Nothing happens when clicking button
→ Voice might not be enabled or loaded
→ Solution: Check console (F12 → Console tab) for errors

## What's Under the Hood?

```
You: "Hello"
    ↓
🎙️ Browser captures audio (Web Audio API)
    ↓
📤 Sends to backend (Socket.IO)
    ↓
🧠 OpenAI Whisper STT API processes
    ↓
📥 Backend sends transcript back
    ↓
🔊 Browser speaks it back
    ↓
You: *hears* "Hello"
```

## File Changes

**New Files** (7):
- `lib/config/schema/voice.py` — Configuration
- `apps/backend/voice_layer/voice_handler.py` — Backend processing
- `apps/frontend/js/voiceHandler.js` — Browser audio capture
- `apps/frontend/js/voiceInit.js` — Voice initialization
- `apps/frontend/css/voice.css` — Styling
- `docs/VOICE_INTEGRATION.md` — Full documentation
- `docs/VOICE_IMPLEMENTATION_SUMMARY.md` — Implementation details

**Modified Files** (5):
- `lib/config/schema/png.py` — Added Voice config field
- `apps/backend/intf_layer/telemetry_web_server.py` — Voice Socket.IO handlers
- `apps/frontend/html/driver-view.html` — Voice button + scripts
- `png_config.json` — Voice section added
- `pyproject.toml` — Added dependencies (openai, librosa, soundfile)

## API Costs

| Provider | Cost | When Used |
|----------|------|-----------|
| OpenAI Whisper (STT) | $0.02/min | Every time you speak |
| Web Speech API (TTS) | Free | Always (browser-native) |

## Safe to Try?

✅ **Yes!** Voice is **disabled by default**
✅ No changes to existing features
✅ Fully backward compatible
✅ Costs only incurred when explicitly enabled

## Next Steps

1. ✅ Enable voice in config (see Step 2 above)
2. Start app and test
3. Report any issues on GitHub
4. Future: Voice commands, better TTS, multi-language support

## Need Help?

- Read full docs: `docs/VOICE_INTEGRATION.md`
- Check browser console: Press F12 → Console tab
- Review backend logs: Look for "voice" in logs
- Test manually: Create small 5-second audio sample

---

**That's it!** You now have voice communication in Pits n' Giggles. 🎉

Have fun racing with voice! 🏁
