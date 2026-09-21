"""Data models for BackupAgent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class BackupStatus(Enum):
    """Backup status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    INCOMPLETE = "incomplete"


class BackupType(Enum):
    """Backup type."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class RecoveryStatus(Enum):
    """Recovery status."""
    NOT_TESTED = "not_tested"
    TESTED = "tested"
    VERIFIED = "verified"
    FAILED = "failed"


@dataclass
class BackupTarget:
    """Backup target configuration."""
    device: str
    paths: list[str]
    exclude_patterns: list[str] = field(default_factory=list)
    retention_days: int = 30
    backup_type: BackupType = BackupType.INCREMENTAL


@dataclass
class BackupJob:
    """Single backup job."""
    job_id: str
    device: str
    target_paths: list[str]
    backup_type: BackupType
    status: BackupStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    size_bytes: int = 0
    compressed_bytes: int = 0
    files_count: int = 0
    error: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def compression_ratio(self) -> float:
        if self.size_bytes > 0:
            return self.compressed_bytes / self.size_bytes
        return 0.0


@dataclass
class BackupStore:
    """Backup storage location."""
    name: str
    location: str  # /backup/external, /mnt/nas, s3://bucket
    total_bytes: int
    used_bytes: int
    available_bytes: int
    retention_strategy: str  # "fifo", "lru", "keep_latest_n"

    @property
    def utilization_percent(self) -> float:
        if self.total_bytes > 0:
            return (self.used_bytes / self.total_bytes) * 100
        return 0.0


@dataclass
class RestorePoint:
    """Point-in-time restore capability."""
    backup_id: str
    device: str
    timestamp: datetime
    backup_type: BackupType
    size_bytes: int
    recovery_status: RecoveryStatus
    metadata: dict = field(default_factory=dict)

    @property
    def age_days(self) -> int:
        return (datetime.utcnow() - self.timestamp).days


@dataclass
class RecoveryJob:
    """Recovery operation."""
    recovery_id: str
    restore_point_id: str
    target_device: str
    target_paths: list[str]
    status: BackupStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    files_restored: int = 0
    error: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


@dataclass
class BackupMetrics:
    """Backup metrics and statistics."""
    total_backups: int
    successful_backups: int
    failed_backups: int
    total_data_backed_up: int  # bytes
    compression_ratio_avg: float
    backup_frequency_hours: int
    last_successful_backup: Optional[datetime] = None
    next_scheduled_backup: Optional[datetime] = None
    restore_points_available: int = 0
    oldest_backup_days: int = 0
