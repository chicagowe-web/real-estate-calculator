"""Service for device metrics."""

import random
from datetime import datetime
from typing import List, Optional

from ..models import DeviceMetrics


class DeviceService:
    """Manage device metrics."""

    DEVICES = ["garage-core", "tp", "kali", "canfd", "canfd2"]

    async def get_all_devices(self) -> List[DeviceMetrics]:
        """Get all device metrics."""
        devices = []

        for device_name in self.DEVICES:
            # Simulate realistic metrics
            cpu = random.gauss(40, 15)
            cpu = max(0, min(100, cpu))

            memory = random.gauss(60, 15)
            memory = max(0, min(100, memory))

            disk = random.gauss(50, 10)
            disk = max(0, min(100, disk))

            device = DeviceMetrics(
                device=device_name,
                cpu_percent=cpu,
                memory_percent=memory,
                disk_percent=disk,
                network_in_mbps=random.uniform(0, 100),
                network_out_mbps=random.uniform(0, 100),
                temperature_celsius=45 + random.gauss(0, 5),
                status="healthy" if cpu < 85 and memory < 85 else "warning",
            )
            devices.append(device)

        return devices

    async def get_device(self, device_name: str) -> Optional[DeviceMetrics]:
        """Get specific device metrics."""
        devices = await self.get_all_devices()

        for device in devices:
            if device.device.lower() == device_name.lower():
                return device

        return None

    async def get_device_history(self, device_name: str, hours: int = 24) -> List[dict]:
        """Get device metrics history."""
        history = []

        for i in range(hours * 60):  # One entry per minute
            history.append({
                "timestamp": datetime.utcnow() - datetime.timedelta(minutes=i),
                "cpu_percent": random.gauss(40, 15),
                "memory_percent": random.gauss(60, 15),
                "disk_percent": random.gauss(50, 10),
            })

        return history
