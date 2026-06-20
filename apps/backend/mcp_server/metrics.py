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

"""Prometheus metrics for MCP voice pipeline monitoring."""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class VoiceMetrics:
    """Collect and report metrics for voice pipeline."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: Dict[str, Any] = {
            "tool_calls": {},
            "latencies": [],
            "errors": [],
        }

    def record_tool_call(
        self,
        tool_name: str,
        duration_ms: float,
        provider: Optional[str] = None,
        status: str = "success",
        error: Optional[str] = None,
    ) -> None:
        """
        Record a tool invocation.

        Args:
            tool_name: Name of the MCP tool called
            duration_ms: Time taken in milliseconds
            provider: Provider used (STT/TTS/LLM provider)
            status: "success" or "failed"
            error: Error message if failed
        """
        if tool_name not in self.metrics["tool_calls"]:
            self.metrics["tool_calls"][tool_name] = {
                "count": 0,
                "total_ms": 0,
                "errors": 0,
                "providers": {},
            }

        stats = self.metrics["tool_calls"][tool_name]
        stats["count"] += 1
        stats["total_ms"] += duration_ms

        if status == "failed":
            stats["errors"] += 1
            self.metrics["errors"].append({
                "tool": tool_name,
                "timestamp": datetime.utcnow().isoformat(),
                "error": error,
            })

        if provider:
            if provider not in stats["providers"]:
                stats["providers"][provider] = {"count": 0, "total_ms": 0}
            stats["providers"][provider]["count"] += 1
            stats["providers"][provider]["total_ms"] += duration_ms

        self.metrics["latencies"].append({
            "tool": tool_name,
            "latency_ms": duration_ms,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        })

        logger.debug(
            f"Tool metric: {tool_name} - {duration_ms:.1f}ms - {status}"
        )

    def get_percentile_latency(self, percentile: int = 95) -> Optional[float]:
        """
        Get latency percentile across all tool calls.

        Args:
            percentile: Percentile to calculate (e.g., 95 for P95)

        Returns:
            Latency in milliseconds or None
        """
        if not self.metrics["latencies"]:
            return None

        latencies = sorted([m["latency_ms"] for m in self.metrics["latencies"]])
        index = int(len(latencies) * percentile / 100)
        return latencies[min(index, len(latencies) - 1)]

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        total_calls = sum(
            stats["count"] for stats in self.metrics["tool_calls"].values()
        )
        total_errors = sum(
            stats["errors"] for stats in self.metrics["tool_calls"].values()
        )

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_calls": total_calls,
            "total_errors": total_errors,
            "error_rate": total_errors / max(total_calls, 1),
            "p50_latency_ms": self.get_percentile_latency(50),
            "p95_latency_ms": self.get_percentile_latency(95),
            "p99_latency_ms": self.get_percentile_latency(99),
            "tools": self.metrics["tool_calls"],
        }

    def log_json_event(
        self,
        tool_name: str,
        duration_ms: float,
        provider: Optional[str] = None,
        status: str = "success",
        error: Optional[str] = None,
    ) -> None:
        """
        Log structured JSON event for monitoring.

        Args:
            tool_name: Name of the MCP tool
            duration_ms: Duration in milliseconds
            provider: Provider used
            status: success or failed
            error: Error message if failed
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "voice_tool_invocation",
            "tool": tool_name,
            "duration_ms": duration_ms,
            "provider": provider,
            "status": status,
            "error": error,
        }

        logger.info(json.dumps(event))


# Global metrics instance
_metrics: Optional[VoiceMetrics] = None


def get_metrics() -> VoiceMetrics:
    """Get or create global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = VoiceMetrics()
    return _metrics


def record_voice_tool(
    tool_name: str,
    duration_ms: float,
    provider: Optional[str] = None,
    status: str = "success",
    error: Optional[str] = None,
) -> None:
    """Record a voice tool invocation to global metrics."""
    metrics = get_metrics()
    metrics.record_tool_call(tool_name, duration_ms, provider, status, error)
    metrics.log_json_event(tool_name, duration_ms, provider, status, error)
