from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..models import SecretConfig
from ..security import encrypt_value, save_secrets_to_file, decrypt_value

router = APIRouter(prefix="/config/secrets", tags=["secrets"])

SYSTEM_KEYS = {"APP_SECRET_KEY"}


@router.get("/edit")
async def secrets_edit_form(request: Request, db: Session = Depends(get_db)):
    return RedirectResponse(url="/config", status_code=303)


@router.post("/new")
async def secret_create(
    key: str = Form(...),
    value: str = Form(""),
    db: Session = Depends(get_db),
):
    key = key.strip().upper().replace(" ", "_")
    if not key:
        return RedirectResponse(url="/config", status_code=303)
    existing = db.query(SecretConfig).filter(SecretConfig.key == key).first()
    if existing:
        if value.strip():
            existing.value = encrypt_value(value.strip())
            db.commit()
    else:
        sc = SecretConfig(key=key, value=encrypt_value(value.strip()) if value.strip() else "")
        db.add(sc)
        db.commit()
    _refresh_secrets_file(db)
    return RedirectResponse(url="/config", status_code=303)


@router.post("/{key}/update")
async def secret_update(
    key: str,
    value: str = Form(""),
    db: Session = Depends(get_db),
):
    sc = db.query(SecretConfig).filter(SecretConfig.key == key).first()
    if sc and value.strip():
        sc.value = encrypt_value(value.strip())
        db.commit()
        _refresh_secrets_file(db)
    return RedirectResponse(url="/config", status_code=303)


@router.post("/{key}/delete")
async def secret_delete(
    key: str,
    db: Session = Depends(get_db),
):
    if key in SYSTEM_KEYS:
        return RedirectResponse(url="/config", status_code=303)
    sc = db.query(SecretConfig).filter(SecretConfig.key == key).first()
    if sc:
        db.delete(sc)
        db.commit()
        _refresh_secrets_file(db)
    return RedirectResponse(url="/config", status_code=303)


def _refresh_secrets_file(db):
    all_secrets = db.query(SecretConfig).all()
    plaintext = {s.key: decrypt_value(s.value) or "" for s in all_secrets}
    save_secrets_to_file("secrets/secret.key", plaintext)
