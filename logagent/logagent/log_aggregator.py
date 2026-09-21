"""Log collection and aggregation."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from typing import Optional

from .models import LogEntry, LogLevel, LogSource, LogPattern, LogMetrics

logger = logging.getLogger("logagent.log_aggregator")


class LogAggregator:
    """Collect and aggregate logs from multiple devices."""

    def __init__(self):
        self.logs: list[LogEntry] = []
        self.patterns: dict[str, LogPattern] = {}

    async def collect_logs(
        self,
        device: str,
        source: LogSource,
        since_minutes: int = 60,
    ) -> list[LogEntry]:
        """Collect logs from device.

        Args:
            device: Device to collect from
            source: Log source
            since_minutes: Minutes to collect from

        Returns:
            List of LogEntry
        """
        entries = []

        try:
            if source == LogSource.SYSTEM:
                cmd = f"ssh {device} 'journalctl --since {since_minutes}min -n 1000 --no-pager -o json' 2>/dev/null"
            elif source == LogSource.SECURITY:
                cmd = f"ssh {device} 'tail -n 1000 /var/log/auth.log 2>/dev/null' 2>/dev/null"
            else:
                cmd = f"ssh {device} 'tail -n 1000 /var/log/syslog 2>/dev/null' 2>/dev/null"

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        entry = LogEntry(
                            timestamp=datetime.utcnow(),
                            device=device,
                            source=source,
                            level=self._parse_level(line),
                            message=line[:200],
                        )
                        entries.append(entry)
                        self.logs.append(entry)

            logger.info(f"Collected {len(entries)} logs from {device}/{source.value}")

        except Exception as e:
            logger.error(f"Log collection failed: {e}")

        return entries

    async def detect_patterns(self) -> list[LogPattern]:
        """Detect patterns in logs.

        Returns:
            List of LogPattern
        """
        patterns = []

        # Analyze error frequency
        errors = [l for l in self.logs if l.level in [LogLevel.ERROR, LogLevel.CRITICAL]]
        if len(errors) > 10:
            pattern = LogPattern(
                pattern_id="error_spike",
                name="Error Spike",
                description=f"{len(errors)} errors detected",
                severity=LogLevel.WARNING,
                frequency=len(errors),
                affected_devices=list(set(e.device for e in errors)),
                last_occurrence=datetime.utcnow(),
            )
            patterns.append(pattern)
            self.patterns["error_spike"] = pattern

        # Detect repeating messages
        message_counts = {}
        for log in self.logs:
            message_counts[log.message] = message_counts.get(log.message, 0) + 1

        for msg, count in message_counts.items():
            if count > 5:
                pattern = LogPattern(
                    pattern_id=f"repeat_{hash(msg) % 10000}",
                    name="Repeating Message",
                    description=msg[:50],
                    severity=LogLevel.INFO,
                    frequency=count,
                    last_occurrence=datetime.utcnow(),
                )
                patterns.append(pattern)

        logger.info(f"Detected {len(patterns)} patterns")
        return patterns

    async def search_logs(self, query: str, limit: int = 100) -> list[LogEntry]:
        """Search logs by query.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Matching LogEntry list
        """
        results = [
            log for log in self.logs
            if query.lower() in log.message.lower()
        ][:limit]

        return results

    def get_metrics(self) -> LogMetrics:
        """Get log metrics.

        Returns:
            LogMetrics
        """
        metrics = LogMetrics(
            total_entries=len(self.logs),
            entries_by_level={},
            entries_by_source={},
            entries_by_device={},
            patterns_detected=len(self.patterns),
            unique_patterns=list(self.patterns.values()),
        )

        # Count by level
        for level in LogLevel:
            count = sum(1 for l in self.logs if l.level == level)
            if count > 0:
                metrics.entries_by_level[level.value] = count

        # Count by source
        for source in LogSource:
            count = sum(1 for l in self.logs if l.source == source)
            if count > 0:
                metrics.entries_by_source[source.value] = count

        # Count by device
        devices = set(l.device for l in self.logs)
        for device in devices:
            count = sum(1 for l in self.logs if l.device == device)
            metrics.entries_by_device[device] = count

        # Count errors
        now = datetime.utcnow()
        day_ago = datetime.utcfromtimestamp(now.timestamp() - 86400)
        errors_24h = [
            l for l in self.logs
            if l.timestamp >= day_ago and l.level in [LogLevel.ERROR, LogLevel.CRITICAL]
        ]
        metrics.errors_last_24h = sum(1 for e in errors_24h if e.level == LogLevel.ERROR)
        metrics.critical_last_24h = sum(1 for e in errors_24h if e.level == LogLevel.CRITICAL)

        return metrics

    def _parse_level(self, line: str) -> LogLevel:
        """Parse log level from line."""
        line_lower = line.lower()
        if "critical" in line_lower or "fatal" in line_lower:
            return LogLevel.CRITICAL
        elif "error" in line_lower:
            return LogLevel.ERROR
        elif "warning" in line_lower or "warn" in line_lower:
            return LogLevel.WARNING
        elif "info" in line_lower:
            return LogLevel.INFO
        return LogLevel.DEBUG
