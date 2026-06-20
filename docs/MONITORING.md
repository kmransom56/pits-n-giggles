# Production Monitoring & Alerting

**Real-time observability for MCP voice pipeline on K80 hardware.**

## Metrics Collection

### Available Metrics

All MCP tool invocations are automatically tracked:

```python
record_voice_tool(
    tool_name: str,           # e.g., "search_race_data", "process_voice_command"
    duration_ms: float,       # Execution time in milliseconds
    provider: str,            # STT/TTS/LLM provider used
    status: str,              # "success" or "failed"
    error: Optional[str]      # Error message if failed
)
```

### Structured JSON Logging

Every tool invocation logs a JSON event:

```json
{
  "timestamp": "2025-06-19T12:00:00.000000",
  "event_type": "voice_tool_invocation",
  "tool": "search_race_data",
  "duration_ms": 87.4,
  "provider": "general",
  "status": "success",
  "error": null
}
```

**Log to file:**
```bash
# Redirect stderr to capture structured logs
poetry run python -m apps.backend.mcp_server.launcher 2> /var/log/mcp-voice.log &
```

**Parse with jq:**
```bash
# Real-time metrics
tail -f /var/log/mcp-voice.log | jq 'select(.event_type=="voice_tool_invocation")'

# Tool latency
tail -f /var/log/mcp-voice.log | jq 'select(.tool=="process_voice_command") | .duration_ms'

# Error tracking
tail -f /var/log/mcp-voice.log | jq 'select(.status=="failed")'
```

## Performance Targets

### K80 Latency SLOs

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| P50 latency | 3-4s | > 5s |
| P95 latency | 7-8s | > 10s |
| P99 latency | 8-9s | > 12s |
| Error rate | < 1% | > 5% |

### Breakdown (Per Component)

```
Total (Target: 4-9s)
├─ STT (search/transcribe): 1-2s
├─ Search race data: ~100ms
├─ LLM (ollama mistral:7b): 2-5s
├─ TTS (pyttsx3): ~500ms
└─ Overhead: ~200ms
```

## Health Checks

### HTTP Health Endpoint (Future)

```bash
# Check if MCP server is running (currently stdio-only)
curl http://localhost:4770/health 2>/dev/null

# Expected: 200 OK with status JSON
# Currently: Use log monitoring instead
```

### System Health

```bash
# GPU memory (should be stable)
watch -n 5 'nvidia-smi --query-gpu=index,memory.used,memory.free --format=csv,nounits'

# Expected K80 state:
# GPU 0: 2GB used (faster-whisper)
# GPU 1: 14GB used (ollama mistral:7b)

# Process memory
ps aux | grep mcp_server.launcher
# Should be < 3GB total

# Disk I/O (check for bottlenecks)
iostat -x 1 5
```

## Alerting Rules

### systemd-journald Alerts

```bash
# High latency alert
journalctl -u mcp-voice -f | while IFS= read -r line; do
  duration=$(echo "$line" | jq -r '.duration_ms // empty')
  if (( $(echo "$duration > 10000" | bc -l) )); then
    echo "ALERT: High latency detected: ${duration}ms" | \
      mail -s "MCP Voice High Latency" ops@example.com
  fi
done
```

### Error Rate Monitoring

```bash
# Count errors in last hour
journalctl -u mcp-voice --since "1 hour ago" | \
  jq 'select(.status=="failed")' | wc -l

# If > 10 errors per hour, alert
```

### GPU Memory Alert

```bash
# Monitor GPU VRAM
nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | while read mem; do
  # Alert if > 18GB on GPU 1 (leave 6GB headroom)
  if (( mem > 18000 )); then
    echo "ALERT: GPU VRAM exhaustion: ${mem}MB" | \
      mail -s "MCP Voice VRAM Alert" ops@example.com
  fi
done
```

## Prometheus Integration (Coming Soon)

### Metrics to Expose

