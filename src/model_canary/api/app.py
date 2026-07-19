from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from model_canary import __version__
from model_canary.core.models import (
    PromptConfig,
)
from model_canary.engine import CanaryEngine


def create_app(
    config_path: str | None = None,
    title: str = "Model Canary API",
    _engine: CanaryEngine | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = _engine or CanaryEngine(config_path=config_path)
        await engine.initialize()
        app.state.engine = engine
        yield
        if _engine is None:
            await engine.close()

    app = FastAPI(
        title=title,
        version=__version__,
        description="Detect AI Model Drift Before Production Does",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    if _engine is not None:
        app.state.engine = _engine

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ===== Health =====

    @app.get("/health", tags=["System"])
    async def health():
        return {
            "status": "ok",
            "version": __version__,
            "service": "model-canary",
        }

    # ===== Runs =====

    @app.get("/api/v1/runs", tags=["Runs"])
    async def list_runs(
        limit: int = Query(20, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        engine = app.state.engine
        try:
            reports = await engine._storage.get_drift_reports(limit=limit)
            return {"runs": [r.model_dump(mode='json') for r in reports], "total": len(reports)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/v1/runs/{run_id}", tags=["Runs"])
    async def get_run(run_id: str):
        engine = app.state.engine
        result = await engine._storage.get_run_result(run_id)
        if not result:
            raise HTTPException(status_code=404, detail="Run not found")
        return result.model_dump(mode='json')

    # ===== Drift Reports =====

    @app.get("/api/v1/drifts", tags=["Drifts"])
    async def list_drifts(
        prompt_name: str | None = Query(None),
        model: str | None = Query(None),
        provider: str | None = Query(None),
        severity: str | None = Query(None),
        limit: int = Query(50, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        engine = app.state.engine
        reports = await engine._storage.get_drift_reports(
            prompt_name=prompt_name,
            model=model,
            provider=provider,
            severity=severity,
            limit=limit,
            offset=offset,
        )
        return {
            "drifts": [r.model_dump(mode='json') for r in reports],
            "total": len(reports),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/drifts/{drift_id}", tags=["Drifts"])
    async def get_drift(drift_id: str):
        engine = app.state.engine
        reports = await engine._storage.get_drift_reports(limit=1000)
        for r in reports:
            if r.id == drift_id:
                return r.model_dump(mode='json')
        raise HTTPException(status_code=404, detail="Drift report not found")

    # ===== Fingerprints =====

    @app.get("/api/v1/fingerprints", tags=["Fingerprints"])
    async def list_fingerprints(
        prompt_name: str = Query(...),
        model: str | None = Query(None),
        provider: str | None = Query(None),
        limit: int = Query(50, ge=1, le=1000),
    ):
        engine = app.state.engine
        model_val = model or ""
        provider_val = provider or ""
        fps = await engine._storage.get_fingerprint_history(
            prompt_name=prompt_name,
            model=model_val,
            provider=provider_val,
            limit=limit,
        )
        return {
            "fingerprints": [fp.model_dump(mode='json') for fp in fps],
            "total": len(fps),
        }

    # ===== Execute =====

    @app.post("/api/v1/run", tags=["Execution"])
    async def execute_run(
        suite_name: str | None = None,
    ):
        engine = app.state.engine
        if suite_name:
            result = await engine.run_suite(suite_name)
        else:
            results = await engine.run_all_suites()
            return {"results": [r.model_dump(mode='json') for r in results]}
        return result.model_dump(mode='json')

    @app.post("/api/v1/run/prompt", tags=["Execution"])
    async def execute_prompt(
        prompt: str,
        provider: str,
        model: str | None = None,
    ):
        engine = app.state.engine
        prompt_cfg = PromptConfig(name="api-prompt", prompt=prompt, model=model or "")
        result = await engine.run_prompt(prompt_cfg, provider)
        return result.model_dump(mode='json')

    # ===== Benchmark =====

    @app.post("/api/v1/benchmark", tags=["Benchmark"])
    async def benchmark(
        prompt: str,
        models: list[str] = Query(...),
        providers: list[str] | None = Query(None),
    ):
        engine = app.state.engine
        results = await engine.benchmark(prompt, models, providers)
        return {"results": results}

    # ===== Compare =====

    @app.get("/api/v1/compare", tags=["Compare"])
    async def compare(
        prompt_name: str = Query(...),
        provider_a: str = Query(...),
        provider_b: str = Query(...),
    ):
        engine = app.state.engine
        result = await engine.compare(prompt_name, provider_a, provider_b)
        return result

    # ===== Stats =====

    @app.get("/api/v1/stats", tags=["Stats"])
    async def get_stats():
        engine = app.state.engine
        reports = await engine._storage.get_drift_reports(limit=10000)

        total_reports = len(reports)
        severity_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}

        for r in reports:
            severity_counts[r.severity.value] = severity_counts.get(r.severity.value, 0) + 1
            type_counts[r.drift_type.value] = type_counts.get(r.drift_type.value, 0) + 1

        return {
            "total_drifts": total_reports,
            "by_severity": severity_counts,
            "by_type": type_counts,
            "critical_count": severity_counts.get("critical", 0),
            "high_count": severity_counts.get("high", 0),
        }

    # ===== Providers =====

    @app.get("/api/v1/providers", tags=["Providers"])
    async def list_providers():
        engine = app.state.engine
        return {
            "providers": list(engine._providers.keys()),
            "count": len(engine._providers),
        }

    # ===== Prompts =====

    @app.get("/api/v1/prompts", tags=["Prompts"])
    async def list_prompts():
        engine = app.state.engine
        prompts = []
        for suite in engine._config.test_suites:
            for p in suite.prompts:
                prompts.append({
                    "name": p.name,
                    "description": p.description,
                    "category": p.category,
                    "severity": p.severity.value,
                    "suite": suite.name,
                    "evaluators": p.evaluators,
                })
        return {"prompts": prompts, "total": len(prompts)}

    # ===== Dashboard HTML =====

    @app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
    async def dashboard_page():
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Model Canary Dashboard</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #0d1117; color: #c9d1d9; }
                .container { max-width: 1200px; margin: 0 auto; }
                h1 { color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
                .card { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 20px; margin: 10px 0; }
                .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
                .stat-card { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 15px; text-align: center; }
                .stat-value { font-size: 2em; font-weight: bold; color: #58a6ff; }
                .stat-label { color: #8b949e; font-size: 0.9em; margin-top: 5px; }
                .critical { color: #f85149; }
                .high { color: #d29922; }
                .medium { color: #a371f7; }
                .table { width: 100%; border-collapse: collapse; margin: 15px 0; }
                .table th, .table td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #30363d; }
                .table th { color: #8b949e; font-weight: 600; }
                .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
                .badge-critical { background: #f85149; color: white; }
                .badge-high { background: #d29922; color: white; }
                .badge-medium { background: #a371f7; color: white; }
                .badge-low { background: #238636; color: white; }
                .refresh { float: right; padding: 8px 16px; background: #238636; color: white; border: none; border-radius: 6px; cursor: pointer; }
                .refresh:hover { background: #2ea043; }
                .footer { margin-top: 30px; text-align: center; color: #8b949e; font-size: 0.8em; }
                pre { background: #0d1117; padding: 10px; border-radius: 4px; overflow-x: auto; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Model Canary Dashboard <button class="refresh" onclick="location.reload()">Refresh</button></h1>
                <div id="stats" class="stats"></div>
                <div class="card">
                    <h2>Recent Drift Reports</h2>
                    <table class="table" id="drifts-table">
                        <thead><tr><th>Type</th><th>Severity</th><th>Prompt</th><th>Model</th><th>Score</th><th>Time</th><th>Message</th></tr></thead>
                        <tbody id="drifts-body"></tbody>
                    </table>
                </div>
                <div class="card">
                    <h2>Configuration</h2>
                    <pre id="config-display">Loading...</pre>
                </div>
                <div class="footer">
                    Model Canary v""" + __version__ + """ &mdash; <a href="/docs" style="color: #58a6ff;">API Docs</a>
                </div>
            </div>
            <script>
                async function loadData() {
                    try {
                        const [statsRes, driftsRes, healthRes] = await Promise.all([
                            fetch('/api/v1/stats'),
                            fetch('/api/v1/drifts?limit=20'),
                            fetch('/health')
                        ]);
                        const stats = await statsRes.json();
                        const drifts = await driftsRes.json();

                        // Stats
                        const statsHtml = `
                            <div class="stat-card"><div class="stat-value">${stats.total_drifts}</div><div class="stat-label">Total Drifts</div></div>
                            <div class="stat-card"><div class="stat-value critical">${stats.critical_count}</div><div class="stat-label">Critical</div></div>
                            <div class="stat-card"><div class="stat-value high">${stats.high_count}</div><div class="stat-label">High</div></div>
                            <div class="stat-card"><div class="stat-value">${stats.total_drifts - stats.critical_count - stats.high_count}</div><div class="stat-label">Medium/Low</div></div>
                        `;
                        document.getElementById('stats').innerHTML = statsHtml;

                        // Drifts
                        const tbody = document.getElementById('drifts-body');
                        tbody.innerHTML = drifts.drifts.map(d => {
                            const badgeClass = d.severity === 'critical' ? 'badge-critical' : d.severity === 'high' ? 'badge-high' : d.severity === 'medium' ? 'badge-medium' : 'badge-low';
                            return `<tr>
                                <td>${d.drift_type}</td>
                                <td><span class="badge ${badgeClass}">${d.severity}</span></td>
                                <td>${d.prompt_name}</td>
                                <td>${d.model}</td>
                                <td>${d.drift_score.toFixed(4)}</td>
                                <td>${new Date(d.timestamp).toLocaleString()}</td>
                                <td>${d.message.substring(0, 60)}...</td>
                            </tr>`;
                        }).join('');

                    } catch(e) {
                        document.getElementById('drifts-body').innerHTML = `<tr><td colspan="7">Error loading data: ${e.message}</td></tr>`;
                    }
                }
                loadData();
                setInterval(loadData, 30000);
            </script>
        </body>
        </html>
        """)

    return app
