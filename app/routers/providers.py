from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..database import get_db
from ..models import ProviderConfig

router = APIRouter(prefix="/config/providers", tags=["providers"])


@router.post("/")
async def provider_create(
    request: Request,
    name: str = Form(...),
    label: str = Form(...),
    base_url: str = Form(...),
    timeout_seconds: int = Form(180),
    enabled: str = Form("true"),
    app_name: str = Form(""),
    site_url: str = Form(""),
    db: Session = Depends(get_db),
):
    existing = db.query(ProviderConfig).filter(ProviderConfig.name == name).first()
    if existing:
        return RedirectResponse(url="/config", status_code=303)

    prov = ProviderConfig(
        name=name,
        label=label,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        enabled=enabled == "true",
        app_name=app_name or None,
        site_url=site_url or None,
    )
    db.add(prov)
    db.commit()
    return RedirectResponse(url="/config", status_code=303)


@router.post("/{provider_id}")
async def provider_update(
    provider_id: int,
    request: Request,
    name: str = Form(...),
    label: str = Form(...),
    base_url: str = Form(...),
    timeout_seconds: int = Form(180),
    enabled: str = Form("true"),
    app_name: str = Form(""),
    site_url: str = Form(""),
    db: Session = Depends(get_db),
):
    prov = db.query(ProviderConfig).filter(ProviderConfig.id == provider_id).first()
    if not prov:
        return RedirectResponse(url="/config", status_code=303)

    prov.name = name
    prov.label = label
    prov.base_url = base_url
    prov.timeout_seconds = timeout_seconds
    prov.enabled = enabled == "true"
    prov.app_name = app_name or None
    prov.site_url = site_url or None
    prov.updated_at = datetime.now(timezone.utc)
    db.commit()
    return RedirectResponse(url="/config", status_code=303)


@router.post("/{provider_id}/delete")
async def provider_delete(provider_id: int, db: Session = Depends(get_db)):
    prov = db.query(ProviderConfig).filter(ProviderConfig.id == provider_id).first()
    if prov:
        db.delete(prov)
        db.commit()
    return RedirectResponse(url="/config", status_code=303)


@router.post("/{provider_id}/toggle")
async def provider_toggle(provider_id: int, db: Session = Depends(get_db)):
    prov = db.query(ProviderConfig).filter(ProviderConfig.id == provider_id).first()
    if prov:
        prov.enabled = not prov.enabled
        db.commit()
    return RedirectResponse(url="/config", status_code=303)
