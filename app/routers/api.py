import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ConfiguredModel, TestCase, TestRun, TestResult, MetricResult, TestType
from ..schemas import PromptPreviewRequest

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/models")
async def api_models(db: Session = Depends(get_db)):
    models = db.query(ConfiguredModel).all()
    return [
        {
            "id": m.id,
            "label": m.label,
            "provider": m.provider,
            "model_name": m.model_name,
            "enabled": m.enabled,
            "family": m.family,
            "size_b": m.size_b,
            "context_window": m.context_window,
            "supports_vision": m.supports_vision,
            "supports_json": m.supports_json,
        }
        for m in models
    ]


@router.get("/test-cases")
async def api_test_cases(db: Session = Depends(get_db)):
    test_cases = db.query(TestCase).all()
    return [
        {
            "id": tc.id,
            "test_type_id": tc.test_type_id,
            "title": tc.title,
            "description": tc.description,
            "difficulty": tc.difficulty,
            "risk_level": tc.risk_level,
            "enabled": tc.enabled,
            "created_at": str(tc.created_at) if tc.created_at else None,
        }
        for tc in test_cases
    ]


@router.post("/preview-prompt")
async def api_preview_prompt(data: PromptPreviewRequest, db: Session = Depends(get_db)):
    from ..services.prompt_builder import _build_generated_prompt, validate_prompt

    test_type = db.query(TestType).filter(TestType.id == data.test_type_id).first()

    class _FakeTC:
        pass

    fake_tc = _FakeTC()
    fake_tc.test_type_id = data.test_type_id
    fake_tc.title = data.title
    fake_tc.description = data.description or None
    fake_tc.input_text = data.input_text or None
    fake_tc.context_text = data.context_text or None
    fake_tc.system_prompt = data.system_prompt or None
    fake_tc.rules = data.custom_rules or None
    fake_tc.expected_output_json = data.expected_output_json or None
    fake_tc.user_prompt_template = None

    prompt = _build_generated_prompt(fake_tc, test_type)

    allowed_source = (data.input_text or "") + "\n" + (data.context_text or "")
    valid, issues, status = validate_prompt(
        prompt,
        data.test_type_id,
        data.expected_output_json or None,
        allowed_source_text=allowed_source,
    )

    prompt_lower = prompt.lower()
    checks = {
        "has_json_instruction": "rispondi esclusivamente con un json" in prompt_lower,
        "has_response_container": '"answer"' in prompt,
        "no_unreplaced_placeholders": "{input_text}" not in prompt and "{{input_text}}" not in prompt,
        "no_contamination": not any(i.startswith("contamination") for i in issues),
        "allowed_labels_present": data.test_type_id != "classification"
            or "Classi ammesse" in prompt
            or '"allowed_labels"' in prompt,
    }

    warnings = []
    if data.test_type_id == "code_analysis":
        try:
            d = json.loads(data.expected_output_json or "{}")
            if not d.get("code_language"):
                warnings.append("code_language non impostato — il prompt mostrerà 'Linguaggio: it'")
        except Exception:
            pass

    expected_schema_preview = {}
    if data.expected_output_json:
        try:
            d = json.loads(data.expected_output_json)
            if isinstance(d, dict):
                expected_schema_preview = d.get("schema", d.get("expected_fields", d.get("expected", {})))
                if not isinstance(expected_schema_preview, dict):
                    expected_schema_preview = {}
        except Exception:
            pass

    return JSONResponse({
        "prompt": prompt,
        "valid": valid,
        "issues": issues,
        "warnings": warnings,
        "checks": checks,
        "expected_schema_preview": expected_schema_preview,
        "status": status,
    })


@router.post("/test-cases")
async def api_test_case_create(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    tc = TestCase(
        test_type_id=body.get("test_type_id", ""),
        title=body.get("title", ""),
        description=body.get("description"),
        input_text=body.get("input_text"),
        context_text=body.get("context_text"),
        system_prompt=body.get("system_prompt"),
        user_prompt_template=body.get("user_prompt_template"),
        expected_output_json=body.get("expected_output_json"),
        expected_text=body.get("expected_text"),
        expected_labels_json=body.get("expected_labels_json"),
        rubric_json=body.get("rubric_json"),
        tags_json=body.get("tags_json"),
        difficulty=body.get("difficulty", "medium"),
        risk_level=body.get("risk_level", "low"),
        enabled=body.get("enabled", True),
    )
    db.add(tc)
    db.commit()
    return JSONResponse({"id": tc.id, "status": "created"})


@router.post("/test-runs")
async def api_test_run_create(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    run = TestRun(
        name=body.get("name", "API Run"),
        description=body.get("description", ""),
        status="created",
        selected_model_ids_json=json.dumps(body.get("selected_model_ids", [])),
        selected_test_case_ids_json=json.dumps(body.get("selected_test_case_ids", [])),
    )
    db.add(run)
    db.commit()
    return JSONResponse({"id": run.id, "status": "created"})


@router.post("/test-runs/{id}/start")
async def api_test_run_start(id: int, db: Session = Depends(get_db)):
    from .test_runs import _running_tasks
    from ..services.test_runner import execute_test_run
    import asyncio

    run = db.query(TestRun).filter(TestRun.id == id).first()
    if not run:
        return JSONResponse({"error": "not found"}, status_code=404)
    if run.status == "running":
        return JSONResponse({"status": "already running"})

    run.status = "running"
    from datetime import datetime, timezone
    run.started_at = datetime.now(timezone.utc)
    db.commit()

    task = asyncio.create_task(execute_test_run(id))
    _running_tasks[id] = task

    return JSONResponse({"status": "started"})


@router.get("/test-runs/{id}")
async def api_test_run_get(id: int, db: Session = Depends(get_db)):
    run = db.query(TestRun).filter(TestRun.id == id).first()
    if not run:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {
        "id": run.id,
        "name": run.name,
        "status": run.status,
        "selected_model_ids": json.loads(run.selected_model_ids_json or "[]"),
        "selected_test_case_ids": json.loads(run.selected_test_case_ids_json or "[]"),
        "started_at": str(run.started_at) if run.started_at else None,
        "completed_at": str(run.completed_at) if run.completed_at else None,
        "created_at": str(run.created_at) if run.created_at else None,
    }


@router.get("/test-runs/{id}/results")
async def api_test_run_results(id: int, db: Session = Depends(get_db)):
    results = db.query(TestResult).filter(TestResult.test_run_id == id).all()
    data = []
    for r in results:
        score = None
        for m in (r.metrics or []):
            if m.metric_name == "final_score":
                score = m.metric_value
                break
        data.append({
            "id": r.id,
            "test_case_id": r.test_case_id,
            "model_id": r.model_id,
            "provider": r.provider,
            "status": r.status,
            "score": score,
            "latency_ms": r.latency_ms,
            "error": r.error_message,
        })
    return data


@router.get("/reports/{id}")
async def api_report(id: int, db: Session = Depends(get_db)):
    from ..models import Report
    report = db.query(Report).filter(Report.id == id).first()
    if not report:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {
        "id": report.id,
        "test_run_id": report.test_run_id,
        "title": report.title,
        "summary_text": report.summary_text,
        "findings": json.loads(report.findings_json or "{}"),
        "created_at": str(report.created_at) if report.created_at else None,
    }
