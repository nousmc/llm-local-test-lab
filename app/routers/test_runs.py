import json
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from ..database import get_db, retry_commit
from ..models import TestRun, TestResult, TestCase, ConfiguredModel, MetricResult, ValidationResult
from ..services.test_runner import execute_test_run
from ..services.report_builder import generate_report, generate_csv
from ..services.chart_builder import build_run_charts
from ..schemas import TestRunCreate

router = APIRouter(prefix="/test-runs", tags=["test_runs"])

_running_tasks = {}


@router.get("/", response_class=HTMLResponse)
async def test_run_list(request: Request, db: Session = Depends(get_db)):
    runs = db.query(TestRun).order_by(TestRun.created_at.desc()).all()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="test_run_create.html",
        context={"request": request, "runs": runs, "lib_groups": {}, "total_test_cases": 0, "mode": "list"},
    )


@router.get("/new", response_class=HTMLResponse)
async def test_run_new(request: Request, db: Session = Depends(get_db)):
    models = db.query(ConfiguredModel).filter(ConfiguredModel.enabled == True).all()
    test_cases = db.query(TestCase).filter(TestCase.enabled == True).order_by(TestCase.library_id, TestCase.test_type_id, TestCase.title).all()
    from ..models import TestLibrary
    libraries = db.query(TestLibrary).all()
    lib_map = {lib.id: lib for lib in libraries}
    lib_groups = {}
    for tc in test_cases:
        lid = tc.library_id or "general"
        if lid not in lib_groups:
            lib_groups[lid] = {"label": lib_map[lid].label if lid in lib_map else "General", "cases": []}
        lib_groups[lid]["cases"].append(tc)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="test_run_create.html",
        context={
            "request": request,
            "models": models,
            "lib_groups": lib_groups,
            "total_test_cases": len(test_cases),
            "mode": "create",
        },
    )


@router.post("/")
async def test_run_create(
    request: Request,
    db: Session = Depends(get_db),
):
    form = await request.form()
    name = form.get("name", "Unnamed Run")
    description = form.get("description", "")
    requested_model_ids = [str(x) for x in form.getlist("model_ids") if str(x).strip()]
    requested_test_case_ids = [int(x) for x in form.getlist("test_case_ids") if str(x).strip()]

    valid_model_ids = {
        row.id for row in db.query(ConfiguredModel.id).filter(ConfiguredModel.enabled == True).all()
    }
    valid_test_case_ids = {
        row.id for row in db.query(TestCase.id).filter(TestCase.enabled == True).all()
    }

    model_ids = [mid for mid in requested_model_ids if mid in valid_model_ids]
    test_case_ids = [tcid for tcid in requested_test_case_ids if tcid in valid_test_case_ids]

    run = TestRun(
        name=str(name),
        description=str(description),
        status="created" if model_ids and test_case_ids else "failed",
        selected_model_ids_json=json.dumps(model_ids),
        selected_test_case_ids_json=json.dumps(test_case_ids),
        execution_config_json=json.dumps({
            "create_validation": {
                "requested_model_ids": requested_model_ids,
                "accepted_model_ids": model_ids,
                "requested_test_case_ids": requested_test_case_ids,
                "accepted_test_case_ids": test_case_ids,
                "error": None if model_ids and test_case_ids else "Seleziona almeno un modello e almeno un test case abilitati",
            }
        }),
        validator_config_json="{}",
    )
    db.add(run)
    db.commit()

    return RedirectResponse(url=f"/test-runs/{run.id}", status_code=303)


@router.get("/{id}", response_class=HTMLResponse)
async def test_run_detail(id: int, request: Request, db: Session = Depends(get_db)):
    run = db.query(TestRun).filter(TestRun.id == id).first()
    if not run:
        return RedirectResponse(url="/test-runs")

    results = db.query(TestResult).filter(TestResult.test_run_id == id).all()
    chart_data = build_run_charts(db, id)

    results_data = []
    for r in results:
        score = None
        for m in (r.metrics or []):
            if m.metric_name == "final_score":
                score = m.metric_value
                break
        results_data.append({
            "id": r.id,
            "test_case_id": r.test_case_id,
            "test_case_title": r.test_case.title if r.test_case else "",
            "test_case_desc": r.test_case.description if r.test_case else "",
            "model_id": r.model_id,
            "provider": r.provider,
            "status": r.status,
            "score": score,
            "latency_ms": r.latency_ms,
            "error": r.error_message,
        })

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="test_run_detail.html",
        context={
            "request": request,
            "run": run,
            "results": results_data,
            "chart_data": json.dumps(chart_data),
            "chart_data_raw": chart_data,
            "total_results": len(results),
            "completed": sum(1 for r in results if r.status == "completed"),
            "failed": sum(1 for r in results if r.status in ("failed", "timeout")),
            "avg_score": round(sum(s["score"] for s in results_data if s["score"] is not None) / max(1, sum(1 for s in results_data if s["score"] is not None)), 4),
            "avg_latency": round(sum(r.latency_ms for r in results if r.latency_ms) / max(1, sum(1 for r in results if r.latency_ms)), 2),
            "executive_report": run.executive_report_text if run.status in ("completed", "failed") else None,
            "report": None,
        },
    )


