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

"""Voice provider abstraction layer for extensible STT/TTS/LLM support."""

import io
import logging
from abc import ABC, abstractmethod
from typing import Optional

import librosa
import numpy as np

logger = logging.getLogger(__name__)


class STTProvider(ABC):
    """Abstract base class for Speech-to-Text providers."""

    def __init__(self, language: str = "en"):
        """Initialize STT provider.

        Args:
            language: Language code (e.g., "en", "en-US")
        """
        self.language = language

    @abstractmethod
    async def transcribe(self, audio_data: np.ndarray, sample_rate: int) -> Optional[str]:
        """
        Transcribe audio to text.

        Args:
            audio_data: Audio as numpy array (float32, [-1, 1])
            sample_rate: Sample rate in Hz

        Returns:
            Transcribed text or None if failed
        """
        pass

    @abstractmethod
    async def close(self):
        """Clean up resources."""
        pass


class TTSProvider(ABC):
    """Abstract base class for Text-to-Speech providers."""

    @abstractmethod
    async def synthesize(self, text: str) -> Optional[bytes]:
        """
        Synthesize text to audio.

        Args:
            text: Text to speak

        Returns:
            Audio bytes (WAV format) or None if failed
        """
        pass

    @abstractmethod
    async def close(self):
        """Clean up resources."""
        pass


class LLMProvider(ABC):
    """Abstract base class for Language Model providers (command processing)."""

    @abstractmethod
    async def process_command(self, text: str, context: Optional[dict] = None) -> Optional[str]:
        """
        Process voice command through LLM.

        Args:
            text: Transcribed command text
            context: Optional context (race state, driver data, etc.)

        Returns:
            LLM response or None if failed
        """
        pass

    @abstractmethod
    async def close(self):
        """Clean up resources."""
        pass


class OpenAISTTProvider(STTProvider):
    """OpenAI Whisper STT provider (cloud-based)."""

    def __init__(self, api_key: str, language: str = "en"):
        """Initialize OpenAI Whisper provider.

        Args:
            api_key: OpenAI API key
            language: Language code
        """
        super().__init__(language)
        self.api_key = api_key

        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=api_key)
        except ImportError:
            logger.error("openai package not installed. Install with: pip install openai")
            self.client = None

    async def transcribe(self, audio_data: np.ndarray, sample_rate: int) -> Optional[str]:
        """Transcribe using OpenAI Whisper API."""
        if not self.client:
            logger.error("OpenAI client not available")
            return None

        try:
            # Convert to WAV bytes
            wav_bytes = self._audio_to_wav_bytes(audio_data, sample_rate)

            # Call Whisper API
            import asyncio
            response = await asyncio.wait_for(
                self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=("audio.wav", io.BytesIO(wav_bytes), "audio/wav"),
                    language=self.language.split("-")[0],
                ),
                timeout=10
            )

            return response.text.strip() if response.text else None

        except Exception as e:
            logger.error(f"OpenAI Whisper error: {e}", exc_info=True)
            return None

    def _audio_to_wav_bytes(self, audio: np.ndarray, sr: int) -> bytes:
        """Convert numpy array to WAV bytes."""
        import soundfile as sf
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, audio, sr, format="WAV", subtype="PCM_16")
        wav_buffer.seek(0)
        return wav_buffer.read()

    async def close(self):
        """Close OpenAI client."""
        if self.client:
            await self.client.close()


class FasterWhisperSTTProvider(STTProvider):
    """Local faster-whisper STT provider (GPU-accelerated, no API cost)."""

    def __init__(self, language: str = "en", model_size: str = "base", device: str = "cuda"):
        """Initialize faster-whisper provider.

        Args:
            language: Language code
            model_size: Model size ("tiny", "base", "small", "medium", "large")
            device: Device to run on ("cuda", "cpu")
        """
        super().__init__(language)
        self.model_size = model_size
        self.device = device
        self.model = None

        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading faster-whisper {model_size} on {device}...")
            self.model = WhisperModel(model_size, device=device, compute_type="float16")
        except ImportError:
            logger.error("faster-whisper not installed. Install with: pip install faster-whisper")
        except Exception as e:
            logger.error(f"Failed to load faster-whisper model: {e}")

    async def transcribe(self, audio_data: np.ndarray, sample_rate: int) -> Optional[str]:
        """Transcribe using local faster-whisper model."""
        if not self.model:
            logger.error("faster-whisper model not loaded")
            return None

        try:
            # Resample to 16kHz if needed
            if sample_rate != 16000:
                audio_16k = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
            else:
                audio_16k = audio_data

            # Transcribe
            segments, info = self.model.transcribe(
                audio_16k,
                language=self.language.split("-")[0],
                beam_size=5
            )

            # Combine segments
            text = " ".join([segment.text.strip() for segment in segments])
            return text if text else None

        except Exception as e:
            logger.error(f"faster-whisper error: {e}", exc_info=True)
            return None

    async def close(self):
        """Clean up model resources."""
        if self.model:
            # faster-whisper doesn't have explicit close
            self.model = None


