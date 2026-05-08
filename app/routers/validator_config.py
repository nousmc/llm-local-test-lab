from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..database import get_db
from ..models import ValidatorConfig

router = APIRouter(prefix="/config/validator", tags=["validator_config"])


@router.post("/")
async def validator_create(
    request: Request,
    enabled: str = Form("false"),
    provider: str = Form(...),
    model: str = Form(...),
    fallback_provider: str = Form(""),
    fallback_model: str = Form(""),
    validation_mode: str = Form("rubric_json"),
    temperature: str = Form("0.0"),
    max_tokens: str = Form("2048"),
    db: Session = Depends(get_db),
):
    existing = db.query(ValidatorConfig).first()
    if existing:
        return _update_validator(existing, enabled, provider, model, fallback_provider,
                                 fallback_model, validation_mode, temperature, max_tokens, db)

    vc = ValidatorConfig(
        enabled=enabled == "true",
        provider=provider,
        model=model,
        fallback_provider=fallback_provider or None,
        fallback_model=fallback_model or None,
        validation_mode=validation_mode,
        temperature=float(temperature),
        max_tokens=int(max_tokens),
    )
    db.add(vc)
    db.commit()
    return RedirectResponse(url="/config", status_code=303)


@router.post("/{validator_id}")
async def validator_update(
    validator_id: int,
    request: Request,
    enabled: str = Form("false"),
    provider: str = Form(...),
    model: str = Form(...),
    fallback_provider: str = Form(""),
    fallback_model: str = Form(""),
    validation_mode: str = Form("rubric_json"),
    temperature: str = Form("0.0"),
    max_tokens: str = Form("2048"),
    db: Session = Depends(get_db),
):
    vc = db.query(ValidatorConfig).filter(ValidatorConfig.id == validator_id).first()
    if not vc:
        return RedirectResponse(url="/config", status_code=303)

    return _update_validator(vc, enabled, provider, model, fallback_provider,
                             fallback_model, validation_mode, temperature, max_tokens, db)


@router.post("/{validator_id}/delete")
async def validator_delete(validator_id: int, db: Session = Depends(get_db)):
    vc = db.query(ValidatorConfig).filter(ValidatorConfig.id == validator_id).first()
    if vc:
        db.delete(vc)
        db.commit()
    return RedirectResponse(url="/config", status_code=303)


@router.post("/{validator_id}/toggle")
async def validator_toggle(validator_id: int, db: Session = Depends(get_db)):
    vc = db.query(ValidatorConfig).filter(ValidatorConfig.id == validator_id).first()
    if vc:
        vc.enabled = not vc.enabled
        db.commit()
    return RedirectResponse(url="/config", status_code=303)


def _update_validator(vc, enabled: str, provider: str, model: str,
                      fallback_provider: str, fallback_model: str,
                      validation_mode: str, temperature: str, max_tokens: str,
                      db: Session) -> RedirectResponse:
    vc.enabled = enabled == "true"
    vc.provider = provider
    vc.model = model
    vc.fallback_provider = fallback_provider or None
    vc.fallback_model = fallback_model or None
    vc.validation_mode = validation_mode
    vc.temperature = float(temperature)
    vc.max_tokens = int(max_tokens)
    vc.updated_at = datetime.now(timezone.utc)
    db.commit()
    return RedirectResponse(url="/config", status_code=303)
