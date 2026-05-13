import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import TestRun, Report, TestResult
from ..services.report_builder import generate_report, generate_csv
from ..services.config_loader import get_weighted_score_threshold

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/", response_class=HTMLResponse)
async def report_list(request: Request, db: Session = Depends(get_db)):
    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    runs_with_reports = []
    for rep in reports:
        run = db.query(TestRun).filter(TestRun.id == rep.test_run_id).first()
        runs_with_reports.append({"report": rep, "run": run})

    runs_without_reports = db.query(TestRun).filter(
        TestRun.status.in_(["completed", "failed"])
    ).order_by(TestRun.completed_at.desc()).all()
    missing = []
    for run in runs_without_reports:
        existing = db.query(Report).filter(Report.test_run_id == run.id).first()
        if not existing:
            missing.append(run)

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="report_detail.html",
        context={
            "request": request,
            "reports": runs_with_reports,
            "runs_without_reports": missing,
            "mode": "list",
        },
    )


@router.get("/{test_run_id}", response_class=HTMLResponse)
async def report_detail(test_run_id: int, request: Request, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.test_run_id == test_run_id).first()
    run = db.query(TestRun).filter(TestRun.id == test_run_id).first()

    if not report:
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="report_detail.html",
            context={
                "request": request,
                "report": None,
                "run": run,
                "mode": "missing",
            },
        )

    findings = json.loads(report.findings_json or "{}")
    charts = json.loads(report.chart_payload_json or "{}")

    benchmark_cfg = json.loads(run.benchmark_config_json or "{}") if run else {}
    is_benchmark = benchmark_cfg.get("enabled", False)
    benchmark_stats = None
    benchmark_chart = None
    if is_benchmark:
        try:
            from ..services.benchmark_stats import compute_benchmark_stats, build_benchmark_chart_data
            benchmark_stats = compute_benchmark_stats(db, test_run_id)
            benchmark_chart = build_benchmark_chart_data(benchmark_stats)
        except Exception:
            benchmark_stats = None
            benchmark_chart = None

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="report_detail.html",
        context={
            "request": request,
            "report": report,
            "run": run,
            "findings": findings,
            "charts": json.dumps(charts),
            "weighted_score_threshold": get_weighted_score_threshold(),
            "is_benchmark": is_benchmark,
            "benchmark_stats": benchmark_stats,
            "benchmark_chart": json.dumps(benchmark_chart) if benchmark_chart else "{}",
            "benchmark_chart_raw": benchmark_chart,
            "mode": "detail",
        },
    )


@router.post("/{test_run_id}/generate")
async def report_generate(test_run_id: int, db: Session = Depends(get_db)):
    report = generate_report(db, test_run_id)
    if not report:
        return RedirectResponse(url="/reports", status_code=303)
    return RedirectResponse(url=f"/reports/{test_run_id}", status_code=303)


@router.get("/{test_run_id}/export/html", response_class=HTMLResponse)
async def report_export_html(test_run_id: int, request: Request, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.test_run_id == test_run_id).first()
    run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not report or not run:
        return HTMLResponse("<h1>Report not found</h1>")

    findings = json.loads(report.findings_json or "{}")
    results = db.query(TestResult).filter(TestResult.test_run_id == test_run_id).all()

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Report: {run.name}</title>
<style>body{{font-family:Arial;max-width:1200px;margin:20px auto;padding:20px}}
h1{{color:#333}}h2{{border-bottom:2px solid #eee}}table{{width:100%;border-collapse:collapse;margin:10px 0}}
th,td{{border:1px solid #ddd;padding:8px;text-align:left}}th{{background:#f5f5f5}}
.pass{{color:green}}.fail{{color:red}}.score{{font-weight:bold}}</style></head>
<body><h1>{run.name}</h1>
<p>{run.description or ""}</p>
<h2>Sintesi</h2>
<p>Totale test: {findings.get("total", 0)} | Passati: {findings.get("passed_count", 0)} | Falliti: {findings.get("failed", 0)}</p>
<p>Score medio: {findings.get("avg_score", 0)} | Pass rate: {findings.get("pass_rate", 0)}%</p>
<p>Latenza media: {findings.get("avg_latency", 0)}ms</p>
<h2>Risultati per modello</h2>
<table><tr><th>Modello</th><th>Avg Score</th><th>Pass Rate</th><th>Test</th></tr>"""
    for mid, mdata in findings.get("model_stats", {}).items():
        html += f"<tr><td>{mdata.get('label', mid)}</td><td>{mdata.get('avg_score', 0)}</td><td>{mdata.get('pass_rate', 0)}%</td><td>{mdata.get('total', 0)}</td></tr>"
    html += "</table>"
    html += "<h2>Errori</h2><table><tr><th>Tipo</th><th>Conteggio</th></tr>"
    for etype, count in findings.get("errors_by_type", {}).items():
        html += f"<tr><td>{etype}</td><td>{count}</td></tr>"
    html += "</table>"
    html += f"<p style='margin-top:30px'>Generato: {report.created_at}</p></body></html>"
    return HTMLResponse(html)


@router.get("/{test_run_id}/export/json")
async def report_export_json(test_run_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.test_run_id == test_run_id).first()
    if not report:
        return Response("{}", media_type="application/json")
    data = {
        "title": report.title,
        "summary": report.summary_text,
        "findings": json.loads(report.findings_json or "{}"),
        "created_at": str(report.created_at),
    }
    return Response(
        content=json.dumps(data, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=report_{test_run_id}.json"},
    )


@router.get("/{test_run_id}/export/csv")
async def report_export_csv(test_run_id: int, db: Session = Depends(get_db)):
    results = db.query(TestResult).filter(TestResult.test_run_id == test_run_id).all()
    csv_content = generate_csv(results)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{test_run_id}.csv"},
    )
