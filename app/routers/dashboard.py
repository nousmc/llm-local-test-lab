import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db, SessionLocal
from ..models import ConfiguredModel, TestCase, TestRun, TestResult, MetricResult
from ..services.chart_builder import build_dashboard_charts

router = APIRouter()

DEFAULT = {
    "total_models": 0,
    "enabled_models": 0,
    "total_test_cases": 0,
    "total_runs": 0,
    "completed_runs": 0,
    "avg_score": 0.0,
    "best_model": None,
    "error_rate": 0.0,
    "avg_latency": 0.0,
}


@router.get("/", response_class=HTMLResponse)
async def root(request: Request, db: Session = Depends(get_db)):
    return await dashboard(request, db)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    stats = _get_stats(db)
    recent_runs = db.query(TestRun).order_by(TestRun.created_at.desc()).limit(10).all()
    chart_data = build_dashboard_charts(db)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"request": request, "stats": stats, "recent_runs": recent_runs, "chart_data": json.dumps(chart_data)},
    )


def _get_stats(db: Session) -> dict:
    try:
        total_models = db.query(ConfiguredModel).count()
        enabled_models = db.query(ConfiguredModel).filter(ConfiguredModel.enabled == True).count()
        total_test_cases = db.query(TestCase).count()
        total_runs = db.query(TestRun).count()
        completed_runs = db.query(TestRun).filter(TestRun.status == "completed").count()

        all_final_scores = db.query(MetricResult.metric_value).filter(
            MetricResult.metric_name == "final_score"
        ).all()
        scores = [s[0] for s in all_final_scores if s[0] is not None]
        avg_score = round(sum(scores) / len(scores), 4) if scores else 0.0

        errors = db.query(TestResult).filter(
            TestResult.status.in_(["failed", "timeout"]),
            TestResult.error_type != None,
            TestResult.error_type != "",
        ).count()
        error_rate = round(errors / max(1, db.query(TestResult).count()) * 100, 1)

        latencies = db.query(TestResult.latency_ms).filter(TestResult.latency_ms != None).all()
        avg_lat = round(sum(l[0] for l in latencies) / len(latencies), 2) if latencies else 0.0

        best = _get_best_model(db, all_final_scores)

        return {
            "total_models": total_models,
            "enabled_models": enabled_models,
            "total_test_cases": total_test_cases,
            "total_runs": total_runs,
            "completed_runs": completed_runs,
            "avg_score": avg_score,
            "best_model": best,
            "error_rate": error_rate,
            "avg_latency": avg_lat,
        }
    except Exception:
        return DEFAULT


def _get_best_model(db, scores_query):
    try:
        model_scores = {}
        results = db.query(TestResult).all()
        for r in results:
            for m in (r.metrics or []):
                if m.metric_name == "final_score" and m.metric_value is not None:
                    if r.model_id not in model_scores:
                        model_scores[r.model_id] = []
                    model_scores[r.model_id].append(m.metric_value)
        if model_scores:
            best_id = max(model_scores, key=lambda k: sum(model_scores[k]) / len(model_scores[k]))
            model = db.query(ConfiguredModel).filter(ConfiguredModel.id == best_id).first()
            return model.label if model else best_id
    except Exception:
        pass
    return None
