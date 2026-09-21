"""Model lifecycle management."""

from __future__ import annotations

import logging
import subprocess
import uuid
from datetime import datetime
from typing import Optional

from .models import Model, ModelStatus, ModelType, ModelMetrics, TrainingJob, ModelUpdate

logger = logging.getLogger("modelagent.model_manager")


class ModelManager:
    """Manage ML models across infrastructure."""

    def __init__(self):
        self.models: dict[str, Model] = {}
        self.metrics: dict[str, ModelMetrics] = {}
        self.training_jobs: dict[str, TrainingJob] = {}
        self.updates: dict[str, ModelUpdate] = {}

    async def register_model(
        self,
        name: str,
        model_type: ModelType,
        device: str,
        version: str,
        vram_mb: int,
    ) -> Model:
        """Register a model.

        Args:
            name: Model name
            model_type: Type of model
            device: Device hosting model
            version: Model version
            vram_mb: VRAM required

        Returns:
            Model
        """
        model_id = f"model-{uuid.uuid4().hex[:8]}"

        model = Model(
            model_id=model_id,
            name=name,
            model_type=model_type,
            version=version,
            device=device,
            status=ModelStatus.IDLE,
            vram_mb=vram_mb,
            last_updated=datetime.utcnow(),
        )

        self.models[model_id] = model
        self.metrics[model_id] = ModelMetrics(model_id=model_id)

        logger.info(f"Registered model: {name} v{version} on {device}")
        return model

    async def load_model(self, model_id: str) -> bool:
        """Load model into memory.

        Args:
            model_id: Model ID

        Returns:
            True if successful
        """
        if model_id not in self.models:
            logger.error(f"Model {model_id} not found")
            return False

        model = self.models[model_id]
        model.status = ModelStatus.LOADING

        try:
            if model.model_type == ModelType.OLLAMA:
                cmd = f"ssh {model.device} 'ollama pull {model.name}:latest' 2>/dev/null"
            else:
                cmd = f"ssh {model.device} 'load-model {model.name}' 2>/dev/null"

            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=600)

            if result.returncode == 0:
                model.status = ModelStatus.IDLE
                logger.info(f"Loaded model: {model.name}")
                return True
            else:
                model.status = ModelStatus.ERROR
                logger.error(f"Failed to load model: {result.stderr}")
                return False

        except Exception as e:
            model.status = ModelStatus.ERROR
            logger.error(f"Load failed: {e}")
            return False

    async def unload_model(self, model_id: str) -> bool:
        """Unload model from memory.

        Args:
            model_id: Model ID

        Returns:
            True if successful
        """
        if model_id not in self.models:
            return False

        model = self.models[model_id]
        model.status = ModelStatus.UNLOADING

        try:
            if model.model_type == ModelType.OLLAMA:
                cmd = f"ssh {model.device} 'ollama unload {model.name}' 2>/dev/null"
            else:
                cmd = f"ssh {model.device} 'unload-model {model.name}' 2>/dev/null"

            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=60)

            if result.returncode == 0:
                model.status = ModelStatus.IDLE
                logger.info(f"Unloaded model: {model.name}")
                return True

        except Exception as e:
            logger.error(f"Unload failed: {e}")

        return False

    async def start_training(
        self,
        model_id: str,
        dataset_size: int,
        epochs: int = 10,
    ) -> TrainingJob:
        """Start training job for model.

        Args:
            model_id: Model to train
            dataset_size: Training dataset size
            epochs: Number of epochs

        Returns:
            TrainingJob
        """
        if model_id not in self.models:
            return None

        model = self.models[model_id]
        job_id = f"train-{uuid.uuid4().hex[:8]}"

        job = TrainingJob(
            job_id=job_id,
            model_id=model_id,
            device=model.device,
            status=ModelStatus.TRAINING,
            start_time=datetime.utcnow(),
            total_epochs=epochs,
            dataset_size=dataset_size,
        )

        self.training_jobs[job_id] = job
        model.status = ModelStatus.TRAINING

        logger.info(f"Started training job: {job_id} for {model.name}")
        return job

    async def publish_update(
        self,
        model_id: str,
        version: str,
        changes: str,
        eval_score: float,
    ) -> ModelUpdate:
        """Publish model update.

        Args:
            model_id: Model being updated
            version: New version
            changes: Changes description
            eval_score: New evaluation score

        Returns:
            ModelUpdate
        """
        if model_id not in self.models:
            return None

        model = self.models[model_id]
        update_id = f"update-{uuid.uuid4().hex[:8]}"

        update = ModelUpdate(
            update_id=update_id,
            model_id=model_id,
            version=version,
            changes=changes,
            eval_score_before=model.eval_score,
            eval_score_after=eval_score,
            compatibility="backward_compatible" if eval_score >= model.eval_score else "breaking",
            rollback_available=True,
        )

        self.updates[update_id] = update
        model.version = version
        model.eval_score = eval_score

        logger.info(f"Published update: {model.name} v{version} (score: {eval_score})")
        return update

    def get_gpu_utilization(self) -> dict:
        """Get GPU utilization across devices.

        Returns:
            Device -> utilization percentage
        """
        utilization = {}

        devices = set(m.device for m in self.models.values())
        for device in devices:
            try:
                cmd = f"ssh {device} 'nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader 2>/dev/null' 2>/dev/null"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    util = float(result.stdout.strip().rstrip("%"))
                    utilization[device] = util

            except Exception as e:
                logger.warning(f"GPU utilization query failed: {e}")

        return utilization

    def get_model_status_summary(self) -> dict:
        """Get summary of all models.

        Returns:
            Status summary
        """
        return {
            "total_models": len(self.models),
            "models_by_status": {
                status.value: sum(1 for m in self.models.values() if m.status == status)
                for status in ModelStatus
            },
            "total_vram_used_mb": sum(m.vram_mb for m in self.models.values()),
            "active_training_jobs": sum(1 for j in self.training_jobs.values() if j.status == ModelStatus.TRAINING),
        }
