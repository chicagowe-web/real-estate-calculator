"""Security monitoring and threat detection."""

from __future__ import annotations

import logging
import subprocess
import uuid
from datetime import datetime
from typing import Optional

from .models import SecurityEvent, SecurityEventType, ThreatLevel, SecurityMetrics

logger = logging.getLogger("securityagent.security_monitor")


class SecurityMonitor:
    """Monitor security events across infrastructure."""

    def __init__(self):
        self.events: list[SecurityEvent] = []
        self.blocked_ips: set[str] = set()

    async def scan_failed_logins(self, device: str) -> list[SecurityEvent]:
        """Scan for failed login attempts.

        Args:
            device: Device to scan

        Returns:
            List of SecurityEvent
        """
        events = []

        try:
            cmd = f"ssh {device} 'grep Failed /var/log/auth.log 2>/dev/null | tail -100' 2>/dev/null"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        event = SecurityEvent(
                            event_id=f"login-{uuid.uuid4().hex[:8]}",
                            event_type=SecurityEventType.FAILED_LOGIN,
                            device=device,
                            threat_level=ThreatLevel.WARNING,
                            timestamp=datetime.utcnow(),
                            details=line[:200],
                        )
                        events.append(event)
                        self.events.append(event)

            logger.info(f"Scanned {device}: {len(events)} failed logins")

        except Exception as e:
            logger.error(f"Failed login scan error: {e}")

        return events

    async def check_ssh_keys(self, device: str) -> list[SecurityEvent]:
        """Check SSH key configurations.

        Args:
            device: Device to check

        Returns:
            List of SecurityEvent
        """
        events = []

        try:
            cmd = f"ssh {device} 'find /home -name authorized_keys -exec wc -l {{}} \\; 2>/dev/null' 2>/dev/null"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        key_count = int(line.split()[0])
                        if key_count > 10:
                            event = SecurityEvent(
                                event_id=f"ssh-{uuid.uuid4().hex[:8]}",
                                event_type=SecurityEventType.FILE_ACCESS,
                                device=device,
                                threat_level=ThreatLevel.WARNING,
                                timestamp=datetime.utcnow(),
                                details=f"Excessive SSH keys: {key_count}",
                            )
                            events.append(event)
                            self.events.append(event)

            logger.info(f"Checked SSH keys on {device}: {len(events)} issues")

        except Exception as e:
            logger.error(f"SSH key check error: {e}")

        return events

    async def scan_for_intrusions(self, device: str) -> list[SecurityEvent]:
        """Scan for intrusion attempts.

        Args:
            device: Device to scan

        Returns:
            List of SecurityEvent
        """
        events = []

        try:
            # Check for unusual network connections
            cmd = f"ssh {device} 'ss -tuln | grep ESTABLISHED | wc -l' 2>/dev/null"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                conn_count = int(result.stdout.strip())
                if conn_count > 50:
                    event = SecurityEvent(
                        event_id=f"intrusion-{uuid.uuid4().hex[:8]}",
                        event_type=SecurityEventType.INTRUSION_ATTEMPT,
                        device=device,
                        threat_level=ThreatLevel.CRITICAL if conn_count > 100 else ThreatLevel.WARNING,
                        timestamp=datetime.utcnow(),
                        details=f"Unusual connection count: {conn_count}",
                    )
                    events.append(event)
                    self.events.append(event)

        except Exception as e:
            logger.error(f"Intrusion scan error: {e}")

        return events

    async def block_ip(self, ip_address: str, device: str) -> bool:
        """Block IP address on device.

        Args:
            ip_address: IP to block
            device: Device to block on

        Returns:
            True if successful
        """
        try:
            cmd = f"ssh {device} 'iptables -I INPUT -s {ip_address} -j DROP' 2>/dev/null"
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=10)

            if result.returncode == 0:
                self.blocked_ips.add(ip_address)
                logger.info(f"Blocked IP {ip_address} on {device}")
                return True

        except Exception as e:
            logger.error(f"IP block failed: {e}")

        return False

    def get_metrics(self) -> SecurityMetrics:
        """Get security metrics.

        Returns:
            SecurityMetrics
        """
        now = datetime.utcnow()
        day_ago = datetime.utcfromtimestamp(now.timestamp() - 86400)

        events_24h = [e for e in self.events if e.timestamp >= day_ago]
        critical = [e for e in events_24h if e.threat_level == ThreatLevel.CRITICAL]
        failed_logins = [e for e in events_24h if e.event_type == SecurityEventType.FAILED_LOGIN]
        intrusions = [e for e in events_24h if e.event_type == SecurityEventType.INTRUSION_ATTEMPT]

        metrics = SecurityMetrics(
            total_events_24h=len(events_24h),
            critical_events=len(critical),
            failed_login_attempts=len(failed_logins),
            failed_login_sources=list(set(e.source_ip for e in failed_logins if e.source_ip)),
            intrusion_attempts=len(intrusions),
            last_security_scan=max((e.timestamp for e in events_24h), default=None),
        )

        return metrics
