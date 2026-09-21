"""Data models for DeploymentAgent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DeploymentStatus(Enum):
    """Deployment status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Deployment:
    """Code deployment."""
    deployment_id: str
    repo: str
    branch: str
    commit: str
    target_devices: list[str]
    status: DeploymentStatus
    start_time: datetime = None
    end_time: datetime = None
    deployed_devices: list[str] = field(default_factory=list)
    failed_devices: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class HealthCheck:
    """Health check after deployment."""
    deployment_id: str
    device: str
    checks_passed: int
    checks_total: int
    endpoints_responding: list[str] = field(default_factory=list)
    endpoints_down: list[str] = field(default_factory=list)
    healthy: bool = False


@dataclass
class Rollback:
    """Rollback operation."""
    rollback_id: str
    deployment_id: str
    target_devices: list[str]
    previous_commit: str
    status: DeploymentStatus
    start_time: datetime = None
    end_time: datetime = None
