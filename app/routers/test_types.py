from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
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


@router.post("/")
async def test_type_create(
    request: Request,
    id: str = Form(...),
    label: str = Form(...),
    description: str = Form(""),
    expected_json_template: str = Form(""),
    answer_format_template: str = Form(""),
    redirect: str = Form("/test-types"),
    db: Session = Depends(get_db),
):
    """Crea un nuovo tipo di test.

    Args:
        request: Richiesta HTTP.
        id: ID del tipo di test.
        label: Etichetta del tipo di test.
        description: Descrizione del tipo di test.
        expected_json_template: Template JSON atteso.
        answer_format_template: Template del formato di risposta.
        redirect: URL di reindirizzamento dopo la creazione.
        db: Sessione del database.
    """
    existing = db.query(TestType).filter(TestType.id == id).first()
    if not existing:
        tt = TestType(
            id=id,
            label=label,
            description=description or None,
            expected_json_template=expected_json_template or None,
            answer_format_template=answer_format_template or None,
            enabled=True,
        )
        db.add(tt)
        db.commit()
    return RedirectResponse(url=redirect, status_code=303)


@router.post("/{id}/update")
async def test_type_update(
    id: str,
    request: Request,
    label: str = Form(...),
    description: str = Form(""),
    expected_json_template: str = Form(""),
    answer_format_template: str = Form(""),
    redirect: str = Form("/test-types"),
    db: Session = Depends(get_db),
):
    """Aggiorna un tipo di test esistente.

    Args:
        id: ID del tipo di test da aggiornare.
        request: Richiesta HTTP.
        label: Nuova etichetta.
        description: Nuova descrizione.
        expected_json_template: Nuovo template JSON atteso.
        answer_format_template: Nuovo template del formato di risposta.
        redirect: URL di reindirizzamento dopo l'aggiornamento.
        db: Sessione del database.
    """
    tt = db.query(TestType).filter(TestType.id == id).first()
    if tt:
        tt.label = label
        tt.description = description or None
        tt.expected_json_template = expected_json_template or None
        tt.answer_format_template = answer_format_template or None
        db.commit()
    return RedirectResponse(url=redirect, status_code=303)


@router.post("/{id}/delete")
async def test_type_delete(
    id: str,
    request: Request,
    redirect: str = Form("/test-types"),
    db: Session = Depends(get_db),
):
    """Elimina un tipo di test.

    Args:
        id: ID del tipo di test da eliminare.
        request: Richiesta HTTP.
        redirect: URL di reindirizzamento dopo l'eliminazione.
        db: Sessione del database.
    """
    tt = db.query(TestType).filter(TestType.id == id).first()
    if tt:
        db.delete(tt)
        db.commit()
    return RedirectResponse(url=redirect, status_code=303)
