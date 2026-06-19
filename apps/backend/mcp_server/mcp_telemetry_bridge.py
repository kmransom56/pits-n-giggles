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

"""Bridge between F1 telemetry handler and MCP server for live SessionState integration."""

import logging
import threading
from typing import Optional

from apps.backend.state_mgmt_layer.session_state import SessionState
from lib.config.schema.voice import VoiceSettings

logger = logging.getLogger(__name__)


class MCPTelemetryBridge:
    """Bridges telemetry handler and MCP server for live F1 race data."""

    _instance: Optional["MCPTelemetryBridge"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "MCPTelemetryBridge":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.session_state: Optional[SessionState] = None
        self.mcp_thread: Optional[threading.Thread] = None
        self.mcp_enabled = False

    def register_session_state(self, session_state: SessionState) -> None:
        """Register SessionState instance for MCP server access."""
        self.session_state = session_state
        logger.info("✓ MCP Telemetry Bridge: SessionState registered")

    def start_mcp_server(
        self,
        stt_provider: str = "faster-whisper",
        tts_provider: str = "web-speech-api",
        whisper_device: str = "cuda",
        whisper_model_size: str = "base",
    ) -> None:
        """Start MCP server in background thread with live SessionState."""
        if not self.session_state:
            logger.warning("⚠ MCP Server: No SessionState available, cannot start")
            return

        if self.mcp_thread and self.mcp_thread.is_alive():
            logger.warning("⚠ MCP Server: Already running")
            return

        from .launcher import launch_mcp_server

        # Create MCP thread
        self.mcp_thread = threading.Thread(
            target=launch_mcp_server,
            kwargs={
                "stt_provider": stt_provider,
                "tts_provider": tts_provider,
                "whisper_device": whisper_device,
                "whisper_model_size": whisper_model_size,
                "debug": False,
                "session_state": self.session_state,
            },
            daemon=True,
            name="MCP-Server-Thread",
        )

        self.mcp_thread.start()
        self.mcp_enabled = True
        logger.info("✓ MCP Server: Started in background thread with live telemetry")

    def stop_mcp_server(self) -> None:
        """Stop MCP server thread."""
        if self.mcp_thread and self.mcp_thread.is_alive():
            logger.info("Stopping MCP server...")
            # FastMCP server runs synchronously, so we can't forcefully stop it
            # Instead, it will stop when launcher catches KeyboardInterrupt
            self.mcp_enabled = False

    def is_enabled(self) -> bool:
        """Check if MCP server is running with live SessionState."""
        return self.mcp_enabled and self.session_state is not None

    def get_session_state(self) -> Optional[SessionState]:
        """Get registered SessionState for MCP server tools."""
        return self.session_state