@router.post("/{id}/start")
async def test_run_start(id: int, db: Session = Depends(get_db)):
    run = db.query(TestRun).filter(TestRun.id == id).first()
    if not run or run.status == "running":
        return RedirectResponse(url=f"/test-runs/{id}", status_code=303)

    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    retry_commit(db)

    task = asyncio.create_task(execute_test_run(id))
    _running_tasks[id] = task

    return RedirectResponse(url=f"/test-runs/{id}", status_code=303)


@router.post("/{id}/cancel")
async def test_run_cancel(id: int, request: Request, db: Session = Depends(get_db)):
    run = db.query(TestRun).filter(TestRun.id == id).first()
    if not run or run.status != "running":
        return RedirectResponse(url=f"/test-runs/{id}", status_code=303)

    if id in _running_tasks:
        _running_tasks[id].cancel()
        del _running_tasks[id]

    await asyncio.sleep(0.5)

    from ..database import SessionLocal as _DB
    new_db = _DB()
    try:
        run2 = new_db.query(TestRun).filter(TestRun.id == id).first()
        if run2:
            run2.status = "cancelled"
            run2.completed_at = datetime.now(timezone.utc)
            retry_commit(new_db)
    except Exception as e:
        print(f"Cancel commit warning: {e}")
    finally:
        new_db.close()

    return RedirectResponse(url=f"/test-runs/{id}", status_code=303)


@router.post("/{id}/rerun-failed")
async def test_run_rerun_failed(id: int, db: Session = Depends(get_db)):
    run = db.query(TestRun).filter(TestRun.id == id).first()
    if not run:
        return RedirectResponse(url="/test-runs")
    if run.status not in ("completed", "failed"):
        return RedirectResponse(url=f"/test-runs/{id}", status_code=303)

    failed_results = db.query(TestResult).filter(
        TestResult.test_run_id == id,
        TestResult.status.in_(["failed", "timeout"]),
    ).all()

    for fr in failed_results:
        fr.status = "pending"
        fr.error_message = None
        fr.error_type = None
        fr.response_text = None
        fr.response_json = None
        fr.raw_response_json = None
        fr.latency_ms = None
        fr.started_at = None
        fr.completed_at = None

    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    run.completed_at = None
    retry_commit(db)

    task = asyncio.create_task(execute_test_run(id))
    _running_tasks[id] = task

    return RedirectResponse(url=f"/test-runs/{id}", status_code=303)


@router.get("/{id}/results")
async def test_run_results(id: int, request: Request, db: Session = Depends(get_db)):
    return await test_run_detail(id, request, db)


@router.get("/{id}/results/{result_id}", response_class=HTMLResponse)
async def test_result_detail(id: int, result_id: int, request: Request, db: Session = Depends(get_db)):
    result = db.query(TestResult).filter(TestResult.id == result_id, TestResult.test_run_id == id).first()
    if not result:
        return RedirectResponse(url=f"/test-runs/{id}")

    validations = db.query(ValidationResult).filter(ValidationResult.test_result_id == result_id).all()
    metrics = db.query(MetricResult).filter(MetricResult.test_result_id == result_id).all()

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="test_run_detail.html",
        context={
            "request": request,
            "run": result.test_run,
            "result_detail": result,
            "validations": validations,
            "metrics": metrics,
            "results": [],
            "chart_data": "{}",
            "total_results": 0,
            "completed": 0,
            "failed": 0,
            "mode": "result_detail",
        },
    )


@router.get("/{id}/results.csv")
async def test_run_results_csv(id: int, db: Session = Depends(get_db)):
    results = db.query(TestResult).filter(TestResult.test_run_id == id).all()
    csv_content = generate_csv(results)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=run_{id}_results.csv"},
    )


@router.get("/{id}/results.json")
async def test_run_results_json(id: int, db: Session = Depends(get_db)):
    results = db.query(TestResult).filter(TestResult.test_run_id == id).all()
    data = []
    for r in results:
        score = None
        for m in (r.metrics or []):
            if m.metric_name == "final_score":
                score = m.metric_value
                break
        data.append({
            "run_id": r.test_run_id,
            "test_case_id": r.test_case_id,
            "test_type": r.test_case.test_type_id if r.test_case else "",
            "model_id": r.model_id,
            "provider": r.provider,
            "model_name": r.model_name,
            "score": score,
            "latency_ms": r.latency_ms,
            "tokens_per_second": r.tokens_per_second,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "total_tokens": r.total_tokens,
            "error_message": r.error_message,
            "status": r.status,
        })
    return Response(
        content=json.dumps(data, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=run_{id}_results.json"},
    )