class PyTTSx3Provider(TTSProvider):
    """Local pyttsx3 TTS provider (offline, cross-platform)."""

    def __init__(self, rate: int = 150):
        """Initialize pyttsx3 provider.

        Args:
            rate: Speech rate (default 150 words per minute)
        """
        self.rate = rate
        self.engine = None

        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', rate)
            logger.info(f"pyttsx3 initialized at {rate} wpm")
        except ImportError:
            logger.error("pyttsx3 not installed. Install with: pip install pyttsx3")
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3: {e}")

    async def synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize text using pyttsx3."""
        if not self.engine:
            logger.error("pyttsx3 engine not initialized")
            return None

        try:
            import io
            import wave

            # Use in-memory file for audio
            audio_buffer = io.BytesIO()
            self.engine.save_to_file(text, audio_buffer)
            self.engine.runAndWait()

            # Return WAV bytes
            audio_buffer.seek(0)
            return audio_buffer.read()

        except Exception as e:
            logger.error(f"pyttsx3 synthesis error: {e}", exc_info=True)
            return None

    async def close(self):
        """Clean up engine."""
        if self.engine:
            self.engine.stop()
            self.engine = None


class STTProviderFactory:
    """Factory for creating STT providers based on configuration."""

    @staticmethod
    def create(provider_type: str, config: dict) -> Optional[STTProvider]:
        """Create STT provider instance.

        Args:
            provider_type: "openai", "faster-whisper", or custom
            config: Provider-specific configuration dict

        Returns:
            Initialized STT provider or None
        """
        if provider_type == "openai":
            api_key = config.get("api_key")
            if not api_key:
                logger.error("OpenAI API key required for openai provider")
                return None
            return OpenAISTTProvider(api_key=api_key, language=config.get("language", "en"))

        elif provider_type == "faster-whisper":
            return FasterWhisperSTTProvider(
                language=config.get("language", "en"),
                model_size=config.get("model_size", "base"),
                device=config.get("device", "cuda")
            )

        else:
            logger.error(f"Unknown STT provider: {provider_type}")
            return None


class TTSProviderFactory:
    """Factory for creating TTS providers based on configuration."""

    @staticmethod
    def create(provider_type: str, config: dict) -> Optional[TTSProvider]:
        """Create TTS provider instance.

        Args:
            provider_type: "web-speech-api", "pyttsx3", or custom
            config: Provider-specific configuration dict

        Returns:
            Initialized TTS provider or None (web-speech-api runs in browser)
        """
        if provider_type == "web-speech-api":
            # Web Speech API runs in browser, no backend provider needed
            logger.info("Using Web Speech API (browser-side TTS)")
            return None

        elif provider_type == "pyttsx3":
            return PyTTSx3Provider(rate=config.get("rate", 150))

        else:
            logger.warning(f"Unknown TTS provider: {provider_type}, falling back to web-speech-api")
            return None


class OllamaLLMProvider(LLMProvider):
    """Ollama LLM provider for local language model inference."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral:7b-instruct"):
        """
        Initialize Ollama LLM provider.

        Args:
            base_url: Ollama server URL (default: localhost:11434)
            model: Model name to use (default: mistral:7b-instruct)
        """
        self.base_url = base_url
        self.model = model
        self.client = None

        try:
            import aiohttp
            self.client = aiohttp.ClientSession()
            logger.info(f"✓ Ollama LLM: {model} @ {base_url}")
        except ImportError:
            logger.error("aiohttp not installed, cannot use Ollama provider")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")

    async def process_command(self, text: str, context: Optional[dict] = None) -> Optional[str]:
        """
        Process voice command through Ollama LLM.

        Args:
            text: Transcribed command text
            context: Optional race context (driver data, telemetry, etc.)

        Returns:
            LLM response or None if failed
        """
        if not self.client:
            logger.error("Ollama client not initialized")
            return None

        try:
            # Build prompt with context if available
            system_prompt = (
                "You are an F1 Race Engineer AI assistant. "
                "Provide concise, professional responses about F1 telemetry and race strategy. "
                "Keep responses under 2 sentences."
            )

            user_message = text
            if context:
                user_message = f"Race Context: {context}\n\nCommand: {text}"

            # Call Ollama API
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": f"{system_prompt}\n\nUser: {user_message}",
                "stream": False,
                "temperature": 0.3,
            }

            async with self.client.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("response", "No response").strip()
                else:
                    logger.error(f"Ollama API error: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Ollama processing error: {e}")
            return None

    async def close(self):
        """Close Ollama client connection."""
        if self.client:
            await self.client.close()
            logger.info("✓ Ollama client closed")


class LLMProviderFactory:
    """Factory for creating LLM providers."""

    @staticmethod
    def create(provider_type: str, config: dict) -> Optional[LLMProvider]:
        """
        Create LLM provider instance.

        Args:
            provider_type: "ollama", "openai", or custom
            config: Provider-specific configuration dict

        Returns:
            Initialized LLM provider or None if failed
        """
        if provider_type == "ollama":
            return OllamaLLMProvider(
                base_url=config.get("base_url", "http://localhost:11434"),
                model=config.get("model", "mistral:7b-instruct"),
            )

        elif provider_type == "openai":
            # Placeholder for OpenAI provider
            logger.warning("OpenAI LLM provider not yet implemented")
            return None

        else:
            logger.error(f"Unknown LLM provider: {provider_type}")
            return None
