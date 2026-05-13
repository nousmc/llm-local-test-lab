from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json
import yaml
from pathlib import Path

from ..database import get_db
from ..models import TestLibrary, TestCase

router = APIRouter(prefix="/libraries", tags=["libraries"])


def seed_libraries_from_yaml(db: Session, yaml_path: str = "config/config.yaml") -> list[str]:
    """Crea librerie di test dal file YAML di configurazione se non gia presenti.

    Args:
        db: Sessione del database.
        yaml_path: Percorso del file YAML di configurazione.

    Returns:
        Lista degli ID delle librerie create.
    """
    path = Path(yaml_path)
    if not path.exists():
        return []

    try:
        data = yaml.safe_load(path.read_text())
    except Exception:
        return []

    libraries = data.get("libraries") or data.get("test_libraries") or []
    if not isinstance(libraries, list):
        return []

    created = []
    for lib_data in libraries:
        if not isinstance(lib_data, dict):
            continue
        lib_id = str(lib_data.get("id") or "")
        if not lib_id:
            continue
        existing = db.query(TestLibrary).filter(TestLibrary.id == lib_id).first()
        if existing:
            continue
        lib = TestLibrary(
            id=lib_id,
            label=str(lib_data.get("label", lib_id)),
            description=str(lib_data.get("description", "")) or None,
            domain=str(lib_data.get("domain", "")) or None,
            tags_json=json.dumps(lib_data.get("tags", []) if isinstance(lib_data.get("tags"), list) else []),
            enabled=bool(lib_data.get("enabled", True)),
        )
        db.add(lib)
        created.append(lib_id)

    if created:
        db.commit()
    return created


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
    redirect: str = Form("/libraries"),
    db: Session = Depends(get_db),
):
    if not db.query(TestLibrary).filter(TestLibrary.id == id).first():
        lib = TestLibrary(id=id, label=label, description=description or None,
                          domain=domain or None, tags_json=json.dumps([t.strip() for t in tags.split(",") if t.strip()]),
                          enabled=enabled == "true")
        db.add(lib)
        db.commit()
    return RedirectResponse(url=redirect, status_code=303)


@router.post("/{lib_id}/update")
async def library_update(
    lib_id: str,
    request: Request,
    label: str = Form(...),
    description: str = Form(""),
    domain: str = Form(""),
    tags: str = Form(""),
    enabled: str = Form("true"),
    redirect: str = Form("/libraries"),
    db: Session = Depends(get_db),
):
    """Aggiorna una libreria di test esistente.

    Args:
        lib_id: ID della libreria da aggiornare.
        request: Richiesta HTTP.
        label: Nuova etichetta.
        description: Nuova descrizione.
        domain: Nuovo dominio.
        tags: Nuovi tag separati da virgola.
        enabled: Stato abilitato.
        redirect: URL di reindirizzamento.
        db: Sessione del database.
    """
    lib = db.query(TestLibrary).filter(TestLibrary.id == lib_id).first()
    if lib:
        lib.label = label
        lib.description = description or None
        lib.domain = domain or None
        lib.tags_json = json.dumps([t.strip() for t in tags.split(",") if t.strip()])
        lib.enabled = enabled == "true"
        lib.updated_at = datetime.now(timezone.utc)
        db.commit()
    return RedirectResponse(url=redirect, status_code=303)


@router.post("/{lib_id}/delete")
async def library_delete(
    lib_id: str,
    request: Request,
    redirect: str = Form("/libraries"),
    db: Session = Depends(get_db),
):
    """Elimina una libreria di test e riassegna i suoi test case a 'general'.

    Args:
        lib_id: ID della libreria da eliminare.
        request: Richiesta HTTP.
        redirect: URL di reindirizzamento dopo l'eliminazione.
        db: Sessione del database.
    """
    lib = db.query(TestLibrary).filter(TestLibrary.id == lib_id).first()
    if lib:
        for tc in db.query(TestCase).filter(TestCase.library_id == lib_id).all():
            tc.library_id = "general"
        db.delete(lib)
        db.commit()
    return RedirectResponse(url=redirect, status_code=303)


@router.post("/{lib_id}/toggle")
async def library_toggle(
    lib_id: str,
    request: Request,
    redirect: str = Form("/libraries"),
    db: Session = Depends(get_db),
):
    """Attiva/disattiva una libreria di test.

    Args:
        lib_id: ID della libreria.
        request: Richiesta HTTP.
        redirect: URL di reindirizzamento.
        db: Sessione del database.
    """
    lib = db.query(TestLibrary).filter(TestLibrary.id == lib_id).first()
    if lib:
        lib.enabled = not lib.enabled
        db.commit()
    return RedirectResponse(url=redirect, status_code=303)

