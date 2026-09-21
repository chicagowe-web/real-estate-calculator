"""Data models for SecurityAgent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ThreatLevel(Enum):
    """Threat level classification."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    """Security event type."""
    FAILED_LOGIN = "failed_login"
    SUCCESSFUL_LOGIN = "successful_login"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    FILE_ACCESS = "file_access"
    NETWORK_SCAN = "network_scan"
    INTRUSION_ATTEMPT = "intrusion_attempt"
    MALWARE_DETECTION = "malware_detection"
    PATCH_AVAILABLE = "patch_available"


@dataclass
class SecurityEvent:
    """Security event."""
    event_id: str
    event_type: SecurityEventType
    device: str
    threat_level: ThreatLevel
    timestamp: datetime
    details: str
    source_ip: str = ""
    user: str = ""
    action_taken: str = ""


@dataclass
class SecurityMetrics:
    """Security metrics."""
    total_events_24h: int = 0
    critical_events: int = 0
    failed_login_attempts: int = 0
    failed_login_sources: list[str] = field(default_factory=list)
    intrusion_attempts: int = 0
    devices_at_risk: list[str] = field(default_factory=list)
    patches_available: int = 0
    last_security_scan: datetime = None
