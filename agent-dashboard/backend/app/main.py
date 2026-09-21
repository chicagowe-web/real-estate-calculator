"""FastAPI backend for Agent Dashboard."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZIPMiddleware
from fastapi.responses import JSONResponse

from .models import (
    DashboardOverview, AgentInfo, DeviceMetrics, Alert, AlertSeverity,
    DeploymentStatus, BackupInfo, GPUMetrics, WebSocketMessage
)
from .services.agent_service import AgentService
from .services.device_service import DeviceService
from .services.alert_service import AlertService
from .services.deployment_service import DeploymentService
from .services.backup_service import BackupService
from .services.gpu_service import GPUService

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Services
agent_service = AgentService()
device_service = DeviceService()
alert_service = AlertService()
deployment_service = DeploymentService()
backup_service = BackupService()
gpu_service = GPUService()

# WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: WebSocketMessage):
        """Broadcast message to all connected clients."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message.dict())
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


# Background task to send metrics
async def metrics_broadcast_task():
    """Periodically broadcast metrics to all connected clients."""
    while True:
        try:
            # Collect current metrics
            overview = await get_dashboard_overview()

            message = WebSocketMessage(
                type="metric_update",
                data=overview.dict()
            )

            await manager.broadcast(message)
            await asyncio.sleep(2)  # Update every 2 seconds
        except Exception as e:
            logger.error(f"Error in metrics broadcast: {e}")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager."""
    # Startup
    task = asyncio.create_task(metrics_broadcast_task())
    logger.info("Dashboard backend started")

    yield

    # Shutdown
    task.cancel()
    logger.info("Dashboard backend stopped")


# Create FastAPI app
app = FastAPI(
    title="Agent Dashboard API",
    description="Real-time monitoring for 12-agent distributed infrastructure",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware
app.add_middleware(GZIPMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "services": {
            "agents": "ready",
            "devices": "ready",
            "alerts": "ready",
            "deployments": "ready",
            "backups": "ready",
            "gpu": "ready"
        }
    }


@app.get("/api/dashboard", response_model=DashboardOverview)
async def get_dashboard_overview() -> DashboardOverview:
    """Get complete dashboard overview."""
    try:
        agents = await agent_service.get_all_agents()
        devices = await device_service.get_all_devices()
        alerts = await alert_service.get_recent_alerts(limit=10)
        deployments = await deployment_service.get_recent_deployments(limit=5)
        backups = await backup_service.get_recent_backups(limit=5)
        gpu = await gpu_service.get_gpu_metrics()

        # Calculate system health (0-100)
        health_score = 100.0
        if alerts:
            critical_count = sum(1 for a in alerts if a.severity == AlertSeverity.CRITICAL)
            health_score -= critical_count * 10

        for device in devices:
            if device.cpu_percent > 90:
                health_score -= 5
            if device.memory_percent > 85:
                health_score -= 5

        health_score = max(0, min(100, health_score))

        return DashboardOverview(
            agents=agents,
            devices=devices,
            recent_alerts=alerts,
            deployments=deployments,
            backups=backups,
            gpu_metrics=gpu,
            system_health=health_score,
        )
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents", response_model=list[AgentInfo])
async def get_agents():
    """Get all agents status."""
    return await agent_service.get_all_agents()


@app.get("/api/agents/{agent_name}")
async def get_agent(agent_name: str):
    """Get specific agent details."""
    agent = await agent_service.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@app.get("/api/devices", response_model=list[DeviceMetrics])
async def get_devices():
    """Get all device metrics."""
    return await device_service.get_all_devices()


@app.get("/api/devices/{device_name}")
async def get_device(device_name: str):
    """Get specific device metrics."""
    device = await device_service.get_device(device_name)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@app.get("/api/alerts", response_model=list[Alert])
async def get_alerts(limit: int = 50, severity: str = None):
    """Get recent alerts."""
    alerts = await alert_service.get_recent_alerts(limit=limit)

    if severity:
        alerts = [a for a in alerts if a.severity.value == severity]

    return alerts


@app.post("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve an alert."""
    result = await alert_service.resolve_alert(alert_id)
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "resolved", "alert_id": alert_id}


@app.get("/api/deployments", response_model=list[DeploymentStatus])
async def get_deployments():
    """Get recent deployments."""
    return await deployment_service.get_recent_deployments(limit=10)


@app.post("/api/deployments/{deployment_id}/rollback")
async def rollback_deployment(deployment_id: str):
    """Rollback a deployment."""
    result = await deployment_service.rollback(deployment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return {"status": "rollback_initiated", "deployment_id": deployment_id}


@app.get("/api/backups", response_model=list[BackupInfo])
async def get_backups():
    """Get recent backups."""
    return await backup_service.get_recent_backups(limit=10)


@app.get("/api/gpu", response_model=GPUMetrics)
async def get_gpu_metrics():
    """Get GPU metrics."""
    gpu = await gpu_service.get_gpu_metrics()
    if not gpu:
        raise HTTPException(status_code=500, detail="Unable to get GPU metrics")
    return gpu


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()

            # Echo back acknowledgment
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
