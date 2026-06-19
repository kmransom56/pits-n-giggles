# MIT License
#
# Copyright (c) [2025] [Ashwin Natarajan]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""MCP server launcher for Pits n' Giggles voice integration."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.config.schema.voice import VoiceSettings
from .voice_mcp import run_mcp_server

logger = logging.getLogger(__name__)


def launch_mcp_server(
    stt_provider: str = "faster-whisper",
    tts_provider: str = "web-speech-api",
    whisper_device: str = "cuda",
    whisper_model_size: str = "base",
    port: int = 4770,
    debug: bool = False,
):
    """
    Launch the MCP server with specified configuration.

    Args:
        stt_provider: STT provider ("faster-whisper" or "openai")
        tts_provider: TTS provider ("web-speech-api" or "pyttsx3")
        whisper_device: GPU device ("cuda" or "cpu")
        whisper_model_size: Whisper model size (tiny, base, small, medium, large)
        port: Port to run MCP server on
        debug: Enable debug logging
    """
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="[%(asctime)s] %(name)s - %(levelname)s - %(message)s",
    )

    # Create voice configuration
    config = VoiceSettings(
        enabled=True,
        stt_provider=stt_provider,
        tts_provider=tts_provider,
        whisper_device=whisper_device,
        whisper_model_size=whisper_model_size,
        language="en-US",
        sample_rate=16000,
        timeout_seconds=10,
    )

    logger.info("=" * 70)
    logger.info("🎤 Pits n' Giggles Voice MCP Server")
    logger.info("=" * 70)
    logger.info(f"STT Provider: {stt_provider}")
    logger.info(f"TTS Provider: {tts_provider}")
    logger.info(f"Whisper Device: {whisper_device}")
    logger.info(f"Whisper Model: {whisper_model_size}")
    logger.info(f"Port: {port}")
    logger.info("=" * 70)
    logger.info("\nMCP Protocol: stdio (standard input/output)")
    logger.info("Tools available: 8")
    logger.info("  • transcribe_audio - Speech-to-text via configurable STT")
    logger.info("  • synthesize_speech - Text-to-speech via configurable TTS")
    logger.info("  • search_race_data - Query F1 race telemetry (auto-used by voice commands)")
    logger.info("  • process_voice_command - Process voice commands with auto-search + LLM context")
    logger.info("  • list_stt_providers - Query available STT providers")
    logger.info("  • list_tts_providers - Query available TTS providers")
    logger.info("  • list_voice_config - Get current voice system configuration")
    logger.info("  • get_voice_status - Monitor voice system health")
    logger.info("\nStarting MCP server on stdio transport...")
    logger.info("=" * 70)

    # Run the MCP server (uses stdio by default for MCP protocol)
    try:
        from .voice_mcp import create_mcp_server
        app = create_mcp_server(config)

        # FastMCP.run() is synchronous and uses stdio transport by default
        # This is the correct way to run an MCP server
        app.run()
    except KeyboardInterrupt:
        logger.info("\n\nServer shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Launch Pits n' Giggles Voice MCP Server"
    )
    parser.add_argument(
        "--stt-provider",
        default="faster-whisper",
        choices=["faster-whisper", "openai"],
        help="STT provider",
    )
    parser.add_argument(
        "--tts-provider",
        default="web-speech-api",
        choices=["web-speech-api", "pyttsx3"],
        help="TTS provider",
    )
    parser.add_argument(
        "--whisper-device",
        default="cuda",
        choices=["cuda", "cpu"],
        help="GPU device for Whisper",
    )
    parser.add_argument(
        "--whisper-model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=4770,
        help="Port to run MCP server on",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    launch_mcp_server(
        stt_provider=args.stt_provider,
        tts_provider=args.tts_provider,
        whisper_device=args.whisper_device,
        whisper_model_size=args.whisper_model,
        port=args.port,
        debug=args.debug,
    )
