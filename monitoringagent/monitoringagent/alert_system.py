"""Alert generation and management."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from .models import Alert, AlertSeverity, AlertType
from .inference_client import get_inference_client

logger = logging.getLogger("monitoringagent.alert_system")


class AlertSystem:
    """Generate and manage alerts."""

    def __init__(self):
        self.alerts: dict[str, Alert] = {}  # alert_id -> Alert
        self.alert_history: list[Alert] = []

    def create_threshold_alert(
        self,
        device: str,
        metric: str,
        current_value: float,
        threshold: float,
    ) -> Alert:
        """Create threshold-based alert.

        Args:
            device: Device name
            metric: Metric name
            current_value: Current value
            threshold: Threshold value

        Returns:
            Alert object
        """
        # Determine severity
        if current_value > threshold * 1.2:
            severity = AlertSeverity.CRITICAL
        elif current_value > threshold * 1.1:
            severity = AlertSeverity.HIGH
        else:
            severity = AlertSeverity.MEDIUM

        title = f"{metric.upper()} threshold exceeded on {device}"
        description = f"{metric} at {current_value:.1f}% (threshold: {threshold:.1f}%)"

        return self._create_alert(
            device=device,
            severity=severity,
            alert_type=AlertType.THRESHOLD,
            title=title,
            description=description,
            metric_name=metric,
            current_value=current_value,
            threshold=threshold,
        )

    async def create_anomaly_alert(
        self,
        device: str,
        metric: str,
        current_value: float,
        expected_value: float,
        z_score: float,
    ) -> Alert:
        """Create anomaly-based alert with intelligent explanation.

        Args:
            device: Device name
            metric: Metric name
            current_value: Current value
            expected_value: Expected value
            z_score: Standard deviations away from mean

        Returns:
            Alert object
        """
        # Severity based on z-score
        if abs(z_score) > 4:
            severity = AlertSeverity.CRITICAL
        elif abs(z_score) > 3:
            severity = AlertSeverity.HIGH
        else:
            severity = AlertSeverity.MEDIUM

        title = f"Anomalous {metric} on {device}"

        # Use local GPU to generate intelligent explanation
        try:
            inference = await get_inference_client()
            stddev = abs(current_value - expected_value) / abs(z_score) if z_score != 0 else 1
            description = await inference.explain_anomaly(
                device=device,
                metric=metric,
                current_value=current_value,
                expected_value=expected_value,
                stddev=stddev,
            )
        except Exception as e:
            logger.warning(f"Inference failed, using template: {e}")
            description = (
                f"{metric} at {current_value:.1f} is {abs(z_score):.1f} std devs "
                f"from expected {expected_value:.1f}"
            )

        return self._create_alert(
            device=device,
            severity=severity,
            alert_type=AlertType.ANOMALY,
            title=title,
            description=description,
            metric_name=metric,
            current_value=current_value,
        )

    def create_trend_alert(
        self,
        device: str,
        metric: str,
        current_value: float,
        trend_direction: str,
        days_to_critical: Optional[float] = None,
    ) -> Alert:
        """Create trend-based alert.

        Args:
            device: Device name
            metric: Metric name
            current_value: Current value
            trend_direction: "increasing", "decreasing", or "stable"
            days_to_critical: Days until critical threshold reached

        Returns:
            Alert object
        """
        severity = AlertSeverity.LOW

        if days_to_critical:
            if days_to_critical < 3:
                severity = AlertSeverity.HIGH
            elif days_to_critical < 7:
                severity = AlertSeverity.MEDIUM

        title = f"{metric} {trend_direction} on {device}"

        if days_to_critical:
            description = (
                f"{metric} trending {trend_direction}. "
                f"Will reach critical in ~{days_to_critical:.1f} days."
            )
        else:
            description = f"{metric} trending {trend_direction}"

        return self._create_alert(
            device=device,
            severity=severity,
            alert_type=AlertType.TREND,
            title=title,
            description=description,
            metric_name=metric,
            current_value=current_value,
        )

    def create_service_alert(
        self,
        device: str,
        service: str,
        down: bool = True,
    ) -> Alert:
        """Create service health alert.

        Args:
            device: Device name
            service: Service name
            down: True if service is down

        Returns:
            Alert object
        """
        severity = AlertSeverity.CRITICAL if down else AlertSeverity.HIGH
        status = "down" if down else "degraded"

        title = f"Service {status}: {service} on {device}"
        description = f"{service} is {status} on {device}"

        return self._create_alert(
            device=device,
            severity=severity,
            alert_type=AlertType.THRESHOLD,  # Close enough
            title=title,
            description=description,
            metric_name=f"service:{service}",
        )

    def _create_alert(
        self,
        device: str,
        severity: AlertSeverity,
        alert_type: AlertType,
        title: str,
        description: str,
        metric_name: Optional[str] = None,
        current_value: Optional[float] = None,
        threshold: Optional[float] = None,
    ) -> Alert:
        """Internal alert creation.

        Args:
            device: Device name
            severity: Severity level
            alert_type: Alert type
            title: Alert title
            description: Detailed description
            metric_name: Metric name (optional)
            current_value: Current value (optional)
            threshold: Threshold value (optional)

        Returns:
            Alert object
        """
        alert_id = str(uuid.uuid4())[:8]

        alert = Alert(
            alert_id=alert_id,
            device=device,
            severity=severity,
            alert_type=alert_type,
            title=title,
            description=description,
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold,
            timestamp=datetime.utcnow(),
        )

        self.alerts[alert_id] = alert
        self.alert_history.append(alert)

        logger.warning(f"Alert: {severity.value.upper()} - {title}")

        return alert

    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Mark alert as acknowledged.

        Args:
            alert_id: Alert ID
            user: User acknowledging

        Returns:
            True if successful
        """
        if alert_id not in self.alerts:
            return False

        alert = self.alerts[alert_id]
        alert.acknowledged = True
        alert.acknowledged_by = user
        alert.acknowledged_at = datetime.utcnow()

        logger.info(f"Alert {alert_id} acknowledged by {user}")
        return True

    def get_recent_alerts(self, limit: int = 20, severity: Optional[AlertSeverity] = None) -> list[Alert]:
        """Get recent alerts.

        Args:
            limit: Maximum alerts to return
            severity: Filter by severity (optional)

        Returns:
            List of alerts
        """
        alerts = self.alert_history

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        # Most recent first
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)[:limit]

    def get_active_alerts(self) -> list[Alert]:
        """Get currently active (unacknowledged) alerts.

        Returns:
            List of active alerts
        """
        return [a for a in self.alerts.values() if not a.acknowledged]

    def resolve_alert(self, alert_id: str) -> bool:
        """Remove alert from active list.

        Args:
            alert_id: Alert ID

        Returns:
            True if successful
        """
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            logger.info(f"Alert {alert_id} resolved")
            return True
        return False


