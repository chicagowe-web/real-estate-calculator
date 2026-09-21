"""Data models for ModelManagementAgent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ModelStatus(Enum):
    """Model status."""
    IDLE = "idle"
    TRAINING = "training"
    INFERENCING = "inferencing"
    LOADING = "loading"
    UNLOADING = "unloading"
    ERROR = "error"


class ModelType(Enum):
    """Model type."""
    GARAGE_AI = "garage_ai"  # Automotive diagnostic
    OLLAMA = "ollama"  # Local inference
    EXTERNAL = "external"  # External API


@dataclass
class Model:
    """ML model metadata."""
    model_id: str
    name: str
    model_type: ModelType
    version: str
    device: str  # Where it's loaded
    status: ModelStatus
    vram_mb: int  # Memory usage
    eval_score: float = 0.0
    last_updated: datetime = None
    training_data_size: int = 0  # bytes
    known_issues: list[str] = field(default_factory=list)


@dataclass
class ModelMetrics:
    """Model performance metrics."""
    model_id: str
    inference_count: int = 0
    avg_inference_time_ms: float = 0.0
    error_count: int = 0
    success_rate: float = 0.0
    tokens_generated: int = 0
    vram_peak_mb: int = 0
    vram_avg_mb: int = 0


@dataclass
class TrainingJob:
    """Model training job."""
    job_id: str
    model_id: str
    device: str
    status: ModelStatus
    start_time: datetime = None
    end_time: datetime = None
    epoch: int = 0
    total_epochs: int = 0
    loss: float = 0.0
    accuracy: float = 0.0
    dataset_size: int = 0


@dataclass
class ModelUpdate:
    """Model update/version."""
    update_id: str
    model_id: str
    version: str
    changes: str
    eval_score_before: float
    eval_score_after: float
    compatibility: str  # "backward_compatible", "breaking"
    rollback_available: bool = True
