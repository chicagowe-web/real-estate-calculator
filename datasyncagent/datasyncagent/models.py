"""Data models for DataSyncAgent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SyncStatus(Enum):
    """Sync job status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class SyncJob:
    """Data synchronization job."""
    job_id: str
    source_device: str
    target_devices: list[str]
    source_path: str
    target_path: str
    status: SyncStatus
    start_time: datetime = None
    end_time: datetime = None
    files_synced: int = 0
    bytes_synced: int = 0
    error: str = ""


@dataclass
class SyncPair:
    """Device pair for continuous sync."""
    pair_id: str
    device_a: str
    device_b: str
    paths: list[str]
    enabled: bool
    last_sync: datetime = None
    next_sync: datetime = None


@dataclass
class SyncMetrics:
    """Sync metrics."""
    total_syncs: int = 0
    successful_syncs: int = 0
    failed_syncs: int = 0
    total_bytes_synced: int = 0
    avg_sync_time_seconds: float = 0.0
    sync_pairs_active: int = 0
