"""Service for agent status and monitoring."""

import random
from datetime import datetime, timedelta
from typing import List

from ..models import AgentInfo, AgentStatus


class AgentService:
    """Manage agent status and metrics."""

    AGENTS = [
        "Hermes",
        "ResearchAgent",
        "MonitoringAgent",
        "AgentUptoDate",
        "BackupAgent",
        "LogAggregationAgent",
        "ModelManagementAgent",
        "SecurityAgent",
        "DataSyncAgent",
        "NotificationAgent",
        "PerformanceOptimizationAgent",
        "DeploymentAgent",
    ]

    async def get_all_agents(self) -> List[AgentInfo]:
        """Get all agents status."""
        agents = []

        for agent_name in self.AGENTS:
            # Simulate agent data (in production, this would query actual agents)
            status_options = [AgentStatus.ONLINE, AgentStatus.PROCESSING, AgentStatus.IDLE]
            status = random.choices(
                status_options,
                weights=[60, 25, 15],  # Most are online
                k=1
            )[0]

            # If processing, some chance of error
            if status == AgentStatus.PROCESSING and random.random() < 0.05:
                status = AgentStatus.ERROR

            agent = AgentInfo(
                name=agent_name,
                status=status,
                last_activity=datetime.utcnow() - timedelta(seconds=random.randint(1, 300)),
                task_count=random.randint(0, 50),
                success_rate=random.uniform(95.0, 99.9),
                avg_response_time_ms=random.uniform(10, 500),
                error_count=random.randint(0, 5),
            )
            agents.append(agent)

        return agents

    async def get_agent(self, agent_name: str) -> AgentInfo:
        """Get specific agent details."""
        agents = await self.get_all_agents()

        for agent in agents:
            if agent.name.lower() == agent_name.lower():
                return agent

        return None

    async def get_agent_logs(self, agent_name: str, limit: int = 100) -> List[dict]:
        """Get agent logs (mock data)."""
        return [
            {
                "timestamp": datetime.utcnow() - timedelta(seconds=i),
                "level": random.choice(["INFO", "WARNING", "ERROR"]),
                "message": f"Agent log message {i}",
            }
            for i in range(limit)
        ]

    async def get_agent_metrics(self, agent_name: str) -> dict:
        """Get agent performance metrics."""
        return {
            "agent_name": agent_name,
            "total_tasks": random.randint(100, 1000),
            "completed_tasks": random.randint(80, 950),
            "failed_tasks": random.randint(0, 20),
            "avg_task_duration_seconds": random.uniform(0.5, 30),
            "last_task": datetime.utcnow() - timedelta(seconds=random.randint(1, 300)),
        }
