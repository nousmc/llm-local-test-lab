from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

from ..database import get_db
from ..models import TestLibrary, TestCase

router = APIRouter(prefix="/libraries", tags=["libraries"])


@router.get("/", response_class=HTMLResponse)
async def library_list(request: Request, db: Session = Depends(get_db)):
    libs = db.query(TestLibrary).all()
    lib_data = []
    for lib in libs:
        tc_count = db.query(TestCase).filter(TestCase.library_id == lib.id).count()
        type_counts = {}
        for row in db.query(TestCase.test_type_id).filter(TestCase.library_id == lib.id).distinct().all():
            type_counts[row[0]] = db.query(TestCase).filter(TestCase.library_id == lib.id, TestCase.test_type_id == row[0]).count()
        lib_data.append({"lib": lib, "tc_count": tc_count, "type_counts": type_counts})

    return request.app.state.templates.TemplateResponse(
        request=request, name="test_library_list.html",
        context={"request": request, "libraries": lib_data},
    )


@router.post("/")
async def library_create(
    request: Request,
    id: str = Form(...), label: str = Form(...),
    description: str = Form(""), domain: str = Form(""),
    tags: str = Form(""), enabled: str = Form("true"),
    db: Session = Depends(get_db),
):
    if not db.query(TestLibrary).filter(TestLibrary.id == id).first():
        lib = TestLibrary(id=id, label=label, description=description or None,
                          domain=domain or None, tags_json=json.dumps([t.strip() for t in tags.split(",") if t.strip()]),
                          enabled=enabled == "true")
        db.add(lib)
        db.commit()
    return RedirectResponse(url="/libraries", status_code=303)


@router.post("/{lib_id}/delete")
async def library_delete(lib_id: str, db: Session = Depends(get_db)):
    lib = db.query(TestLibrary).filter(TestLibrary.id == lib_id).first()
    if lib:
        for tc in db.query(TestCase).filter(TestCase.library_id == lib_id).all():
            tc.library_id = "general"
        db.delete(lib)
        db.commit()
    return RedirectResponse(url="/libraries", status_code=303)


@router.post("/{lib_id}/toggle")
async def library_toggle(lib_id: str, db: Session = Depends(get_db)):
    lib = db.query(TestLibrary).filter(TestLibrary.id == lib_id).first()
    if lib:
        lib.enabled = not lib.enabled
        db.commit()
    return RedirectResponse(url="/libraries", status_code=303)
