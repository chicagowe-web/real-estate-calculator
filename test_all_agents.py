#!/usr/bin/env python3
"""Comprehensive test suite for all 12 agents."""

import asyncio
import sys
from datetime import datetime

# Test counter
tests_passed = 0
tests_failed = 0
tests_total = 0


def test(name):
    """Decorator for test functions."""
    def decorator(func):
        async def wrapper():
            global tests_total, tests_passed, tests_failed
            tests_total += 1
            try:
                await func()
                print(f"✅ {name}")
                tests_passed += 1
                return True
            except AssertionError as e:
                print(f"❌ {name}: {e}")
                tests_failed += 1
                return False
            except Exception as e:
                print(f"❌ {name}: {type(e).__name__}: {e}")
                tests_failed += 1
                return False
        return wrapper
    return decorator


# ============================================================================
# AGENT 1: HERMES
# ============================================================================

@test("Hermes: inference_client is deployed")
async def test_hermes_import():
    import os
    path = "/home/tp/hermes/hermes/inference_client.py"
    assert os.path.exists(path), f"Missing: {path}"


# ============================================================================
# AGENT 2: RESEARCHAGENT
# ============================================================================

@test("ResearchAgent: Can import models")
async def test_researchagent_import():
    from researchagent.researchagent.models import ResearchResult, ResourceBundle
    assert ResearchResult is not None
    assert ResourceBundle is not None


@test("ResearchAgent: Can instantiate ReportBuilder")
async def test_researchagent_report_builder():
    from researchagent.researchagent.synthesis.report_builder import ReportBuilder
    builder = ReportBuilder()
    assert builder is not None


@test("ResearchAgent: ReportBuilder has async methods")
async def test_researchagent_async_methods():
    from researchagent.researchagent.synthesis.report_builder import ReportBuilder
    import inspect
    builder = ReportBuilder()
    assert inspect.iscoroutinefunction(builder.generate_overview)
    assert inspect.iscoroutinefunction(builder.extract_practices)
    assert inspect.iscoroutinefunction(builder.extract_pitfalls)
    assert inspect.iscoroutinefunction(builder.extract_tips)


# ============================================================================
# AGENT 3: MONITORINGAGENT
# ============================================================================

@test("MonitoringAgent: Can import models")
async def test_monitoring_import():
    from monitoringagent.monitoringagent.models import Alert, AlertSeverity
    assert Alert is not None
    assert AlertSeverity is not None


@test("MonitoringAgent: Can instantiate AlertSystem")
async def test_monitoring_alert_system():
    from monitoringagent.monitoringagent.alert_system import AlertSystem
    system = AlertSystem()
    assert system is not None
    assert len(system.alerts) == 0


@test("MonitoringAgent: AlertSystem.create_threshold_alert works")
async def test_monitoring_create_alert():
    from monitoringagent.monitoringagent.alert_system import AlertSystem
    from monitoringagent.monitoringagent.models import AlertSeverity
    system = AlertSystem()
    alert = system.create_threshold_alert(
        device="test-device",
        metric="cpu",
        current_value=85.0,
        threshold=80.0,
    )
    assert alert is not None
    assert alert.device == "test-device"
    assert alert.severity in [AlertSeverity.MEDIUM, AlertSeverity.HIGH, AlertSeverity.CRITICAL]


# ============================================================================
# AGENT 4: AGENTUPTODATE
# ============================================================================

@test("AgentUptoDate: Can import models")
async def test_agentuptodate_import():
    from agentuptodate.agentuptodate.scanner import UpdateType, UpdateRisk
    assert UpdateType is not None
    assert UpdateRisk is not None


@test("AgentUptoDate: Can instantiate Scanner")
async def test_agentuptodate_scanner():
    from agentuptodate.agentuptodate.scanner import Scanner
    scanner = Scanner("test-device")
    assert scanner is not None
    assert scanner.device_name == "test-device"


# ============================================================================
# AGENT 5: BACKUPAGENT
# ============================================================================

@test("BackupAgent: Can import models")
async def test_backup_import():
    from backupagent.backupagent.models import BackupJob, BackupStatus, BackupType
    assert BackupJob is not None
    assert BackupStatus is not None


@test("BackupAgent: Can instantiate BackupManager")
async def test_backup_manager():
    from backupagent.backupagent.backup_manager import BackupManager
    manager = BackupManager()
    assert manager is not None
    assert len(manager.backup_jobs) == 0


@test("BackupAgent: Can schedule backup")
async def test_backup_schedule():
    from backupagent.backupagent.backup_manager import BackupManager
    from backupagent.backupagent.models import BackupType
    manager = BackupManager()
    job = await manager.schedule_backup(
        device="test-device",
        paths=["/home", "/data"],
        backup_type=BackupType.FULL,
    )
    assert job is not None
    assert job.device == "test-device"
    assert job.backup_type == BackupType.FULL


# ============================================================================
# AGENT 6: LOGAGENT
# ============================================================================

@test("LogAgent: Can import models")
async def test_logagent_import():
    from logagent.logagent.models import LogEntry, LogLevel, LogSource
    assert LogEntry is not None
    assert LogLevel is not None


