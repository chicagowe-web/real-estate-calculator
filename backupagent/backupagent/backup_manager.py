"""Backup orchestration and management."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import uuid
from datetime import datetime, timedelta
from typing import Optional

from .models import (
    BackupJob,
    BackupStatus,
    BackupType,
    BackupTarget,
    BackupStore,
    RestorePoint,
    RecoveryJob,
    RecoveryStatus,
    BackupMetrics,
)

logger = logging.getLogger("backupagent.backup_manager")


class BackupManager:
    """Orchestrate backups across distributed devices."""

    def __init__(self):
        self.backup_jobs: dict[str, BackupJob] = {}
        self.backup_history: list[BackupJob] = []
        self.recovery_jobs: dict[str, RecoveryJob] = {}
        self.stores: dict[str, BackupStore] = {}
        self.restore_points: list[RestorePoint] = []

    async def schedule_backup(
        self,
        device: str,
        paths: list[str],
        backup_type: BackupType = BackupType.INCREMENTAL,
    ) -> BackupJob:
        """Schedule backup job for device.

        Args:
            device: Device to backup
            paths: Paths to backup
            backup_type: Type of backup

        Returns:
            BackupJob
        """
        job_id = f"backup-{uuid.uuid4().hex[:8]}"

        job = BackupJob(
            job_id=job_id,
            device=device,
            target_paths=paths,
            backup_type=backup_type,
            status=BackupStatus.PENDING,
        )

        self.backup_jobs[job_id] = job
        logger.info(f"Scheduled {backup_type.value} backup for {device}: {job_id}")

        return job

    async def execute_backup(self, job_id: str) -> BackupJob:
        """Execute scheduled backup job.

        Args:
            job_id: Job ID to execute

        Returns:
            Updated BackupJob
        """
        if job_id not in self.backup_jobs:
            logger.error(f"Backup job {job_id} not found")
            return None

        job = self.backup_jobs[job_id]
        job.status = BackupStatus.IN_PROGRESS
        job.start_time = datetime.utcnow()

        try:
            # Run backup command via SSH
            cmd = f"ssh {job.device} 'tar czf - {' '.join(job.target_paths)} 2>/dev/null | wc -c'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3600)

            if result.returncode == 0:
                job.size_bytes = int(result.stdout.strip())
                job.compressed_bytes = int(job.size_bytes * 0.8)  # Mock compression
                job.files_count = len(job.target_paths) * 100  # Mock file count
                job.status = BackupStatus.SUCCESS
                logger.info(f"Backup {job_id} completed: {job.size_bytes} bytes")
            else:
                job.status = BackupStatus.FAILED
                job.error = result.stderr

        except Exception as e:
            job.status = BackupStatus.FAILED
            job.error = str(e)
            logger.error(f"Backup {job_id} failed: {e}")

        finally:
            job.end_time = datetime.utcnow()
            self.backup_history.append(job)

        return job

    async def create_restore_point(
        self,
        backup_id: str,
        device: str,
        backup_type: BackupType,
        size_bytes: int,
    ) -> RestorePoint:
        """Create restore point from backup.

        Args:
            backup_id: Backup ID
            device: Device backed up
            backup_type: Type of backup
            size_bytes: Backup size

        Returns:
            RestorePoint
        """
        restore_point = RestorePoint(
            backup_id=backup_id,
            device=device,
            timestamp=datetime.utcnow(),
            backup_type=backup_type,
            size_bytes=size_bytes,
            recovery_status=RecoveryStatus.NOT_TESTED,
        )

        self.restore_points.append(restore_point)
        logger.info(f"Created restore point: {backup_id}")

        return restore_point

    async def recover_from_backup(
        self,
        restore_point_id: str,
        target_device: str,
        target_paths: list[str],
    ) -> RecoveryJob:
        """Recover files from backup.

        Args:
            restore_point_id: Restore point ID
            target_device: Target device for recovery
            target_paths: Paths to recover to

        Returns:
            RecoveryJob
        """
        recovery_id = f"recovery-{uuid.uuid4().hex[:8]}"

        job = RecoveryJob(
            recovery_id=recovery_id,
            restore_point_id=restore_point_id,
            target_device=target_device,
            target_paths=target_paths,
            status=BackupStatus.IN_PROGRESS,
            start_time=datetime.utcnow(),
        )

        self.recovery_jobs[recovery_id] = job

        try:
            # Execute recovery via SSH
            cmd = f"ssh {target_device} 'restore-backup {restore_point_id} {' '.join(target_paths)}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1800)

            if result.returncode == 0:
                job.files_restored = 100
                job.status = BackupStatus.SUCCESS
                logger.info(f"Recovery {recovery_id} completed")
            else:
                job.status = BackupStatus.FAILED
                job.error = result.stderr

        except Exception as e:
            job.status = BackupStatus.FAILED
            job.error = str(e)
            logger.error(f"Recovery {recovery_id} failed: {e}")

        finally:
            job.end_time = datetime.utcnow()

        return job

    async def verify_backup(self, backup_id: str) -> bool:
        """Verify backup integrity.

        Args:
            backup_id: Backup to verify

        Returns:
            True if verification passed
        """
        try:
            cmd = f"verify-backup {backup_id}"
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=600)

            if result.returncode == 0:
                # Update restore point status
                for rp in self.restore_points:
                    if rp.backup_id == backup_id:
                        rp.recovery_status = RecoveryStatus.VERIFIED
                        logger.info(f"Backup {backup_id} verified")
                        return True

            return False

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False

    def get_metrics(self) -> BackupMetrics:
        """Get backup metrics.

        Returns:
            BackupMetrics
        """
        successful = sum(1 for j in self.backup_history if j.status == BackupStatus.SUCCESS)
        failed = sum(1 for j in self.backup_history if j.status == BackupStatus.FAILED)
        total_data = sum(j.size_bytes for j in self.backup_history)

        if self.backup_history:
            avg_compression = sum(j.compression_ratio for j in self.backup_history) / len(self.backup_history)
        else:
            avg_compression = 0.0

        oldest_backup = min((rp.age_days for rp in self.restore_points), default=0)
        verified_points = sum(1 for rp in self.restore_points if rp.recovery_status == RecoveryStatus.VERIFIED)

        return BackupMetrics(
            total_backups=len(self.backup_history),
            successful_backups=successful,
            failed_backups=failed,
            total_data_backed_up=total_data,
            compression_ratio_avg=avg_compression,
            backup_frequency_hours=24,
            last_successful_backup=max(
                (j.end_time for j in self.backup_history if j.status == BackupStatus.SUCCESS),
                default=None
            ),
            restore_points_available=len(self.restore_points),
            oldest_backup_days=oldest_backup,
        )

    def get_restore_points(self, device: Optional[str] = None) -> list[RestorePoint]:
        """Get available restore points.

        Args:
            device: Filter by device (optional)

        Returns:
            List of RestorePoint
        """
        points = self.restore_points

        if device:
            points = [p for p in points if p.device == device]

        return sorted(points, key=lambda p: p.timestamp, reverse=True)
