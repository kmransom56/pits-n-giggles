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

import asyncio
import io
import logging
from typing import Optional

import librosa
import numpy as np

from lib.config.schema.voice import VoiceSettings
from .providers import STTProviderFactory, TTSProviderFactory, STTProvider, TTSProvider

logger = logging.getLogger(__name__)


class VoiceHandler:
    """Handles speech-to-text and text-to-speech voice communication with pluggable providers."""

    def __init__(self, voice_config: VoiceSettings):
        """
        Initialize voice handler with configuration.

        Args:
            voice_config: VoiceSettings configuration object
        """
        self.config = voice_config
        self.stt_provider: Optional[STTProvider] = None
        self.tts_provider: Optional[TTSProvider] = None
        self.audio_buffer: Optional[np.ndarray] = None
        self.is_recording = False

        # Initialize providers based on configuration
        if voice_config.enabled:
            self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize STT and TTS providers based on configuration."""
        # Initialize STT provider
        stt_config = {
            "language": self.config.language,
            "api_key": self.config.api_key or "",
            "model_size": self.config.whisper_model_size,
            "device": self.config.whisper_device,
        }
        self.stt_provider = STTProviderFactory.create(self.config.stt_provider, stt_config)

        if not self.stt_provider:
            logger.error(f"Failed to create STT provider: {self.config.stt_provider}")
            return

        logger.info(f"✓ STT Provider: {self.config.stt_provider}")

        # Initialize TTS provider (if needed)
        tts_config = {
            "rate": self.config.tts_rate,
        }
        self.tts_provider = TTSProviderFactory.create(self.config.tts_provider, tts_config)

        if self.config.tts_provider != "web-speech-api" and not self.tts_provider:
            logger.warning(f"TTS provider not available: {self.config.tts_provider}")
        else:
            logger.info(f"✓ TTS Provider: {self.config.tts_provider}")

    async def process_audio_chunk(self, audio_data: bytes, is_final: bool = False) -> Optional[str]:
        """
        Process audio chunk and perform STT when complete.

        Args:
            audio_data: Raw audio chunk data (PCM or WAV)
            is_final: Whether this is the final chunk of the utterance

        Returns:
            Transcribed text if STT succeeds, None otherwise
        """
        if not self.config.enabled or not self.stt_provider:
            return None

        try:
            # Accumulate audio chunks
            chunk_np = self._bytes_to_audio(audio_data)
            if self.audio_buffer is None:
                self.audio_buffer = chunk_np
            else:
                self.audio_buffer = np.concatenate([self.audio_buffer, chunk_np])

            # Only process when final chunk is received
            if not is_final:
                return None

            # Check if we have enough audio to process
            if self.audio_buffer is None or len(self.audio_buffer) == 0:
                return None

            # Transcribe using configured provider
            transcript = await self._transcribe(self.audio_buffer, self.config.sample_rate)

            # Reset buffer
            self.audio_buffer = None

            return transcript

        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}", exc_info=True)
            self.audio_buffer = None
            return None

    async def _transcribe(self, audio_data: np.ndarray, sample_rate: int) -> Optional[str]:
        """
        Transcribe audio using configured STT provider.

        Args:
            audio_data: Audio as numpy array (float32, [-1, 1])
            sample_rate: Sample rate in Hz

        Returns:
            Transcribed text or None if failed
        """
        if not self.stt_provider:
            logger.warning("STT provider not initialized")
            return None

        try:
            # Call transcription with timeout
            transcript = await asyncio.wait_for(
                self.stt_provider.transcribe(audio_data, sample_rate),
                timeout=self.config.timeout_seconds
            )

            if transcript and len(transcript) > 0:
                logger.info(f"Transcribed: {transcript}")
                return transcript

            return None

        except asyncio.TimeoutError:
            logger.error(f"STT timeout after {self.config.timeout_seconds}s")
            return None
        except Exception as e:
            logger.error(f"STT transcription error: {e}", exc_info=True)
            return None

    def _bytes_to_audio(self, audio_bytes: bytes) -> np.ndarray:
        """
        Convert raw audio bytes to numpy array.

        Args:
            audio_bytes: Raw audio data

        Returns:
            Audio as numpy array (float32, normalized to [-1, 1])
        """
        # Convert bytes to int16 array
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)

        # Convert to float32 and normalize to [-1, 1]
        audio_float = audio_int16.astype(np.float32) / 32768.0

        return audio_float

    async def close(self):
        """Clean up resources."""
        if self.stt_provider:
            await self.stt_provider.close()
        if self.tts_provider:
            await self.tts_provider.close()
