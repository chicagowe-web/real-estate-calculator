"""Service for backup tracking."""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from ..models import BackupInfo


class BackupService:
    """Manage backups."""

    def __init__(self):
        self.backups: dict[str, BackupInfo] = {}
        self._generate_sample_backups()

    def _generate_sample_backups(self):
        """Generate sample backups for demo."""
        devices = ["garage-core", "tp", "kali", "canfd", "canfd2"]

        for device in devices:
            for i in range(3):
                backup_id = str(uuid.uuid4())[:8]
                backup = BackupInfo(
                    backup_id=backup_id,
                    device=device,
                    timestamp=datetime.utcnow() - timedelta(days=i),
                    size_gb=random.uniform(50, 500),
                    status=random.choice(["success", "failed"]) if i > 0 else "success",
                    restore_points_available=random.randint(3, 10),
                    last_recovery_tested=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                )
                self.backups[backup_id] = backup

    async def get_recent_backups(self, limit: int = 10) -> List[BackupInfo]:
        """Get recent backups."""
        backups = list(self.backups.values())
        backups.sort(key=lambda b: b.timestamp, reverse=True)
        return backups[:limit]

    async def get_device_backups(self, device: str) -> List[BackupInfo]:
        """Get backups for a device."""
        return [b for b in self.backups.values() if b.device == device]

    async def get_backup(self, backup_id: str) -> Optional[BackupInfo]:
        """Get specific backup."""
        return self.backups.get(backup_id)

    async def create_backup(self, device: str, size_gb: float) -> BackupInfo:
        """Create new backup."""
        backup_id = str(uuid.uuid4())[:8]
        backup = BackupInfo(
            backup_id=backup_id,
            device=device,
            timestamp=datetime.utcnow(),
            size_gb=size_gb,
            status="in_progress",
            restore_points_available=0,
        )
        self.backups[backup_id] = backup
        return backup
