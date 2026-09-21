"""Service for alert management."""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from ..models import Alert, AlertSeverity


class AlertService:
    """Manage system alerts."""

    def __init__(self):
        self.alerts: dict[str, Alert] = {}
        self._generate_sample_alerts()

    def _generate_sample_alerts(self):
        """Generate sample alerts for demo."""
        devices = ["garage-core", "tp", "kali", "canfd", "canfd2"]

        sample_titles = [
            "High CPU usage detected",
            "Memory pressure on device",
            "Disk space running low",
            "Network latency spike",
            "Failed login attempt",
            "Security threat detected",
            "Deployment in progress",
            "Backup failed",
            "GPU temperature high",
        ]

        for i, title in enumerate(sample_titles[:5]):
            alert_id = str(uuid.uuid4())[:8]
            alert = Alert(
                alert_id=alert_id,
                title=title,
                description=f"Alert: {title} on {random.choice(devices)}",
                severity=random.choice(list(AlertSeverity)),
                device=random.choice(devices),
                timestamp=datetime.utcnow() - timedelta(minutes=random.randint(1, 60)),
                resolved=random.random() < 0.3,
                suggested_action="Monitor the system and take appropriate action",
            )
            self.alerts[alert_id] = alert

    async def get_recent_alerts(self, limit: int = 50) -> List[Alert]:
        """Get recent alerts."""
        alerts = list(self.alerts.values())
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        return alerts[:limit]

    async def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get alerts by severity."""
        return [a for a in self.alerts.values() if a.severity == severity]

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
            return True
        return False

    async def create_alert(self, title: str, description: str, severity: AlertSeverity, device: str) -> Alert:
        """Create new alert."""
        alert_id = str(uuid.uuid4())[:8]
        alert = Alert(
            alert_id=alert_id,
            title=title,
            description=description,
            severity=severity,
            device=device,
            timestamp=datetime.utcnow(),
        )
        self.alerts[alert_id] = alert
        return alert
