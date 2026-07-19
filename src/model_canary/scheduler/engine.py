from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from model_canary.core.exceptions import ScheduleError
from model_canary.core.interfaces import Scheduler

logger = logging.getLogger("model_canary.scheduler")


class CanaryScheduler(Scheduler):
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._jobs: dict[str, str] = {}
        self._running = False

    @property
    def name(self) -> str:
        return "apscheduler"

    async def start(self) -> None:
        try:
            self._scheduler.start()
            self._running = True
            logger.info("Scheduler started")
        except Exception as e:
            raise ScheduleError(f"Failed to start scheduler: {e}")

    async def stop(self) -> None:
        try:
            if self._scheduler.running:
                self._scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Scheduler stopped")
        except Exception as e:
            raise ScheduleError(f"Failed to stop scheduler: {e}")

    async def add_job(
        self,
        job_id: str,
        func: Callable,
        cron_expr: str,
        **kwargs: Any,
    ) -> None:
        if job_id in self._jobs:
            logger.warning("Job '%s' already exists, replacing", job_id)
            await self.remove_job(job_id)

        try:
            if cron_expr and self._is_cron(cron_expr):
                parts = cron_expr.strip().split()
                trigger = CronTrigger(
                    second=parts[0] if len(parts) > 0 else "0",
                    minute=parts[1] if len(parts) > 1 else "*",
                    hour=parts[2] if len(parts) > 2 else "*",
                    day=parts[3] if len(parts) > 3 else "*",
                    month=parts[4] if len(parts) > 4 else "*",
                    day_of_week=parts[5] if len(parts) > 5 else "*",
                )
            else:
                interval = int(kwargs.get("interval_seconds", 300))
                trigger = IntervalTrigger(seconds=interval)

            async def wrapped_func():
                try:
                    if asyncio.iscoroutinefunction(func):
                        await func()
                    else:
                        func()
                except Exception as e:
                    logger.error("Scheduled job '%s' failed: %s", job_id, e)

            self._scheduler.add_job(
                wrapped_func,
                trigger=trigger,
                id=job_id,
                replace_existing=True,
                name=job_id,
            )
            self._jobs[job_id] = cron_expr
            logger.info("Added scheduled job '%s': %s", job_id, cron_expr)
        except Exception as e:
            raise ScheduleError(f"Failed to add job '{job_id}': {e}")

    async def remove_job(self, job_id: str) -> None:
        try:
            self._scheduler.remove_job(job_id)
            self._jobs.pop(job_id, None)
            logger.info("Removed scheduled job '%s'", job_id)
        except Exception as e:
            raise ScheduleError(f"Failed to remove job '{job_id}': {e}")

    def _is_cron(self, expr: str) -> bool:
        parts = expr.strip().split()
        return 5 <= len(parts) <= 6

    def get_jobs(self) -> dict[str, str]:
        return dict(self._jobs)

    def is_running(self) -> bool:
        return self._running
