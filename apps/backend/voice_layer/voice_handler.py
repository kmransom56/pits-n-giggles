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
from openai import AsyncOpenAI

from lib.config.schema.voice import VoiceSettings

logger = logging.getLogger(__name__)


class VoiceHandler:
    """Handles speech-to-text and text-to-speech voice communication."""

    def __init__(self, voice_config: VoiceSettings):
        """
        Initialize voice handler with configuration.

        Args:
            voice_config: VoiceSettings configuration object
        """
        self.config = voice_config
        self.openai_client: Optional[AsyncOpenAI] = None
        self.audio_buffer: Optional[np.ndarray] = None
        self.is_recording = False

        if voice_config.enabled and voice_config.stt_provider == "openai":
            api_key = voice_config.api_key or None
            self.openai_client = AsyncOpenAI(api_key=api_key)

    async def process_audio_chunk(self, audio_data: bytes, is_final: bool = False) -> Optional[str]:
        """
        Process audio chunk and perform STT when complete.

        Args:
            audio_data: Raw audio chunk data (PCM or WAV)
            is_final: Whether this is the final chunk of the utterance

        Returns:
            Transcribed text if STT succeeds, None otherwise
        """
        if not self.config.enabled:
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

            # Resample to 16kHz if needed
            audio_16k = librosa.resample(
                self.audio_buffer,
                orig_sr=self.config.sample_rate,
                target_sr=16000
            )

            # Convert to WAV bytes for OpenAI API
            wav_bytes = self._audio_to_wav_bytes(audio_16k, sr=16000)

            # Transcribe using OpenAI Whisper
            transcript = await self._transcribe_whisper(wav_bytes)

            # Reset buffer
            self.audio_buffer = None

            return transcript

        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}", exc_info=True)
            self.audio_buffer = None
            return None

    async def _transcribe_whisper(self, wav_bytes: bytes) -> Optional[str]:
        """
        Transcribe audio using OpenAI Whisper API.

        Args:
            wav_bytes: Audio data as WAV bytes

        Returns:
            Transcribed text or None if transcription fails
        """
        if not self.openai_client:
            logger.warning("OpenAI client not initialized")
            return None

        try:
            # Create file-like object for OpenAI API
            audio_file = io.BytesIO(wav_bytes)
            audio_file.name = "audio.wav"

            # Call Whisper API with timeout
            response = await asyncio.wait_for(
                self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=self.config.language.split("-")[0],  # Extract language code (en from en-US)
                ),
                timeout=self.config.timeout_seconds
            )

            text = response.text.strip()

            # Only return if confidence meets threshold (Whisper doesn't provide confidence,
            # so we do basic validation)
            if text and len(text) > 0:
                logger.info(f"Transcribed: {text}")
                return text

            return None

        except asyncio.TimeoutError:
            logger.error(f"Whisper API timeout after {self.config.timeout_seconds}s")
            return None
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}", exc_info=True)
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

    def _audio_to_wav_bytes(self, audio: np.ndarray, sr: int) -> bytes:
        """
        Convert numpy audio array to WAV bytes.

        Args:
            audio: Audio data as numpy array (float32, [-1, 1])
            sr: Sample rate

        Returns:
            WAV file as bytes
        """
        wav_buffer = io.BytesIO()

        # Use soundfile to write WAV
        import soundfile as sf
        sf.write(wav_buffer, audio, sr, format="WAV", subtype="PCM_16")

        wav_buffer.seek(0)
        return wav_buffer.read()

    async def close(self):
        """Clean up resources."""
        if self.openai_client:
            await self.openai_client.close()
