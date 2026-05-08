import json
import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, File, Form, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import TestCase, TestType, UploadedFile
from ..schemas import TestCaseCreate, TestCaseUpdate
from ..services.file_parser import validate_upload, read_uploaded_file

router = APIRouter(prefix="/test-cases", tags=["test_cases"])


@router.get("/", response_class=HTMLResponse)
async def test_case_list(request: Request, db: Session = Depends(get_db)):
    test_cases = db.query(TestCase).order_by(TestCase.library_id, TestCase.test_type_id, TestCase.title).all()
    test_types = db.query(TestType).all()
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
        name="test_case_form.html",
        context={
            "request": request,
            "lib_groups": lib_groups,
            "test_cases": test_cases,
            "test_types": test_types,
            "mode": "list",
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def test_case_new(request: Request, db: Session = Depends(get_db)):
    test_types = db.query(TestType).all()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="test_case_form.html",
        context={"request": request, "test_types": test_types, "lib_groups": {}, "test_cases": [], "mode": "create", "tc": None},
    )


@router.post("/")
async def test_case_create(
    request: Request,
    title: str = Form(...),
    test_type_id: str = Form(...),
    description: str = Form(""),
    input_text: str = Form(""),
    context_text: str = Form(""),
    system_prompt: str = Form(""),
    user_prompt_template: str = Form(""),
    expected_output_json: str = Form(""),
    expected_text: str = Form(""),
    expected_labels_json: str = Form(""),
    rubric_json: str = Form(""),
    tags_json: str = Form(""),
    difficulty: str = Form("medium"),
    risk_level: str = Form("low"),
    enabled: str = Form("true"),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    uploaded_path = None
    if file and file.filename:
        valid, error = validate_upload(file.filename, file.size or 0)
        if not valid:
            return HTMLResponse(f"<script>alert('{error}');window.history.back();</script>")
        ext = os.path.splitext(file.filename)[1]
        stored_name = f"{uuid.uuid4().hex}{ext}"
        stored_path = f"app/uploads/{stored_name}"
        os.makedirs("app/uploads", exist_ok=True)
        content = await file.read()
        with open(stored_path, "wb") as f:
            f.write(content)
        uploaded_path = stored_path

        uf = UploadedFile(
            original_filename=file.filename,
            stored_path=stored_path,
            mime_type=file.content_type,
            size_bytes=file.size,
        )
        db.add(uf)

    tc = TestCase(
        test_type_id=test_type_id,
        title=title,
        description=description or None,
        input_text=input_text or None,
        input_file_path=uploaded_path,
        context_text=context_text or None,
        system_prompt=system_prompt or None,
        user_prompt_template=user_prompt_template or None,
        expected_output_json=expected_output_json or None,
        expected_text=expected_text or None,
        expected_labels_json=expected_labels_json or None,
        rubric_json=rubric_json or None,
        tags_json=tags_json or None,
        difficulty=difficulty,
        risk_level=risk_level,
        enabled=enabled == "true",
    )
    db.add(tc)
    db.commit()
    return RedirectResponse(url="/test-cases", status_code=303)


@router.get("/{id}", response_class=HTMLResponse)
async def test_case_detail(id: int, request: Request, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == id).first()
    if not tc:
        return RedirectResponse(url="/test-cases")
    test_types = db.query(TestType).all()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="test_case_form.html",
        context={"request": request, "tc": tc, "test_types": test_types, "lib_groups": {}, "test_cases": [], "mode": "detail"},
    )


@router.get("/{id}/edit", response_class=HTMLResponse)
async def test_case_edit(id: int, request: Request, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == id).first()
    if not tc:
        return RedirectResponse(url="/test-cases")
    test_types = db.query(TestType).all()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="test_case_form.html",
        context={"request": request, "tc": tc, "test_types": test_types, "lib_groups": {}, "test_cases": [], "mode": "edit"},
    )


@router.post("/{id}")
async def test_case_update(
    id: int,
    request: Request,
    title: str = Form(...),
    test_type_id: str = Form(...),
    description: str = Form(""),
    input_text: str = Form(""),
    context_text: str = Form(""),
    system_prompt: str = Form(""),
    user_prompt_template: str = Form(""),
    expected_output_json: str = Form(""),
    expected_text: str = Form(""),
    expected_labels_json: str = Form(""),
    rubric_json: str = Form(""),
    tags_json: str = Form(""),
    difficulty: str = Form("medium"),
    risk_level: str = Form("low"),
    enabled: str = Form("true"),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    tc = db.query(TestCase).filter(TestCase.id == id).first()
    if not tc:
        return RedirectResponse(url="/test-cases")

    tc.test_type_id = test_type_id
    tc.title = title
    tc.description = description or None
    tc.input_text = input_text or None
    tc.context_text = context_text or None
    tc.system_prompt = system_prompt or None
    tc.user_prompt_template = user_prompt_template or None
    tc.expected_output_json = expected_output_json or None
    tc.expected_text = expected_text or None
    tc.expected_labels_json = expected_labels_json or None
    tc.rubric_json = rubric_json or None
    tc.tags_json = tags_json or None
    tc.difficulty = difficulty
    tc.risk_level = risk_level
    tc.enabled = enabled == "true"
    tc.updated_at = datetime.now(timezone.utc)

    if file and file.filename:
        valid, error = validate_upload(file.filename, file.size or 0)
        if not valid:
            return HTMLResponse(f"<script>alert('{error}');window.history.back();</script>")
        ext = os.path.splitext(file.filename)[1]
        stored_name = f"{uuid.uuid4().hex}{ext}"
        stored_path = f"app/uploads/{stored_name}"
        os.makedirs("app/uploads", exist_ok=True)
        content = await file.read()
        with open(stored_path, "wb") as f:
            f.write(content)
        tc.input_file_path = stored_path

    db.commit()
    return RedirectResponse(url="/test-cases", status_code=303)


@router.post("/{id}/delete")
async def test_case_delete(id: int, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == id).first()
    if tc:
        db.delete(tc)
        db.commit()
    return RedirectResponse(url="/test-cases", status_code=303)
