"""API response models for dashboard."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent status."""
    ONLINE = "online"
    PROCESSING = "processing"
    IDLE = "idle"
    ERROR = "error"
    OFFLINE = "offline"


class AlertSeverity(str, Enum):
    """Alert severity."""
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class DeviceMetrics(BaseModel):
    """Device metrics."""
    device: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_in_mbps: float
    network_out_mbps: float
    temperature_celsius: Optional[float] = None
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentInfo(BaseModel):
    """Agent information."""
    name: str
    status: AgentStatus
    last_activity: datetime
    task_count: int = 0
    success_rate: float = 100.0
    avg_response_time_ms: float = 0.0
    error_count: int = 0


class Alert(BaseModel):
    """System alert."""
    alert_id: str
    title: str
    description: str
    severity: AlertSeverity
    device: str
    timestamp: datetime
    resolved: bool = False
    suggested_action: Optional[str] = None


class DeploymentStatus(BaseModel):
    """Deployment status."""
    deployment_id: str
    repo: str
    branch: str
    commit: str
    status: str  # "pending", "deploying", "success", "failed"
    start_time: datetime
    end_time: Optional[datetime] = None
    deployed_count: int = 0
    total_devices: int = 0
    rollback_available: bool = True


class BackupInfo(BaseModel):
    """Backup information."""
    backup_id: str
    device: str
    timestamp: datetime
    size_gb: float
    status: str  # "success", "failed", "in_progress"
    restore_points_available: int = 0
    last_recovery_tested: Optional[datetime] = None


class GPUMetrics(BaseModel):
    """GPU metrics."""
    device: str
    vram_used_mb: float
    vram_total_mb: float
    vram_percent: float
    models_loaded: List[str] = []
    inference_queue_depth: int = 0
    avg_inference_time_ms: float = 0.0
    gpu_temp_celsius: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LogPattern(BaseModel):
    """Detected log pattern."""
    pattern_id: str
    name: str
    frequency: int
    severity: AlertSeverity
    affected_devices: List[str]
    last_occurrence: datetime


class SecurityEvent(BaseModel):
    """Security event."""
    event_id: str
    event_type: str
    severity: AlertSeverity
    device: str
    description: str
    timestamp: datetime
    action_taken: Optional[str] = None


class PerformanceMetric(BaseModel):
    """Performance metric for trends."""
    metric_name: str
    device: str
    value: float
    unit: str
    timestamp: datetime


class DashboardOverview(BaseModel):
    """Dashboard overview data."""
    agents: List[AgentInfo]
    devices: List[DeviceMetrics]
    recent_alerts: List[Alert]
    deployments: List[DeploymentStatus]
    backups: List[BackupInfo]
    gpu_metrics: Optional[GPUMetrics] = None
    system_health: float  # 0-100
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WebSocketMessage(BaseModel):
    """WebSocket message format."""
    type: str  # "update", "alert", "metric", "status"
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
