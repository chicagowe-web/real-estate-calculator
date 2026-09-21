"""Orchestrate code deployments across devices."""

from __future__ import annotations

import logging
import subprocess
import uuid
from datetime import datetime
from typing import Optional

from .models import Deployment, DeploymentStatus, HealthCheck, Rollback

logger = logging.getLogger("deployagent.deployment_orchestrator")


class DeploymentOrchestrator:
    """Orchestrate deployments across distributed devices."""

    def __init__(self):
        self.deployments: dict[str, Deployment] = {}
        self.health_checks: dict[str, list[HealthCheck]] = {}
        self.rollbacks: dict[str, Rollback] = {}

    async def deploy(
        self,
        repo: str,
        branch: str,
        commit: str,
        target_devices: list[str],
    ) -> Deployment:
        """Deploy code to devices.

        Args:
            repo: Git repository
            branch: Branch to deploy
            commit: Commit hash
            target_devices: Devices to deploy to

        Returns:
            Deployment
        """
        deployment_id = f"deploy-{uuid.uuid4().hex[:8]}"

        deployment = Deployment(
            deployment_id=deployment_id,
            repo=repo,
            branch=branch,
            commit=commit,
            target_devices=target_devices,
            status=DeploymentStatus.IN_PROGRESS,
            start_time=datetime.utcnow(),
        )

        self.deployments[deployment_id] = deployment

        try:
            # Deploy to each device in parallel
            for device in target_devices:
                try:
                    cmd = (
                        f"ssh {device} 'cd /home/tp && git fetch && git checkout {commit} && "
                        f"pip install -e . 2>&1' 2>/dev/null"
                    )
                    result = subprocess.run(cmd, shell=True, capture_output=True, timeout=600)

                    if result.returncode == 0:
                        deployment.deployed_devices.append(device)
                        logger.info(f"Deployed to {device}")
                    else:
                        deployment.failed_devices.append(device)
                        logger.error(f"Deployment to {device} failed")

                except Exception as e:
                    deployment.failed_devices.append(device)
                    logger.error(f"Deployment error: {e}")

            if deployment.failed_devices:
                deployment.status = DeploymentStatus.FAILED if len(deployment.deployed_devices) == 0 else DeploymentStatus.IN_PROGRESS
            else:
                deployment.status = DeploymentStatus.SUCCESS

            logger.info(
                f"Deployment {deployment_id}: "
                f"{len(deployment.deployed_devices)} successful, "
                f"{len(deployment.failed_devices)} failed"
            )

        except Exception as e:
            deployment.status = DeploymentStatus.FAILED
            deployment.error = str(e)
            logger.error(f"Deployment failed: {e}")

        finally:
            deployment.end_time = datetime.utcnow()

        return deployment

    async def health_check(self, deployment_id: str) -> list[HealthCheck]:
        """Check health after deployment.

        Args:
            deployment_id: Deployment ID

        Returns:
            List of HealthCheck
        """
        if deployment_id not in self.deployments:
            return []

        deployment = self.deployments[deployment_id]
        checks = []

        try:
            for device in deployment.deployed_devices:
                # Run health checks
                cmd = f"ssh {device} 'systemctl status hermes 2>/dev/null' 2>/dev/null"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

                check = HealthCheck(
                    deployment_id=deployment_id,
                    device=device,
                    checks_passed=1 if result.returncode == 0 else 0,
                    checks_total=1,
                    healthy=result.returncode == 0,
                )

                if result.returncode == 0:
                    check.endpoints_responding.append("hermes")
                else:
                    check.endpoints_down.append("hermes")

                checks.append(check)
                self.health_checks[deployment_id] = checks

                logger.info(f"Health check for {device}: {'healthy' if check.healthy else 'unhealthy'}")

        except Exception as e:
            logger.error(f"Health check failed: {e}")

        return checks

    async def rollback(self, deployment_id: str, previous_commit: str) -> Rollback:
        """Rollback deployment.

        Args:
            deployment_id: Deployment to rollback
            previous_commit: Previous commit to revert to

        Returns:
            Rollback
        """
        if deployment_id not in self.deployments:
            return None

        deployment = self.deployments[deployment_id]
        rollback_id = f"rollback-{uuid.uuid4().hex[:8]}"

        rollback = Rollback(
            rollback_id=rollback_id,
            deployment_id=deployment_id,
            target_devices=deployment.deployed_devices,
            previous_commit=previous_commit,
            status=DeploymentStatus.IN_PROGRESS,
            start_time=datetime.utcnow(),
        )

        self.rollbacks[rollback_id] = rollback

        try:
            for device in deployment.deployed_devices:
                cmd = (
                    f"ssh {device} 'cd /home/tp && git checkout {previous_commit} && "
                    f"pip install -e . 2>&1' 2>/dev/null"
                )
                result = subprocess.run(cmd, shell=True, capture_output=True, timeout=600)

                if result.returncode != 0:
                    logger.error(f"Rollback on {device} failed")

            rollback.status = DeploymentStatus.SUCCESS
            logger.info(f"Rollback {rollback_id} completed")

        except Exception as e:
            rollback.status = DeploymentStatus.FAILED
            logger.error(f"Rollback failed: {e}")

        finally:
            rollback.end_time = datetime.utcnow()

        return rollback

    def get_deployment_history(self, limit: int = 20) -> list[Deployment]:
        """Get deployment history.

        Args:
            limit: Maximum results

        Returns:
            List of Deployment
        """
        history = sorted(
            self.deployments.values(),
            key=lambda d: d.start_time or datetime.utcnow(),
            reverse=True,
        )
        return history[:limit]