class HermesIntegration:
    """Integration with Hermes for auto-remediation."""

    @staticmethod
    async def suggest_remediation(alert: Alert) -> Optional[str]:
        """Suggest Hermes action for alert using local GPU.

        Args:
            alert: Alert to remediate

        Returns:
            Suggested Hermes command
        """
        try:
            inference = await get_inference_client()
            command = await inference.suggest_remediation(alert.description)
            return command
        except Exception as e:
            logger.warning(f"Inference failed, using template: {e}")
            # Fallback to pattern-based suggestions
            device = alert.device
            metric = alert.metric_name or ""

            if "cpu" in metric.lower() and alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
                return f'hermes ask "show top processes using CPU on {device}"'
            elif "memory" in metric.lower() and alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
                return f'hermes ask "show top memory consumers on {device}"'
            elif "disk" in metric.lower() and alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
                return f'hermes ask "find largest files on {device}"'
            elif "service" in metric.lower():
                service = metric.split(":")[-1]
                return f'hermes ask "restart {service} on {device}"'
            elif "gpu" in metric.lower():
                return f'hermes ask "check GPU status on {device}"'

            return None

    @staticmethod
    async def execute_remediation(command: str) -> bool:
        """Execute Hermes remediation command.

        In production, would call Hermes API.

        Args:
            command: Hermes command to execute

        Returns:
            True if successful
        """
        logger.info(f"Would execute: {command}")
        # In production: call hermes.ask(command)
        return True
