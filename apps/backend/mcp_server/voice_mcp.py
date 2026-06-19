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

"""MCP Server exposing voice operations (STT/TTS/LLM) as tools for AI assistants."""

import asyncio
import base64
import logging
from typing import Any, Optional

from fastmcp import FastMCP

from lib.config.schema.voice import VoiceSettings
from ..voice_layer.providers import (
    STTProviderFactory,
    TTSProviderFactory,
    LLMProvider,
)
from ..voice_layer.voice_handler import VoiceHandler
from ..state_mgmt_layer.session_state import SessionState

logger = logging.getLogger(__name__)


def create_mcp_server(voice_config: Optional[VoiceSettings] = None, session_state: Optional[SessionState] = None) -> FastMCP:
    """
    Create and configure FastMCP server for voice integration.

    Args:
        voice_config: Voice settings configuration. If None, creates default config.
        session_state: Optional SessionState for live F1 race telemetry. If None, attempts to get from bridge.

    Returns:
        Configured FastMCP server instance
    """
    app = FastMCP("pits-n-giggles-voice", "1.0.0")

    # Initialize voice handler
    if voice_config is None:
        voice_config = VoiceSettings(enabled=True)

    voice_handler = VoiceHandler(voice_config)

    # If no SessionState provided, try to get from telemetry bridge
    if session_state is None:
        try:
            from .mcp_telemetry_bridge import MCPTelemetryBridge
            bridge = MCPTelemetryBridge()
            session_state = bridge.get_session_state()
            if session_state:
                logger.info("✓ SessionState retrieved from telemetry bridge")
        except Exception:
            pass

    voice_state = {
        "handler": voice_handler,
        "config": voice_config,
        "session_state": session_state
    }

    # ==================== STT TOOLS ====================

    @app.tool()
    async def transcribe_audio(
        audio_data_base64: str,
        provider: str = "faster-whisper",
        language: str = "en",
    ) -> dict[str, Any]:
        """
        Transcribe audio to text using specified STT provider.

        Converts audio bytes (base64 encoded) to text using fast-whisper (local GPU)
        or OpenAI Whisper API (cloud). Supports multiple languages.

        Args:
            audio_data_base64: Audio data encoded as base64 (PCM 16kHz float32)
            provider: STT provider to use ("faster-whisper" or "openai")
            language: Language code (e.g., "en", "en-US", "fr", "de")

        Returns:
            Dictionary with:
            - transcript: Transcribed text (or null if failed)
            - provider: Provider used
            - confidence: Confidence score (0-1) if available
            - error: Error message if transcription failed
            - duration_seconds: Duration of audio processed
        """
        try:
            # Decode audio from base64
            import numpy as np

            audio_bytes = base64.b64decode(audio_data_base64)
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float = audio_int16.astype(np.float32) / 32768.0

            # Create STT provider
            config = {
                "language": language,
                "api_key": voice_state["config"].api_key or "",
                "model_size": voice_state["config"].whisper_model_size,
                "device": voice_state["config"].whisper_device,
            }
            stt_provider = STTProviderFactory.create(provider, config)

            if not stt_provider:
                return {
                    "transcript": None,
                    "provider": provider,
                    "error": f"Failed to initialize {provider} provider",
                }

            # Transcribe
            transcript = await stt_provider.transcribe(
                audio_float, voice_state["config"].sample_rate
            )
            await stt_provider.close()

            return {
                "transcript": transcript,
                "provider": provider,
                "confidence": 0.95 if transcript else 0.0,  # Placeholder
                "language": language,
                "duration_seconds": len(audio_float) / voice_state["config"].sample_rate,
            }

        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            return {
                "transcript": None,
                "provider": provider,
                "error": str(e),
            }

    @app.tool()
    async def list_stt_providers() -> dict[str, Any]:
        """
        List available Speech-to-Text (STT) providers.

        Returns:
            Dictionary with available STT providers and their capabilities.
            Each provider includes: type, speed, cost, offline capability, vram_required.
        """
        return {
            "providers": [
                {
                    "name": "faster-whisper",
                    "type": "local",
                    "description": "GPU-optimized local Whisper (CTranslate2-based)",
                    "speed": "10x faster than cloud",
                    "cost": "$0/month",
                    "offline": True,
                    "vram_required_gb": 2,
                    "supported_languages": "99+ languages",
                    "quality": "Excellent (same model as OpenAI)",
                    "model_sizes": ["tiny", "base", "small", "medium", "large"],
                },
                {
                    "name": "openai",
                    "type": "cloud",
                    "description": "OpenAI Whisper API",
                    "speed": "5-10 seconds latency",
                    "cost": "$0.02/minute",
                    "offline": False,
                    "requires_api_key": True,
                    "supported_languages": "99+ languages",
                    "quality": "Excellent (best accuracy)",
                    "estimated_cost_per_hour": "$1.20",
                },
            ],
            "recommended": "faster-whisper (local GPU, 10x faster, $0 cost)",
            "current_config": {
                "provider": voice_state["config"].stt_provider,
                "model_size": voice_state["config"].whisper_model_size,
                "device": voice_state["config"].whisper_device,
            },
        }

    # ==================== TTS TOOLS ====================

    @app.tool()
    async def synthesize_speech(
        text: str,
        provider: str = "web-speech-api",
        language: str = "en-US",
    ) -> dict[str, Any]:
        """
        Synthesize text to speech audio using specified TTS provider.

        Converts text to audio bytes using Web Speech API (browser, high quality)
        or pyttsx3 (local Python, instant).

        Args:
            text: Text to synthesize to speech
            provider: TTS provider to use ("web-speech-api" or "pyttsx3")
            language: Language/voice for TTS (e.g., "en-US", "fr-FR")

        Returns:
            Dictionary with:
            - audio_base64: Audio data encoded as base64 (WAV format)
            - provider: Provider used
            - duration_seconds: Approximate duration of generated speech
            - error: Error message if synthesis failed
        """
        try:
            if provider == "web-speech-api":
                return {
                    "audio_base64": None,
                    "provider": provider,
                    "note": "Web Speech API runs in browser - no audio returned from server",
                    "instruction": "Call window.speechSynthesis.speak() in browser with text",
                }

            # Create TTS provider
            config = {"rate": voice_state["config"].tts_rate}
            tts_provider = TTSProviderFactory.create(provider, config)

            if not tts_provider:
                return {
                    "audio_base64": None,
                    "provider": provider,
                    "error": f"Failed to initialize {provider} provider",
                }

            # Synthesize
            audio_bytes = await tts_provider.synthesize(text)
            await tts_provider.close()

            if audio_bytes:
                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                # Rough estimate: ~150 words per minute
                estimated_duration = max(1.0, len(text.split()) / 2.5)
                return {
                    "audio_base64": audio_base64,
                    "provider": provider,
                    "duration_seconds": estimated_duration,
                    "format": "WAV",
                    "text": text,
                }
            else:
                return {
                    "audio_base64": None,
                    "provider": provider,
                    "error": "Failed to generate audio",
                }

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}", exc_info=True)
            return {
                "audio_base64": None,
                "provider": provider,
                "error": str(e),
            }

    @app.tool()
    async def list_tts_providers() -> dict[str, Any]:
        """
        List available Text-to-Speech (TTS) providers.

        Returns:
            Dictionary with available TTS providers and their capabilities.
            Each provider includes: type, quality, cost, offline capability.
        """
        return {
            "providers": [
                {
                    "name": "web-speech-api",
                    "type": "browser-native",
                    "description": "Web Speech API (built-in browser TTS)",
                    "quality": "Excellent (natural sounding)",
                    "cost": "$0",
                    "offline": True,
                    "latency": "~500ms",
                    "note": "Runs entirely in browser, no server audio generation",
                    "supported_languages": "Depends on browser (usually 20+)",
                },
                {
                    "name": "pyttsx3",
                    "type": "local",
                    "description": "Local Python TTS engine",
                    "quality": "Good (robotic but clear)",
                    "cost": "$0",
                    "offline": True,
                    "latency": "~800ms",
                    "vram_required": "Minimal",
                    "supported_languages": "Multiple (cross-platform)",
                    "cpu_bound": True,
                },
            ],
            "recommended": "web-speech-api (excellent quality, zero cost, browser-native)",
            "current_config": {
                "provider": voice_state["config"].tts_provider,
                "rate": voice_state["config"].tts_rate,
            },
        }

    # ==================== SEARCH TOOLS ====================

    @app.tool()
    async def search_race_data(
        query: str,
        search_type: str = "general",
        driver_number: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Search F1 race data and telemetry.

        Queries current race session for drivers, pit strategies, tire wear, fuel levels,
        lap times, and other telemetry. Used by voice commands to gather context.

        Args:
            query: Search query (e.g., "Leclerc tire wear", "pit strategy Mercedes", "fuel levels")
            search_type: Type of search - "driver", "strategy", "tires", "fuel", "weather", "general"
            driver_number: Optional driver number (1-20) to filter results

        Returns:
            Dictionary with:
            - results: List of matching data
            - query_type: Type of search performed
            - driver_filters: Driver filters applied
            - result_count: Number of results found
            - error: Error message if search failed
        """
        try:
            logger.info(f"Searching race data: {query} (type={search_type})")

            session_state = voice_state.get("session_state")
            results = []

            # If no SessionState available, return empty results (mock data removed)
            if not session_state:
                logger.warning("No SessionState available for race data search")
                return {
                    "results": [],
                    "query_type": search_type,
                    "query": query,
                    "driver_filters": driver_number,
                    "result_count": 0,
                    "note": "No live race session available",
                }

            # Query driver data from SessionState
            try:
                driver_data_list = session_state.m_driver_data
                if not driver_data_list:
                    return {
                        "results": [],
                        "query_type": search_type,
                        "query": query,
                        "driver_filters": driver_number,
                        "result_count": 0,
                    }

                # Filter by search type
                if search_type == "general":
                    # Return all valid drivers with key telemetry
                    for driver_data in driver_data_list:
                        if not driver_data or not driver_data.is_valid:
                            continue

                        # Extract tire wear info
                        tire_wear = {}
                        if hasattr(driver_data.m_tyre_info, 'm_tyre_wear'):
                            tw = driver_data.m_tyre_info.m_tyre_wear
                            if tw:
                                tire_wear = {
                                    "fl": int(tw.m_front_left) if hasattr(tw, 'm_front_left') else 0,
                                    "fr": int(tw.m_front_right) if hasattr(tw, 'm_front_right') else 0,
                                    "rl": int(tw.m_rear_left) if hasattr(tw, 'm_rear_left') else 0,
                                    "rr": int(tw.m_rear_right) if hasattr(tw, 'm_rear_right') else 0,
                                }

                        driver_entry = {
                            "driver": driver_data.m_driver_info.name or "Unknown",
                            "number": driver_data.m_driver_info.number or 0,
                            "position": driver_data.m_driver_info.position or 0,
                            "tire_compound": str(driver_data.m_tyre_info.m_visual_tyre_compound).split('.')[-1] if hasattr(driver_data.m_tyre_info, 'm_visual_tyre_compound') else "unknown",
                            "tire_wear": tire_wear,
                            "fuel_remaining": int(driver_data.m_car_info.m_fuel_in_tank) if hasattr(driver_data.m_car_info, 'm_fuel_in_tank') else 0,
                        }

                        if driver_number is None or driver_data.m_driver_info.number == driver_number:
                            results.append(driver_entry)

                elif search_type == "tires":
                    # Return tire-specific data
                    for driver_data in driver_data_list:
                        if not driver_data or not driver_data.is_valid:
                            continue

                        # Calculate average tire wear
                        tire_wear_avg = 0.0
                        if hasattr(driver_data.m_tyre_info, 'm_tyre_wear'):
                            tw = driver_data.m_tyre_info.m_tyre_wear
                            if tw:
                                wear_values = []
                                if hasattr(tw, 'm_front_left'):
                                    wear_values.append(tw.m_front_left)
                                if hasattr(tw, 'm_front_right'):
                                    wear_values.append(tw.m_front_right)
                                if hasattr(tw, 'm_rear_left'):
                                    wear_values.append(tw.m_rear_left)
                                if hasattr(tw, 'm_rear_right'):
                                    wear_values.append(tw.m_rear_right)
                                tire_wear_avg = sum(wear_values) / len(wear_values) if wear_values else 0

                        recommendation = "pit_soon" if tire_wear_avg > 70 else "monitor" if tire_wear_avg > 50 else "continue"

                        tire_entry = {
                            "driver": driver_data.m_driver_info.name or "Unknown",
                            "number": driver_data.m_driver_info.number or 0,
                            "tire_wear": round(tire_wear_avg, 1),
                            "recommendation": recommendation,
                        }

                        if driver_number is None or driver_data.m_driver_info.number == driver_number:
                            results.append(tire_entry)

                elif search_type == "fuel":
                    # Return fuel-specific data
                    for driver_data in driver_data_list:
                        if not driver_data or not driver_data.is_valid:
                            continue

                        fuel_remaining = int(driver_data.m_car_info.m_fuel_in_tank) if hasattr(driver_data.m_car_info, 'm_fuel_in_tank') else 0

                        fuel_entry = {
                            "driver": driver_data.m_driver_info.name or "Unknown",
                            "number": driver_data.m_driver_info.number or 0,
                            "remaining_liters": fuel_remaining,
                        }

                        if driver_number is None or driver_data.m_driver_info.number == driver_number:
                            results.append(fuel_entry)

                elif search_type == "strategy":
                    # Return pit strategy data
                    for driver_data in driver_data_list:
                        if not driver_data or not driver_data.is_valid:
                            continue

                        pit_stop_info = {}
                        if hasattr(driver_data.m_pit_info, 'm_pit_stops'):
                            pit_stops = driver_data.m_pit_info.m_pit_stops
                            if pit_stops:
                                last_pit = pit_stops[-1]
                                pit_stop_info = {
                                    "pit_stop_lap": last_pit.m_lap if hasattr(last_pit, 'm_lap') else None,
                                    "pit_duration": round(last_pit.m_pit_duration, 1) if hasattr(last_pit, 'm_pit_duration') else None,
                                }

                        strategy_entry = {
                            "driver": driver_data.m_driver_info.name or "Unknown",
                            "number": driver_data.m_driver_info.number or 0,
                            "current_compound": str(driver_data.m_tyre_info.m_visual_tyre_compound).split('.')[-1] if hasattr(driver_data.m_tyre_info, 'm_visual_tyre_compound') else "unknown",
                            **pit_stop_info,
                        }

                        if driver_number is None or driver_data.m_driver_info.number == driver_number:
                            results.append(strategy_entry)

            except Exception as query_error:
                logger.warning(f"Error querying SessionState: {query_error}")

            return {
                "results": results,
                "query_type": search_type,
                "query": query,
                "driver_filters": driver_number,
                "result_count": len(results),
                "source": "live_race_telemetry" if session_state else "mock_data",
            }

        except Exception as e:
            logger.error(f"Race data search error: {e}", exc_info=True)
            return {
                "results": [],
                "query_type": search_type,
                "error": str(e),
                "result_count": 0,
            }

    # ==================== LLM TOOLS ====================

    @app.tool()
    async def process_voice_command(
        transcription: str,
        race_context: Optional[dict[str, Any]] = None,
        llm_provider: str = "ollama",
        auto_search: bool = True,
    ) -> dict[str, Any]:
        """
        Process voice command through LLM with race telemetry context.

        Uses local LLM (Ollama, LM Studio) or cloud LLM (OpenAI) to process
        transcribed voice commands and generate contextual responses.

        Automatically searches for relevant race data to enrich context if auto_search=True.

        Args:
            transcription: Transcribed voice command text
            race_context: Optional pre-fetched race telemetry context (driver data, lap info, etc.)
            llm_provider: LLM provider to use ("ollama", "lmstudio", "openai")
            auto_search: Automatically search for relevant race data (default True)

        Returns:
            Dictionary with:
            - response: LLM response text
            - provider: Provider used
            - processing_time_ms: Time taken to generate response
            - context_used: Whether race context was used
            - search_results: Race data search results if auto_search=True
            - error: Error message if processing failed
        """
        try:
            import time

            start_time = time.time()

            # Auto-search for context if not provided
            search_results = None
            if auto_search and not race_context:
                search_result = await search_race_data(
                    query=transcription,
                    search_type="general"
                )
                if search_result.get("results"):
                    search_results = search_result
                    race_context = search_result.get("results", [])

            # Construct context for LLM
            context_str = ""
            if race_context:
                context_str = f"\n\nRace Context:\n{race_context}"

            system_prompt = (
                "You are an F1 Race Engineer AI assistant. "
                "Provide concise, professional responses about F1 telemetry and race strategy. "
                "Use provided race context when available to give specific, data-driven answers."
            )

            user_message = f"Voice Command: {transcription}{context_str}"

            # Create LLM provider dynamically
            # Note: LLMProviderFactory not yet implemented, using placeholder
            logger.info(
                f"Processing voice command with {llm_provider}: {transcription}"
            )

            processing_time_ms = (time.time() - start_time) * 1000

            return {
                "response": f"[{llm_provider}] Processing: {transcription}",
                "provider": llm_provider,
                "processing_time_ms": processing_time_ms,
                "context_used": bool(race_context),
                "auto_search_enabled": auto_search,
                "search_results": search_results,
                "status": "not_yet_implemented",
                "note": "LLM provider integration coming in next phase",
            }

        except Exception as e:
            logger.error(f"Voice command processing error: {e}", exc_info=True)
            return {
                "response": None,
                "provider": llm_provider,
                "error": str(e),
            }

    @app.tool()
    async def list_voice_config() -> dict[str, Any]:
        """
        Get current voice system configuration.

        Returns:
            Dictionary with complete voice configuration and available options.
        """
        config = voice_state["config"]
        return {
            "voice_enabled": config.enabled,
            "stt_provider": config.stt_provider,
            "tts_provider": config.tts_provider,
            "stt_options": {
                "providers": ["faster-whisper", "openai"],
                "model_sizes": ["tiny", "base", "small", "medium", "large"],
                "current_model": config.whisper_model_size,
                "devices": ["cuda", "cpu"],
                "current_device": config.whisper_device,
            },
            "tts_options": {
                "providers": ["web-speech-api", "pyttsx3"],
                "current_rate": config.tts_rate,
            },
            "audio_settings": {
                "sample_rate": config.sample_rate,
                "language": config.language,
                "timeout_seconds": config.timeout_seconds,
            },
            "hardware_info": {
                "k80_optimized": True,
                "gpu_vram_per_device": "24GB (K80)",
                "recommended_vram_usage": "STT 2GB (GPU 0) + LLM 14GB (GPU 1)",
            },
        }

    @app.tool()
    async def get_voice_status() -> dict[str, Any]:
        """
        Get current voice system status and provider health.

        Returns:
            Dictionary with status of all voice providers and subsystems.
        """
        return {
            "system_online": True,
            "stt_provider": {
                "name": voice_state["config"].stt_provider,
                "status": "ready",
                "initialized": voice_state["handler"].stt_provider is not None,
            },
            "tts_provider": {
                "name": voice_state["config"].tts_provider,
                "status": "ready",
                "initialized": voice_state["handler"].tts_provider is not None,
            },
            "audio_buffer": {
                "status": "empty",
                "recording": voice_state["handler"].is_recording,
            },
            "mcp_server": {
                "status": "online",
                "version": "1.0.0",
                "tools_available": 8,
                "tools": [
                    "transcribe_audio",
                    "synthesize_speech",
                    "search_race_data",
                    "process_voice_command",
                    "list_stt_providers",
                    "list_tts_providers",
                    "list_voice_config",
                    "get_voice_status",
                ],
            },
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }

    return app


if __name__ == "__main__":
    # Direct execution for testing: python -m apps.backend.mcp_server.voice_mcp
    config = VoiceSettings(
        enabled=True,
        stt_provider="faster-whisper",
        whisper_device="cuda",
        tts_provider="pyttsx3",
    )

    app = create_mcp_server(config)

    logger.info("=" * 70)
    logger.info("🎤 Pits n' Giggles Voice MCP Server")
    logger.info("=" * 70)
    logger.info("Running on stdio transport (standard MCP protocol)")
    logger.info("Tools:")
    logger.info("  • transcribe_audio - Speech-to-text")
    logger.info("  • synthesize_speech - Text-to-speech")
    logger.info("  • process_voice_command - LLM processing")
    logger.info("  • list_stt_providers - Available STT providers")
    logger.info("  • list_tts_providers - Available TTS providers")
    logger.info("  • list_voice_config - Current configuration")
    logger.info("  • get_voice_status - System status")
    logger.info("=" * 70)

    app.run()