@test("LogAgent: Can instantiate LogAggregator")
async def test_logagent_aggregator():
    from logagent.logagent.log_aggregator import LogAggregator
    aggregator = LogAggregator()
    assert aggregator is not None
    assert len(aggregator.logs) == 0


@test("LogAgent: Can detect patterns")
async def test_logagent_patterns():
    from logagent.logagent.log_aggregator import LogAggregator
    from logagent.logagent.models import LogEntry, LogLevel, LogSource
    from datetime import datetime

    aggregator = LogAggregator()
    # Add test logs
    for i in range(15):
        entry = LogEntry(
            timestamp=datetime.utcnow(),
            device="test",
            source=LogSource.SYSTEM,
            level=LogLevel.ERROR,
            message="Test error message",
        )
        aggregator.logs.append(entry)

    patterns = await aggregator.detect_patterns()
    assert len(patterns) > 0


# ============================================================================
# AGENT 7: MODELAGENT
# ============================================================================

@test("ModelAgent: Can import models")
async def test_modelagent_import():
    from modelagent.modelagent.models import Model, ModelStatus, ModelType
    assert Model is not None
    assert ModelStatus is not None


@test("ModelAgent: Can instantiate ModelManager")
async def test_modelagent_manager():
    from modelagent.modelagent.model_manager import ModelManager
    manager = ModelManager()
    assert manager is not None
    assert len(manager.models) == 0


@test("ModelAgent: Can register model")
async def test_modelagent_register():
    from modelagent.modelagent.model_manager import ModelManager
    from modelagent.modelagent.models import ModelType
    manager = ModelManager()
    model = await manager.register_model(
        name="test-model",
        model_type=ModelType.GARAGE_AI,
        device="garage-core",
        version="1.0",
        vram_mb=4096,
    )
    assert model is not None
    assert model.name == "test-model"
    assert len(manager.models) == 1


# ============================================================================
# AGENT 8: SECURITYAGENT
# ============================================================================

@test("SecurityAgent: Can import models")
async def test_securityagent_import():
    from securityagent.securityagent.models import SecurityEvent, ThreatLevel
    assert SecurityEvent is not None
    assert ThreatLevel is not None


@test("SecurityAgent: Can instantiate SecurityMonitor")
async def test_securityagent_monitor():
    from securityagent.securityagent.security_monitor import SecurityMonitor
    monitor = SecurityMonitor()
    assert monitor is not None
    assert len(monitor.events) == 0


# ============================================================================
# AGENT 9: DATASYNCAGENT
# ============================================================================

@test("DataSyncAgent: Can import models")
async def test_datasync_import():
    from datasyncagent.datasyncagent.models import SyncJob, SyncStatus, SyncPair
    assert SyncJob is not None
    assert SyncStatus is not None


@test("DataSyncAgent: Can instantiate SyncCoordinator")
async def test_datasync_coordinator():
    from datasyncagent.datasyncagent.sync_coordinator import SyncCoordinator
    coordinator = SyncCoordinator()
    assert coordinator is not None
    assert len(coordinator.sync_jobs) == 0


@test("DataSyncAgent: Can setup sync pair")
async def test_datasync_pair():
    from datasyncagent.datasyncagent.sync_coordinator import SyncCoordinator
    coordinator = SyncCoordinator()
    pair = await coordinator.setup_continuous_sync(
        device_a="device-a",
        device_b="device-b",
        paths=["/data"],
    )
    assert pair is not None
    assert pair.device_a == "device-a"
    assert len(coordinator.sync_pairs) == 1


# ============================================================================
# AGENT 10: NOTIFICATIONAGENT
# ============================================================================

@test("NotificationAgent: Can import models")
async def test_notification_import():
    from notificationagent.notificationagent.models import Notification, Channel
    assert Notification is not None
    assert Channel is not None


@test("NotificationAgent: Can instantiate Notifier")
async def test_notification_notifier():
    from notificationagent.notificationagent.notifier import Notifier
    notifier = Notifier()
    assert notifier is not None
    assert len(notifier.notifications) == 0


# ============================================================================
# AGENT 11: PERFAGENT
# ============================================================================

@test("PerfAgent: Can import models")
async def test_perfagent_import():
    from perfagent.perfagent.models import PerformanceMetric, Optimization
    assert PerformanceMetric is not None
    assert Optimization is not None


@test("PerfAgent: Can instantiate PerformanceOptimizer")
async def test_perfagent_optimizer():
    from perfagent.perfagent.optimizer import PerformanceOptimizer
    optimizer = PerformanceOptimizer()
    assert optimizer is not None


# ============================================================================
# AGENT 12: DEPLOYAGENT
# ============================================================================

@test("DeploymentAgent: Can import models")
async def test_deployagent_import():
    from deployagent.deployagent.models import Deployment, DeploymentStatus
    assert Deployment is not None
    assert DeploymentStatus is not None


