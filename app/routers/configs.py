from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ProviderConfig, ValidatorConfig, SecretConfig
from ..services.config_loader import load_config, reload_config
from ..services.secret_loader import load_secrets
from ..security import decrypt_value

router = APIRouter(prefix="/config", tags=["config"])


def _secret_context(db: Session):
    secrets, available = load_secrets()
    masked = {}
    for key, val in secrets.items():
        if val and len(val) > 4:
            masked[key] = val[:4] + "*" * (len(val) - 8) + val[-4:] if len(val) > 8 else val[:2] + "**"
        else:
            masked[key] = val or "(non impostata)"

    db_secrets = db.query(SecretConfig).all()
    plain = {}
    for ds in db_secrets:
        plain[ds.key] = decrypt_value(ds.value) or ""

    return masked, plain, available


@router.get("/", response_class=HTMLResponse)
async def config_page(request: Request, db: Session = Depends(get_db)):
    config = load_config()
    masked, plain, available = _secret_context(db)
    providers = db.query(ProviderConfig).all()
    validator = db.query(ValidatorConfig).first()

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="config.html",
        context={
            "request": request,
            "config": config,
            "secrets": masked,
            "secret_plain": plain,
            "secrets_available": available,
            "providers": providers,
            "validator": validator,
            "validators_providers": providers,
            "mode": "view",
        },
    )


@router.get("/providers/{provider_id}/edit", response_class=HTMLResponse)
async def provider_edit_form(provider_id: int, request: Request, db: Session = Depends(get_db)):
    config = load_config()
    masked, plain, available = _secret_context(db)
    providers = db.query(ProviderConfig).all()
    validator = db.query(ValidatorConfig).first()
    edit_provider = db.query(ProviderConfig).filter(ProviderConfig.id == provider_id).first()

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="config.html",
        context={
            "request": request,
            "config": config,
            "secrets": masked,
            "secret_plain": plain,
            "secrets_available": available,
            "providers": providers,
            "validator": validator,
            "validators_providers": providers,
            "edit_provider": edit_provider,
            "mode": "edit_provider",
        },
    )


@router.get("/validator/edit", response_class=HTMLResponse)
async def validator_edit_form(request: Request, db: Session = Depends(get_db)):
    config = load_config()
    masked, plain, available = _secret_context(db)
    providers = db.query(ProviderConfig).all()
    validator = db.query(ValidatorConfig).first()

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="config.html",
        context={
            "request": request,
            "config": config,
            "secrets": masked,
            "secret_plain": plain,
            "secrets_available": available,
            "providers": providers,
            "validator": validator,
            "validators_providers": providers,
            "mode": "edit_validator",
        },
    )


@router.post("/reload")
async def config_reload(request: Request):
    config = reload_config()
    return {"status": "ok", "message": "Configurazione ricaricata"}
