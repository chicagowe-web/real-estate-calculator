"""Data models for NotificationAgent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Channel(Enum):
    """Notification channel."""
    EMAIL = "email"
    SLACK = "slack"
    TELEGRAM = "telegram"
    SMS = "sms"
    WEBHOOK = "webhook"


class Priority(Enum):
    """Notification priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Notification:
    """Single notification."""
    notification_id: str
    title: str
    message: str
    priority: Priority
    channels: list[Channel]
    recipient: str
    sent_at: datetime = None
    delivered: bool = False
    error: str = ""


@dataclass
class NotificationTemplate:
    """Notification template."""
    template_id: str
    name: str
    title_template: str
    message_template: str
    channels: list[Channel]
    priority: Priority


@dataclass
class NotificationMetrics:
    """Notification metrics."""
    total_sent: int = 0
    total_delivered: int = 0
    total_failed: int = 0
    by_channel: dict[str, int] = field(default_factory=dict)
    by_priority: dict[str, int] = field(default_factory=dict)