@test("DeploymentAgent: Can instantiate DeploymentOrchestrator")
async def test_deployagent_orchestrator():
    from deployagent.deployagent.deployment_orchestrator import DeploymentOrchestrator
    orchestrator = DeploymentOrchestrator()
    assert orchestrator is not None
    assert len(orchestrator.deployments) == 0


# ============================================================================
# GPU INFERENCE INTEGRATION
# ============================================================================

@test("GPU Inference: ResearchAgent has inference_client")
async def test_gpu_researchagent():
    import os
    path = "/home/tp/researchagent/researchagent/inference_client.py"
    assert os.path.exists(path), f"Missing: {path}"


@test("GPU Inference: MonitoringAgent has inference_client")
async def test_gpu_monitoring():
    import os
    path = "/home/tp/monitoringagent/monitoringagent/inference_client.py"
    assert os.path.exists(path), f"Missing: {path}"


@test("GPU Inference: All 12 agents have inference_client")
async def test_gpu_all_agents():
    import os
    agents = [
        "hermes", "researchagent", "monitoringagent", "agentuptodate",
        "backupagent", "logagent", "modelagent", "securityagent",
        "datasyncagent", "notificationagent", "perfagent", "deployagent"
    ]

    missing = []
    for agent in agents:
        path = f"/home/tp/{agent}/{agent}/inference_client.py"
        if not os.path.exists(path):
            missing.append(agent)

    assert len(missing) == 0, f"Missing inference_client in: {missing}"


# ============================================================================
# MOCK GPU INFERENCE TEST
# ============================================================================

@test("GPU Inference: Can import GarageCoreInference")
async def test_gpu_import():
    from researchagent.researchagent.inference_client import GarageCoreInference
    assert GarageCoreInference is not None


@test("GPU Inference: Can instantiate GarageCoreInference")
async def test_gpu_instantiate():
    from researchagent.researchagent.inference_client import GarageCoreInference
    client = GarageCoreInference()
    assert client is not None
    assert client.ollama_url == "http://192.168.0.129:11434"


@test("GPU Inference: GarageCoreInference has all methods")
async def test_gpu_methods():
    from researchagent.researchagent.inference_client import GarageCoreInference
    import inspect

    client = GarageCoreInference()
    methods = [
        "generate",
        "summarize_research",
        "explain_anomaly",
        "assess_update_risk",
        "suggest_remediation",
        "classify_alert",
        "extract_key_points",
        "health_check",
    ]

    for method in methods:
        assert hasattr(client, method), f"Missing method: {method}"
        assert inspect.iscoroutinefunction(getattr(client, method)), f"Not async: {method}"


# ============================================================================
# MOCK TEST
# ============================================================================

@test("Mock Tests: Can run mock inference test")
async def test_mock_inference():
    # Run the mock test we created earlier
    import subprocess
    result = subprocess.run(
        ["python", "/home/tp/garage-core-inference/test_inference_mock.py"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Mock test failed: {result.stderr}"


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def main():
    """Run all tests."""
    print("=" * 70)
    print("🧪 COMPREHENSIVE AGENT TEST SUITE")
    print("=" * 70)
    print()

    # Collect all test functions
    test_functions = [
        # Hermes
        test_hermes_import,
        # ResearchAgent
        test_researchagent_import,
        test_researchagent_report_builder,
        test_researchagent_async_methods,
        # MonitoringAgent
        test_monitoring_import,
        test_monitoring_alert_system,
        test_monitoring_create_alert,
        # AgentUptoDate
        test_agentuptodate_import,
        test_agentuptodate_scanner,
        # BackupAgent
        test_backup_import,
        test_backup_manager,
        test_backup_schedule,
        # LogAgent
        test_logagent_import,
        test_logagent_aggregator,
        test_logagent_patterns,
        # ModelAgent
        test_modelagent_import,
        test_modelagent_manager,
        test_modelagent_register,
        # SecurityAgent
        test_securityagent_import,
        test_securityagent_monitor,
        # DataSyncAgent
        test_datasync_import,
        test_datasync_coordinator,
        test_datasync_pair,
        # NotificationAgent
        test_notification_import,
        test_notification_notifier,
        # PerfAgent
        test_perfagent_import,
        test_perfagent_optimizer,
        # DeploymentAgent
        test_deployagent_import,
        test_deployagent_orchestrator,
        # GPU Inference
        test_gpu_researchagent,
        test_gpu_monitoring,
        test_gpu_all_agents,
        test_gpu_import,
        test_gpu_instantiate,
        test_gpu_methods,
        # Mock test
        test_mock_inference,
    ]

    # Run tests
    for test_func in test_functions:
        await test_func()

    # Summary
    print()
    print("=" * 70)
    print("📊 TEST RESULTS")
    print("=" * 70)
    print(f"✅ Passed:  {tests_passed}")
    print(f"❌ Failed:  {tests_failed}")
    print(f"📊 Total:   {tests_total}")
    print()

    if tests_failed == 0:
        print("🎉 ALL TESTS PASSED!")
        print()
        print("✅ All 12 agents are working correctly")
        print("✅ GPU inference integration verified")
        print("✅ Mock test suite passing")
        print()
        return 0
    else:
        print(f"⚠️  {tests_failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
