"""Coordinate data synchronization across devices."""

from __future__ import annotations

import logging
import subprocess
import uuid
from datetime import datetime, timedelta
from typing import Optional

from .models import SyncJob, SyncStatus, SyncPair, SyncMetrics

logger = logging.getLogger("datasyncagent.sync_coordinator")


class SyncCoordinator:
    """Orchestrate data synchronization across distributed devices."""

    def __init__(self):
        self.sync_jobs: dict[str, SyncJob] = {}
        self.sync_pairs: dict[str, SyncPair] = {}
        self.sync_history: list[SyncJob] = []

    async def start_sync(
        self,
        source_device: str,
        target_devices: list[str],
        source_path: str,
        target_path: str,
    ) -> SyncJob:
        """Start synchronization job.

        Args:
            source_device: Source device
            target_devices: Target devices
            source_path: Source path
            target_path: Target path

        Returns:
            SyncJob
        """
        job_id = f"sync-{uuid.uuid4().hex[:8]}"

        job = SyncJob(
            job_id=job_id,
            source_device=source_device,
            target_devices=target_devices,
            source_path=source_path,
            target_path=target_path,
            status=SyncStatus.IN_PROGRESS,
            start_time=datetime.utcnow(),
        )

        self.sync_jobs[job_id] = job

        try:
            # Sync using rsync
            for target in target_devices:
                cmd = f"ssh {source_device} 'rsync -avz {source_path} {target}:{target_path}' 2>/dev/null"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3600)

                if result.returncode != 0:
                    job.status = SyncStatus.PARTIAL
                    job.error = result.stderr
                else:
                    # Parse rsync output for bytes synced
                    if "bytes transferred" in result.stderr:
                        parts = result.stderr.split("bytes transferred")
                        job.bytes_synced += int(parts[0].split()[-1])
                    job.files_synced += 1

            if job.status != SyncStatus.PARTIAL:
                job.status = SyncStatus.SUCCESS

            logger.info(f"Sync {job_id} completed: {job.bytes_synced} bytes")

        except Exception as e:
            job.status = SyncStatus.FAILED
            job.error = str(e)
            logger.error(f"Sync failed: {e}")

        finally:
            job.end_time = datetime.utcnow()
            self.sync_history.append(job)

        return job

    async def setup_continuous_sync(
        self,
        device_a: str,
        device_b: str,
        paths: list[str],
    ) -> SyncPair:
        """Setup continuous bidirectional sync between devices.

        Args:
            device_a: Device A
            device_b: Device B
            paths: Paths to sync

        Returns:
            SyncPair
        """
        pair_id = f"pair-{uuid.uuid4().hex[:8]}"

        pair = SyncPair(
            pair_id=pair_id,
            device_a=device_a,
            device_b=device_b,
            paths=paths,
            enabled=True,
            last_sync=datetime.utcnow(),
            next_sync=datetime.utcnow() + timedelta(hours=1),
        )

        self.sync_pairs[pair_id] = pair
        logger.info(f"Setup continuous sync: {device_a} <-> {device_b}")

        return pair

    async def verify_sync(self, job_id: str) -> bool:
        """Verify sync integrity.

        Args:
            job_id: Sync job ID

        Returns:
            True if verified
        """
        if job_id not in self.sync_jobs:
            return False

        job = self.sync_jobs[job_id]

        try:
            # Compare checksums on source and target
            for target in job.target_devices:
                cmd = f"ssh {job.source_device} 'find {job.source_path} -type f -exec md5sum {{}} \\; | sort' 2>/dev/null"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)

                if result.returncode == 0:
                    logger.info(f"Verified sync to {target}")
                else:
                    logger.warning(f"Sync verification failed for {target}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Verification error: {e}")
            return False

    def get_metrics(self) -> SyncMetrics:
        """Get sync metrics.

        Returns:
            SyncMetrics
        """
        successful = sum(1 for j in self.sync_history if j.status == SyncStatus.SUCCESS)
        failed = sum(1 for j in self.sync_history if j.status == SyncStatus.FAILED)
        total_bytes = sum(j.bytes_synced for j in self.sync_history)

        durations = [
            (j.end_time - j.start_time).total_seconds()
            for j in self.sync_history
            if j.start_time and j.end_time
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        return SyncMetrics(
            total_syncs=len(self.sync_history),
            successful_syncs=successful,
            failed_syncs=failed,
            total_bytes_synced=total_bytes,
            avg_sync_time_seconds=avg_duration,
            sync_pairs_active=sum(1 for p in self.sync_pairs.values() if p.enabled),
        )
