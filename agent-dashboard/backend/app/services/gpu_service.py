"""Service for GPU metrics."""

import random
from datetime import datetime
from typing import Optional

from ..models import GPUMetrics


class GPUService:
    """Manage GPU metrics."""

    async def get_gpu_metrics(self) -> Optional[GPUMetrics]:
        """Get GPU metrics from garage-core."""
        # Simulate GPU metrics (in production, query actual Ollama)
        vram_used = random.uniform(5000, 35000)  # MB
        vram_total = 40000  # 40GB typical GPU memory

        models = []
        if random.random() < 0.8:
            models.append("gemma4:e4b")
        if random.random() < 0.3:
            models.append("gemma4:26b")
        if random.random() < 0.6:
            models.append("garage-ai-v12")

        return GPUMetrics(
            device="garage-core",
            vram_used_mb=vram_used,
            vram_total_mb=vram_total,
            vram_percent=(vram_used / vram_total) * 100,
            models_loaded=models,
            inference_queue_depth=random.randint(0, 10),
            avg_inference_time_ms=random.uniform(100, 1000),
            gpu_temp_celsius=40 + random.gauss(0, 5),
        )

    async def get_gpu_history(self, hours: int = 24) -> list[dict]:
        """Get GPU metrics history."""
        history = []

        for i in range(hours * 60):  # One entry per minute
            vram_used = random.gauss(20000, 5000)
            vram_used = max(0, min(40000, vram_used))

            history.append({
                "timestamp": datetime.utcnow() - datetime.timedelta(minutes=i),
                "vram_used_mb": vram_used,
                "vram_percent": (vram_used / 40000) * 100,
                "temp_celsius": 40 + random.gauss(0, 5),
                "inference_queue": random.randint(0, 10),
            })

        return history

    async def get_model_performance(self, model_name: str) -> dict:
        """Get model performance stats."""
        return {
            "model_name": model_name,
            "inferences_total": random.randint(100, 10000),
            "avg_inference_time_ms": random.uniform(100, 1000),
            "errors": random.randint(0, 10),
            "last_inference": datetime.utcnow() - datetime.timedelta(seconds=random.randint(1, 300)),
        }
