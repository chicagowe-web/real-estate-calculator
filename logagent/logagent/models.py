"""Data models for LogAggregationAgent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    """Log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogSource(Enum):
    """Log source."""
    SYSTEM = "system"
    APPLICATION = "application"
    SECURITY = "security"
    BACKUP = "backup"
    MONITORING = "monitoring"


@dataclass
class LogEntry:
    """Single log entry."""
    timestamp: datetime
    device: str
    source: LogSource
    level: LogLevel
    message: str
    context: dict = field(default_factory=dict)


@dataclass
class LogPattern:
    """Pattern detected in logs."""
    pattern_id: str
    name: str
    description: str
    severity: LogLevel
    frequency: int  # occurrences per day
    affected_devices: list[str] = field(default_factory=list)
    last_occurrence: datetime = None


@dataclass
class LogMetrics:
    """Log aggregation metrics."""
    total_entries: int
    entries_by_level: dict[str, int] = field(default_factory=dict)
    entries_by_source: dict[str, int] = field(default_factory=dict)
    entries_by_device: dict[str, int] = field(default_factory=dict)
    patterns_detected: int = 0
    unique_patterns: list[LogPattern] = field(default_factory=list)
    errors_last_24h: int = 0
    critical_last_24h: int = 0
