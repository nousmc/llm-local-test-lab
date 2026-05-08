from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import TestType

router = APIRouter(prefix="/test-types", tags=["test_types"])


@router.get("/", response_class=HTMLResponse)
async def test_type_list(request: Request, db: Session = Depends(get_db)):
    test_types = db.query(TestType).all()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="test_type_list.html",
        context={"request": request, "test_types": test_types},
    )


@router.get("/{test_type_id}", response_class=HTMLResponse)
async def test_type_detail(test_type_id: str, request: Request, db: Session = Depends(get_db)):
    tt = db.query(TestType).filter(TestType.id == test_type_id).first()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="test_type_list.html",
        context={"request": request, "test_types": [tt] if tt else []},
    )