```
# Counter: Total tool invocations
voice_tool_invocations_total{tool="search_race_data",status="success"}

# Histogram: Tool latency
voice_tool_latency_seconds{tool="process_voice_command"}

# Gauge: Current queue depth
voice_queue_depth{provider="ollama"}

# Counter: Errors by type
voice_errors_total{tool="process_voice_command",error_type="provider_failure"}
```

### Grafana Dashboard (Future)

Planned panels:
1. **Real-time latency**: P50/P95/P99 over time
2. **Error rate**: % of failed invocations
3. **GPU utilization**: K80 GPU 0 & GPU 1 memory/compute
4. **Tool breakdown**: Latency per tool (search, LLM, etc.)
5. **Provider health**: STT/TTS/LLM provider availability

## Debugging

### View All Tool Invocations

```bash
journalctl -u mcp-voice -o json | \
  jq -r '.MESSAGE | fromjson | "\(.timestamp) \(.tool) \(.duration_ms)ms"'
```

### Find Slow Commands

```bash
journalctl -u mcp-voice -o json | \
  jq 'select(.duration_ms > 10000) | "\(.tool): \(.duration_ms)ms - \(.error)"'
```

### Monitor Provider Failures

```bash
# STT failures
journalctl -u mcp-voice | grep -i "faster-whisper\|openai" | grep -i "error"

# Ollama failures
journalctl -u mcp-voice | grep -i "ollama" | grep -i "error\|connection"

# Database connection issues
journalctl -u mcp-voice | grep -i "sessionstate\|session" | grep -i "error"
```

## Dashboards

### Simple Text Dashboard

```bash
#!/bin/bash
while true; do
  clear
  echo "=== MCP Voice Pipeline Status ==="
  echo "Last 10 minutes:"
  
  # Error rate
  total=$(journalctl -u mcp-voice --since "10 minutes ago" -o json | jq 'select(.event_type=="voice_tool_invocation")' | wc -l)
  errors=$(journalctl -u mcp-voice --since "10 minutes ago" -o json | jq 'select(.status=="failed")' | wc -l)
  echo "Invocations: $total | Errors: $errors | Rate: $(( errors * 100 / total ))%"
  
  # Latency
  echo "Latencies (ms):"
  journalctl -u mcp-voice --since "10 minutes ago" -o json | \
    jq -r '.duration_ms // empty' | sort -n | \
    awk '{sum+=$1; if(NR==1) min=$1; if(NR==int(NR*0.5)) p50=$1; if(NR==int(NR*0.95)) p95=$1; max=$1} END {print "  Min: " min "  P50: " p50 "  P95: " p95 "  Max: " max}'
  
  sleep 10
done
```

## Incidents

### Issue: High Latency (> 10s)

**Check:**
1. GPU VRAM: `nvidia-smi`
2. CPU load: `top`
3. Ollama status: `curl -s http://localhost:11434/api/tags`

**Solution:**
- Restart Ollama if needed: `systemctl restart ollama`
- Check logs: `journalctl -u mcp-voice -f`
- Reduce concurrent requests

### Issue: High Error Rate (> 5%)

**Check:**
1. SessionState available: Look for "SessionState registered" in logs
2. Ollama running: `curl http://localhost:11434/api/tags`
3. Network connectivity: `ping ollama-server`

**Solution:**
- Restart MCP server: `systemctl restart mcp-voice`
- Verify telemetry connection: Check SessionState logs

### Issue: GPU Memory Exhaustion

**Check:**
```bash
nvidia-smi
# Should show < 2GB on GPU 0, < 14GB on GPU 1
```

**Solution:**
- Restart MCP server (releases GPU 0)
- Restart Ollama (releases GPU 1)
- Use quantized LLM model if needed

## Continuous Monitoring Setup

```bash
# systemd service with auto-restart
[Unit]
Description=MCP Voice Monitoring
After=mcp-voice.service

[Service]
Type=simple
ExecStart=/usr/local/bin/mcp-voice-monitor.sh
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

## Recommended Alert Channels

- Slack: `#mcp-voice-alerts`
- PagerDuty: Critical only (error rate > 10%, P95 > 15s)
- Grafana: Dashboard link in each alert
- Email: Ops team for daily summary
