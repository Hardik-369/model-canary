"""Tests for storage backends."""

import tempfile
from pathlib import Path

import pytest

from model_canary.core.models import (
    CanaryRunResult, DriftReport, DriftSeverity, DriftType,
    Fingerprint, PromptResult,
)


@pytest.fixture
def sample_run():
    return CanaryRunResult(
        suite_name="test-suite",
        total_prompts=5,
        successful_prompts=4,
        failed_prompts=1,
        status="completed",
        total_cost=0.005,
        total_latency_ms=2500.0,
    )


@pytest.fixture
def sample_fingerprint():
    return Fingerprint(
        prompt_name="test-prompt",
        model="gpt-4",
        provider="openai",
        sha256_hash="abc123",
        latency_ms=500.0,
        cost_usd=0.001,
        token_count=50,
        response_length=100,
    )


@pytest.fixture
def sample_drift(sample_fingerprint):
    return DriftReport(
        run_id="test-run",
        prompt_name="test-prompt",
        model="gpt-4",
        provider="openai",
        drift_type=DriftType.OUTPUT_DRIFT,
        severity=DriftSeverity.HIGH,
        baseline_fingerprint=sample_fingerprint,
        current_fingerprint=sample_fingerprint,
        drift_score=0.85,
        message="Output drift detected",
    )


class TestLocalJSONStorage:
    @pytest.mark.asyncio
    async def test_initialize(self):
        from model_canary.storage.local_json import LocalJSONStorage
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalJSONStorage(str(Path(tmp) / ".model-canary" / "data"))
            await storage.initialize()
            assert Path(tmp, ".model-canary", "data", "runs").exists()
            assert Path(tmp, ".model-canary", "data", "fingerprints").exists()
            assert Path(tmp, ".model-canary", "data", "drift_reports").exists()
            await storage.close()

    @pytest.mark.asyncio
    async def test_save_and_get_run(self, sample_run):
        from model_canary.storage.local_json import LocalJSONStorage
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalJSONStorage(str(Path(tmp) / "data"))
            await storage.initialize()
            await storage.save_run_result(sample_run)
            retrieved = await storage.get_run_result(sample_run.id)
            assert retrieved is not None
            assert retrieved.suite_name == "test-suite"
            assert retrieved.status == "completed"
            await storage.close()

    @pytest.mark.asyncio
    async def test_save_and_get_fingerprint(self, sample_fingerprint):
        from model_canary.storage.local_json import LocalJSONStorage
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalJSONStorage(str(Path(tmp) / "data"))
            await storage.initialize()
            await storage.save_fingerprint(sample_fingerprint)
            latest = await storage.get_latest_fingerprint("test-prompt", "gpt-4", "openai")
            assert latest is not None
            assert latest.sha256_hash == "abc123"
            await storage.close()

    @pytest.mark.asyncio
    async def test_save_and_get_drift(self, sample_drift):
        from model_canary.storage.local_json import LocalJSONStorage
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalJSONStorage(str(Path(tmp) / "data"))
            await storage.initialize()
            await storage.save_drift_report(sample_drift)
            reports = await storage.get_drift_reports(limit=10)
            assert len(reports) >= 1
            assert reports[0].drift_type == DriftType.OUTPUT_DRIFT
            await storage.close()

    @pytest.mark.asyncio
    async def test_get_nonexistent_run(self):
        from model_canary.storage.local_json import LocalJSONStorage
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalJSONStorage(str(Path(tmp) / "data"))
            await storage.initialize()
            result = await storage.get_run_result("nonexistent")
            assert result is None
            await storage.close()

    @pytest.mark.asyncio
    async def test_fingerprint_history(self, sample_fingerprint):
        from model_canary.storage.local_json import LocalJSONStorage
        from copy import deepcopy
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalJSONStorage(str(Path(tmp) / "data"))
            await storage.initialize()
            for i in range(3):
                fp = Fingerprint(
                    prompt_name="test-prompt",
                    model="gpt-4",
                    provider="openai",
                    sha256_hash=f"hash{i}",
                    latency_ms=float(100 * (i + 1)),
                    cost_usd=0.001,
                    token_count=50,
                )
                await storage.save_fingerprint(fp)
            history = await storage.get_fingerprint_history("test-prompt", "gpt-4", "openai", limit=10)
            assert len(history) == 3
            await storage.close()


class TestSQLiteStorage:
    @pytest.mark.asyncio
    async def test_initialize_and_close(self):
        from model_canary.storage.sqlite import SQLiteStorage
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            storage = SQLiteStorage(f"sqlite+aiosqlite:///{db_path}")
            await storage.initialize()
            await storage.close()

    @pytest.mark.asyncio
    async def test_save_and_get_run(self, sample_run):
        from model_canary.storage.sqlite import SQLiteStorage
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            storage = SQLiteStorage(f"sqlite+aiosqlite:///{db_path}")
            await storage.initialize()
            await storage.save_run_result(sample_run)
            retrieved = await storage.get_run_result(sample_run.id)
            assert retrieved is not None
            assert retrieved.suite_name == "test-suite"
            await storage.close()

    @pytest.mark.asyncio
    async def test_save_and_get_fingerprint(self, sample_fingerprint):
        from model_canary.storage.sqlite import SQLiteStorage
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            storage = SQLiteStorage(f"sqlite+aiosqlite:///{db_path}")
            await storage.initialize()
            await storage.save_fingerprint(sample_fingerprint)
            latest = await storage.get_latest_fingerprint("test-prompt", "gpt-4", "openai")
            assert latest is not None
            assert latest.sha256_hash == "abc123"
            await storage.close()

    @pytest.mark.asyncio
    async def test_save_and_get_drift(self, sample_drift):
        from model_canary.storage.sqlite import SQLiteStorage
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            storage = SQLiteStorage(f"sqlite+aiosqlite:///{db_path}")
            await storage.initialize()
            await storage.save_drift_report(sample_drift)
            reports = await storage.get_drift_reports(limit=10)
            assert len(reports) >= 1
            assert reports[0].drift_type == DriftType.OUTPUT_DRIFT
            await storage.close()

    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        from model_canary.storage.sqlite import SQLiteStorage
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            storage = SQLiteStorage(f"sqlite+aiosqlite:///{db_path}")
            await storage.initialize()
            result = await storage.get_run_result("nonexistent")
            assert result is None
            await storage.close()
