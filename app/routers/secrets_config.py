from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..models import SecretConfig
from ..security import encrypt_value, save_secrets_to_file

router = APIRouter(prefix="/config/secrets", tags=["secrets"])

PREDEFINED_KEYS = ["OPENROUTER_API_KEY", "OLLAMA_API_KEY", "APP_SECRET_KEY"]


@router.get("/edit")
async def secrets_edit_form(request: Request, db: Session = Depends(get_db)):
    return RedirectResponse(url="/config", status_code=303)


@router.post("/")
async def secrets_save(
    request: Request,
    db: Session = Depends(get_db),
):
    form = await request.form()

    plaintext_secrets = {}
    for key in PREDEFINED_KEYS:
        val = form.get(key, "")
        if isinstance(val, str):
            plaintext_secrets[key] = val.strip()

    for key, val in plaintext_secrets.items():
        existing = db.query(SecretConfig).filter(SecretConfig.key == key).first()
        encrypted = encrypt_value(val) if val else ""

        if existing:
            existing.value = encrypted
        elif val:
            sc = SecretConfig(key=key, value=encrypted)
            db.add(sc)

    existing_keys = {s.key for s in db.query(SecretConfig).all()}

    db.commit()
    db.close()

    final_secrets = {}
    final_db = SessionLocal()
    try:
        for key in PREDEFINED_KEYS:
            db_val = final_db.query(SecretConfig).filter(SecretConfig.key == key).first()
            if db_val:
                from ..security import decrypt_value
                final_secrets[key] = decrypt_value(db_val.value) or ""
            else:
                final_secrets[key] = ""
    finally:
        final_db.close()

    save_secrets_to_file("secrets/secret.key", final_secrets)

    return RedirectResponse(url="/config", status_code=303)
