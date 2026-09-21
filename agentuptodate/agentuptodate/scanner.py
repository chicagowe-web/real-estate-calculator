"""Scan for available updates."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from .inference_client import get_inference_client

logger = logging.getLogger("agentuptodate.scanner")


class UpdateType(Enum):
    """Update severity classification."""
    SECURITY = "security"      # CVE fixes
    MAJOR = "major"            # Breaking changes
    MINOR = "minor"            # New features
    PATCH = "patch"            # Bug fixes
    DEPENDENCY = "dependency"  # Outdated deps


class UpdateRisk(Enum):
    """Risk level for update."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Update:
    """Single available update."""
    package: str
    current_version: str
    available_version: str
    update_type: UpdateType = UpdateType.PATCH
    risk: UpdateRisk = UpdateRisk.LOW
    description: str = ""
    security_advisory: Optional[str] = None


@dataclass
class ScanResult:
    """Results from scanning a device."""
    device: str
    timestamp: datetime
    updates: list[Update]
    errors: list[str]

    @property
    def critical_count(self) -> int:
        return sum(1 for u in self.updates if u.risk == UpdateRisk.CRITICAL)

    @property
    def security_count(self) -> int:
        return sum(1 for u in self.updates if u.update_type == UpdateType.SECURITY)

    @property
    def total_count(self) -> int:
        return len(self.updates)


class Scanner:
    """Detect available updates on devices."""

    def __init__(self, device_name: str, ssh_host: Optional[str] = None):
        self.device_name = device_name
        self.ssh_host = ssh_host or device_name

    def scan(self, update_types: list[str]) -> ScanResult:
        """Scan for available updates.

        Args:
            update_types: List of types to scan (apt, pip, npm, cargo, etc.)

        Returns:
            ScanResult with list of available updates
        """
        result = ScanResult(
            device=self.device_name,
            timestamp=datetime.utcnow(),
            updates=[],
            errors=[],
        )

        for update_type in update_types:
            try:
                match update_type.lower():
                    case "apt":
                        updates = self._scan_apt()
                    case "pip":
                        updates = self._scan_pip()
                    case "npm":
                        updates = self._scan_npm()
                    case "cargo":
                        updates = self._scan_cargo()
                    case _:
                        result.errors.append(f"Unknown update type: {update_type}")
                        continue

                result.updates.extend(updates)
            except Exception as e:
                result.errors.append(f"Error scanning {update_type}: {e}")

        logger.info(
            f"Scanned {self.device_name}: "
            f"{result.total_count} updates, {len(result.errors)} errors"
        )
        return result

    def _scan_apt(self) -> list[Update]:
        """Scan for apt upgradable packages."""
        try:
            # apt list --upgradable
            cmd = f"ssh {self.ssh_host} 'apt list --upgradable 2>/dev/null'"
            output = subprocess.check_output(cmd, shell=True, text=True)

            updates = []
            for line in output.strip().split("\n")[1:]:  # Skip header
                if not line.strip():
                    continue

                parts = line.split("/")
                if len(parts) < 2:
                    continue

                package = parts[0].strip()
                # Extract version info (would need parsing)
                # For now, basic detection
                updates.append(Update(
                    package=package,
                    current_version="",
                    available_version="",
                    update_type=UpdateType.PATCH,
                ))

            return updates
        except Exception as e:
            logger.error(f"apt scan failed: {e}")
            return []

    def _scan_pip(self) -> list[Update]:
        """Scan for outdated pip packages."""
        try:
            cmd = f"ssh {self.ssh_host} 'pip list --outdated --format=json 2>/dev/null'"
            import json
            output = subprocess.check_output(cmd, shell=True, text=True)
            data = json.loads(output)

            updates = []
            for pkg in data:
                updates.append(Update(
                    package=pkg["name"],
                    current_version=pkg["version"],
                    available_version=pkg["latest_version"],
                    update_type=UpdateType.PATCH,
                ))

            return updates
        except Exception as e:
            logger.error(f"pip scan failed: {e}")
            return []

    def _scan_npm(self) -> list[Update]:
        """Scan for outdated npm packages."""
        try:
            cmd = f"ssh {self.ssh_host} 'npm outdated --json 2>/dev/null'"
            import json
            output = subprocess.check_output(cmd, shell=True, text=True)
            data = json.loads(output)

            updates = []
            for package, info in data.items():
                updates.append(Update(
                    package=package,
                    current_version=info.get("current", ""),
                    available_version=info.get("latest", ""),
                    update_type=UpdateType.PATCH,
                ))

            return updates
        except Exception as e:
            logger.error(f"npm scan failed: {e}")
            return []

    def _scan_cargo(self) -> list[Update]:
        """Scan for outdated cargo packages."""
        try:
            cmd = f"ssh {self.ssh_host} 'cargo outdated --json 2>/dev/null'"
            import json
            output = subprocess.check_output(cmd, shell=True, text=True)
            data = json.loads(output)

            updates = []
            for pkg in data.get("dependencies", []):
                updates.append(Update(
                    package=pkg["name"],
                    current_version=pkg.get("installed", ""),
                    available_version=pkg.get("latest", ""),
                    update_type=UpdateType.PATCH,
                ))

            return updates
        except Exception as e:
            logger.error(f"cargo scan failed: {e}")
            return []

    async def assess_risk(self, update: Update) -> Update:
        """Assess update risk using local GPU.

        Args:
            update: Update to assess

        Returns:
            Update with risk level set
        """
        try:
            description = f"""
Package: {update.package}
Current version: {update.current_version}
New version: {update.available_version}
Type: {update.update_type.value}
"""
            inference = await get_inference_client()
            assessment = await inference.assess_update_risk(description)

            # Parse assessment to determine risk
            if "critical" in assessment.lower():
                update.risk = UpdateRisk.CRITICAL
            elif "high" in assessment.lower():
                update.risk = UpdateRisk.HIGH
            elif "medium" in assessment.lower():
                update.risk = UpdateRisk.MEDIUM
            else:
                update.risk = UpdateRisk.LOW

            update.description = assessment
            return update

        except Exception as e:
            logger.warning(f"Risk assessment failed for {update.package}: {e}")
            return update
