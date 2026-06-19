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

# -------------------------------------- IMPORTS -----------------------------------------------------------------------

from typing import Any, ClassVar, Dict, Literal

from pydantic import BaseModel, Field

from .diff import ConfigDiffMixin

# -------------------------------------- CLASS  DEFINITIONS ------------------------------------------------------------


class VoiceSettings(ConfigDiffMixin, BaseModel):

    ui_meta: ClassVar[Dict[str, Any]] = {
        "visible": True,
    }

    enabled: bool = Field(
        default=False,
        description="Enable voice communication features",
        json_schema_extra={
            "ui": {
                "type": "check_box",
                "visible": True
            }
        }
    )

    stt_provider: Literal["openai", "google", "azure"] = Field(
        default="openai",
        description="Speech-to-Text provider",
        json_schema_extra={
            "ui": {
                "type": "dropdown",
                "visible": True
            }
        }
    )

    tts_provider: Literal["web-speech-api", "google", "elevenlabs", "azure"] = Field(
        default="web-speech-api",
        description="Text-to-Speech provider (web-speech-api runs client-side in browser)",
        json_schema_extra={
            "ui": {
                "type": "dropdown",
                "visible": True
            }
        }
    )

    language: str = Field(
        default="en-US",
        description="Language code for voice recognition (e.g., en-US, fr-FR)",
        json_schema_extra={
            "ui": {
                "type": "text_box",
                "visible": True
            }
        }
    )

    sample_rate: int = Field(
        default=16000,
        description="Audio sample rate in Hz (16000 recommended for speech)",
        json_schema_extra={
            "ui": {
                "type": "number",
                "visible": False
            }
        }
    )

    chunk_duration_ms: int = Field(
        default=100,
        description="Audio chunk duration in milliseconds for streaming",
        json_schema_extra={
            "ui": {
                "type": "number",
                "visible": False
            }
        }
    )

    audio_format: Literal["wav", "pcm"] = Field(
        default="pcm",
        description="Audio format for streaming (pcm for raw, wav for WAV container)",
        json_schema_extra={
            "ui": {
                "type": "dropdown",
                "visible": False
            }
        }
    )

    vad_enabled: bool = Field(
        default=False,
        description="Enable Voice Activity Detection to skip silence",
        json_schema_extra={
            "ui": {
                "type": "check_box",
                "visible": True
            }
        }
    )

    vad_threshold: float = Field(
        default=0.5,
        description="Voice Activity Detection threshold (0.0-1.0)",
        json_schema_extra={
            "ui": {
                "type": "number",
                "visible": False
            }
        }
    )

    api_key: str = Field(
        default="",
        description="API key for STT/TTS provider (leave empty if using default credentials)",
        json_schema_extra={
            "ui": {
                "type": "password_box",
                "visible": False
            }
        }
    )

    timeout_seconds: int = Field(
        default=10,
        description="STT processing timeout in seconds",
        json_schema_extra={
            "ui": {
                "type": "number",
                "visible": False
            }
        }
    )

    auto_announce_enabled: bool = Field(
        default=True,
        description="Automatically announce telemetry updates via voice",
        json_schema_extra={
            "ui": {
                "type": "check_box",
                "visible": True
            }
        }
    )

    min_confidence: float = Field(
        default=0.7,
        description="Minimum confidence threshold for STT results (0.0-1.0)",
        json_schema_extra={
            "ui": {
                "type": "number",
                "visible": False
            }
        }
    )
