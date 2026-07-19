from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from model_canary.core.interfaces import StorageBackend
from model_canary.core.models import (
    CanaryRunResult,
    DriftReport,
    DriftSeverity,
    DriftType,
    Fingerprint,
)


class Base(DeclarativeBase):
    pass


class RunResultModel(Base):
    __tablename__ = "mc_run_results"

    id = Column(String, primary_key=True)
    suite_name = Column(String, nullable=False)
    status = Column(String, default="running")
    start_time = Column(DateTime, default=lambda: datetime.now(UTC))
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Float, default=0.0)
    total_prompts = Column(Integer, default=0)
    successful_prompts = Column(Integer, default=0)
    failed_prompts = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    total_latency_ms = Column(Float, default=0.0)
    alerts_sent = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    extra = Column(JSON, nullable=True)


class FingerprintModel(Base):
    __tablename__ = "mc_fingerprints"

    id = Column(String, primary_key=True)
    prompt_name = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)
    sha256_hash = Column(String, default="")
    token_count = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    cost_usd = Column(Float, default=0.0)
    refusal = Column(Boolean, default=False)
    stop_reason = Column(String, nullable=True)
    finish_reason = Column(String, nullable=True)
    json_schema_hash = Column(String, nullable=True)
    markdown_structure_hash = Column(String, nullable=True)
    tool_call_count = Column(Integer, default=0)
    function_call_count = Column(Integer, default=0)
    reasoning_length = Column(Integer, nullable=True)
    response_length = Column(Integer, default=0)
    response_hash = Column(String, default="")
    prompt_result_id = Column(String, default="")
    run_id = Column(String, default="", index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    extra = Column(JSON, nullable=True)


class DriftReportModel(Base):
    __tablename__ = "mc_drift_reports"

    id = Column(String, primary_key=True)
    run_id = Column(String, nullable=False, index=True)
    prompt_name = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    drift_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    drift_score = Column(Float, default=0.0)
    drift_details = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    previous_value = Column(Text, nullable=True)
    current_value = Column(Text, nullable=True)
    threshold = Column(Float, nullable=True)
    message = Column(Text, default="")
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    tags = Column(JSON, nullable=True)
    extra = Column(JSON, nullable=True)
    baseline_fingerprint_id = Column(String, nullable=True)
    current_fingerprint_id = Column(String, nullable=True)


class SQLAlchemyStorage(StorageBackend):
    def __init__(self, connection_string: str = "sqlite:///model_canary.db") -> None:
        self._connection_string = connection_string
        self._engine = None
        self._session_factory = None

    async def initialize(self) -> None:
        if self._connection_string.startswith("sqlite"):
            self._engine = create_async_engine(self._connection_string, echo=False)
        else:
            self._engine = create_async_engine(self._connection_string, echo=False)
        self._session_factory = async_sessionmaker(self._engine, class_=AsyncSession)
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()

    async def save_run_result(self, result: CanaryRunResult) -> None:
        async with self._session_factory() as session:
            model = RunResultModel(
                id=result.id,
                suite_name=result.suite_name,
                status=result.status,
                start_time=result.start_time,
                end_time=result.end_time,
                duration_ms=result.duration_ms,
                total_prompts=result.total_prompts,
                successful_prompts=result.successful_prompts,
                failed_prompts=result.failed_prompts,
                total_cost=result.total_cost,
                total_latency_ms=result.total_latency_ms,
                alerts_sent=result.alerts_sent,
                error=result.error,
                extra=result.extra,
            )
            session.add(model)
            await session.commit()

    async def save_drift_report(self, report: DriftReport) -> None:
        async with self._session_factory() as session:
            model = DriftReportModel(
                id=report.id,
                run_id=report.run_id,
                prompt_name=report.prompt_name,
                model=report.model,
                provider=report.provider,
                drift_type=report.drift_type.value,
                severity=report.severity.value,
                drift_score=report.drift_score,
                drift_details=report.drift_details,
                metrics=report.metrics,
                previous_value=report.previous_value,
                current_value=report.current_value,
                threshold=report.threshold,
                message=report.message,
                timestamp=report.timestamp,
                acknowledged=report.acknowledged,
                acknowledged_by=report.acknowledged_by,
                acknowledged_at=report.acknowledged_at,
                tags=list(report.tags) if report.tags else None,
                extra=report.extra,
                baseline_fingerprint_id=report.baseline_fingerprint.id,
                current_fingerprint_id=report.current_fingerprint.id,
            )
            session.add(model)
            await session.commit()

    async def save_fingerprint(self, fingerprint: Fingerprint) -> None:
        async with self._session_factory() as session:
            model = FingerprintModel(
                id=fingerprint.id,
                prompt_name=fingerprint.prompt_name,
                model=fingerprint.model,
                provider=fingerprint.provider,
                sha256_hash=fingerprint.sha256_hash,
                token_count=fingerprint.token_count,
                latency_ms=fingerprint.latency_ms,
                cost_usd=fingerprint.cost_usd,
                refusal=fingerprint.refusal,
                stop_reason=fingerprint.stop_reason,
                finish_reason=fingerprint.finish_reason,
                json_schema_hash=fingerprint.json_schema_hash,
                markdown_structure_hash=fingerprint.markdown_structure_hash,
                tool_call_count=fingerprint.tool_call_count,
                function_call_count=fingerprint.function_call_count,
                reasoning_length=fingerprint.reasoning_length,
                response_length=fingerprint.response_length,
                response_hash=fingerprint.response_hash,
                prompt_result_id=fingerprint.prompt_result_id,
                run_id=fingerprint.run_id,
                timestamp=fingerprint.timestamp,
                extra=fingerprint.extra,
            )
            session.add(model)
            await session.commit()

    async def get_run_result(self, run_id: str) -> CanaryRunResult | None:
        async with self._session_factory() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(RunResultModel).where(RunResultModel.id == run_id)
            )
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return CanaryRunResult(
                id=model.id,
                suite_name=model.suite_name,
                status=model.status,
                start_time=model.start_time,
                end_time=model.end_time,
                duration_ms=model.duration_ms,
                total_prompts=model.total_prompts,
                successful_prompts=model.successful_prompts,
                failed_prompts=model.failed_prompts,
                total_cost=model.total_cost,
                total_latency_ms=model.total_latency_ms,
                alerts_sent=model.alerts_sent,
                error=model.error,
                extra=model.extra or {},
            )

    async def get_latest_fingerprint(
        self, prompt_name: str, model: str, provider: str
    ) -> Fingerprint | None:
        async with self._session_factory() as session:
            from sqlalchemy import desc, select
            result = await session.execute(
                select(FingerprintModel)
                .where(
                    FingerprintModel.prompt_name == prompt_name,
                    FingerprintModel.model == model,
                    FingerprintModel.provider == provider,
                )
                .order_by(desc(FingerprintModel.timestamp))
                .limit(1)
            )
            model_obj = result.scalar_one_or_none()
            if model_obj is None:
                return None
            return self._model_to_fingerprint(model_obj)

    async def get_drift_reports(
        self,
        prompt_name: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        severity: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DriftReport]:
        async with self._session_factory() as session:
            from sqlalchemy import desc, select
            query = select(DriftReportModel)
            if prompt_name:
                query = query.where(DriftReportModel.prompt_name == prompt_name)
            if model:
                query = query.where(DriftReportModel.model == model)
            if provider:
                query = query.where(DriftReportModel.provider == provider)
            if severity:
                query = query.where(DriftReportModel.severity == severity)
            query = query.order_by(desc(DriftReportModel.timestamp)).offset(offset).limit(limit)
            result = await session.execute(query)
            models = result.scalars().all()
            return [self._model_to_drift_report(m) for m in models]

    async def get_fingerprint_history(
        self,
        prompt_name: str,
        model: str,
        provider: str,
        limit: int = 100,
    ) -> list[Fingerprint]:
        async with self._session_factory() as session:
            from sqlalchemy import desc, select
            result = await session.execute(
                select(FingerprintModel)
                .where(
                    FingerprintModel.prompt_name == prompt_name,
                    FingerprintModel.model == model,
                    FingerprintModel.provider == provider,
                )
                .order_by(desc(FingerprintModel.timestamp))
                .limit(limit)
            )
            models = result.scalars().all()
            return [self._model_to_fingerprint(m) for m in models]

    def _model_to_fingerprint(self, model: FingerprintModel) -> Fingerprint:
        return Fingerprint(
            id=model.id,
            prompt_name=model.prompt_name,
            model=model.model,
            provider=model.provider,
            sha256_hash=model.sha256_hash or "",
            token_count=model.token_count or 0,
            latency_ms=model.latency_ms or 0.0,
            cost_usd=model.cost_usd or 0.0,
            refusal=model.refusal or False,
            stop_reason=model.stop_reason,
            finish_reason=model.finish_reason,
            json_schema_hash=model.json_schema_hash,
            markdown_structure_hash=model.markdown_structure_hash,
            tool_call_count=model.tool_call_count or 0,
            function_call_count=model.function_call_count or 0,
            reasoning_length=model.reasoning_length,
            response_length=model.response_length or 0,
            response_hash=model.response_hash or "",
            prompt_result_id=model.prompt_result_id or "",
            run_id=model.run_id or "",
            timestamp=model.timestamp,
            extra=model.extra or {},
        )

    def _model_to_drift_report(self, model: DriftReportModel) -> DriftReport:
        baseline = Fingerprint(
            id=model.baseline_fingerprint_id or "",
            prompt_name=model.prompt_name,
            model=model.model,
            provider=model.provider,
        )
        current = Fingerprint(
            id=model.current_fingerprint_id or "",
            prompt_name=model.prompt_name,
            model=model.model,
            provider=model.provider,
        )
        return DriftReport(
            id=model.id,
            run_id=model.run_id,
            prompt_name=model.prompt_name,
            model=model.model,
            provider=model.provider,
            drift_type=DriftType(model.drift_type),
            severity=DriftSeverity(model.severity),
            baseline_fingerprint=baseline,
            current_fingerprint=current,
            drift_score=model.drift_score or 0.0,
            drift_details=model.drift_details or {},
            metrics=model.metrics or {},
            previous_value=model.previous_value,
            current_value=model.current_value,
            threshold=model.threshold,
            message=model.message or "",
            timestamp=model.timestamp,
            acknowledged=model.acknowledged or False,
            acknowledged_by=model.acknowledged_by,
            acknowledged_at=model.acknowledged_at,
            tags=list(model.tags) if model.tags else [],
            extra=model.extra or {},
        )
