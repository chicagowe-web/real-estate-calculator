"""Data models for PerformanceOptimizationAgent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


@dataclass
class PerformanceMetric:
    """Performance metric."""
    metric_name: str
    device: str
    value: float
    timestamp: datetime
    unit: str


@dataclass
class Optimization:
    """Performance optimization."""
    optimization_id: str
    device: str
    parameter: str
    current_value: str
    recommended_value: str
    expected_improvement_percent: float
    applied: bool = False
    result_improvement_percent: float = 0.0


@dataclass
class TuningJob:
    """Auto-tuning job."""
    job_id: str
    device: str
    status: str  # "pending", "running", "completed"
    start_time: datetime = None
    end_time: datetime = None
    improvements_found: int = 0
    average_improvement: float = 0.0
