"""Service for deployment tracking."""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from ..models import DeploymentStatus


class DeploymentService:
    """Manage deployments."""

    def __init__(self):
        self.deployments: dict[str, DeploymentStatus] = {}
        self._generate_sample_deployments()

    def _generate_sample_deployments(self):
        """Generate sample deployments for demo."""
        for i in range(3):
            deployment_id = str(uuid.uuid4())[:8]
            deployment = DeploymentStatus(
                deployment_id=deployment_id,
                repo="agent-ecosystem",
                branch=random.choice(["main", "develop", "feature/gpu-optimization"]),
                commit=str(uuid.uuid4())[:8],
                status=random.choice(["success", "deploying", "failed"]),
                start_time=datetime.utcnow() - timedelta(hours=i),
                end_time=datetime.utcnow() if random.random() < 0.7 else None,
                deployed_count=random.randint(3, 5),
                total_devices=5,
                rollback_available=True,
            )
            self.deployments[deployment_id] = deployment

    async def get_recent_deployments(self, limit: int = 10) -> List[DeploymentStatus]:
        """Get recent deployments."""
        deployments = list(self.deployments.values())
        deployments.sort(key=lambda d: d.start_time, reverse=True)
        return deployments[:limit]

    async def get_deployment(self, deployment_id: str) -> Optional[DeploymentStatus]:
        """Get specific deployment."""
        return self.deployments.get(deployment_id)

    async def rollback(self, deployment_id: str) -> bool:
        """Rollback a deployment."""
        if deployment_id in self.deployments:
            deployment = self.deployments[deployment_id]
            deployment.status = "rolling_back"
            return True
        return False

    async def create_deployment(self, repo: str, branch: str, commit: str) -> DeploymentStatus:
        """Create new deployment."""
        deployment_id = str(uuid.uuid4())[:8]
        deployment = DeploymentStatus(
            deployment_id=deployment_id,
            repo=repo,
            branch=branch,
            commit=commit,
            status="pending",
            start_time=datetime.utcnow(),
            total_devices=5,
            rollback_available=True,
        )
        self.deployments[deployment_id] = deployment
        return deployment
