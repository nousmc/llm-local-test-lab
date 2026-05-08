from ..security import load_secrets_from_file as _load_file, encrypt_value, decrypt_value


def load_secrets(secrets_path: str = "secrets/secret.key"):
    try:
        from ..database import SessionLocal
        from ..models import SecretConfig
        db = SessionLocal()
        db_secrets = db.query(SecretConfig).all()
        db.close()

        desired_keys = ["OPENROUTER_API_KEY", "OLLAMA_API_KEY", "APP_SECRET_KEY"]
        secrets = {}
        for sk in desired_keys:
            db_val = next((s for s in db_secrets if s.key == sk), None)
            if db_val:
                secrets[sk] = decrypt_value(db_val.value) or ""

        if any(secrets.values()):
            available = True
        else:
            file_secrets, available = _load_file(secrets_path)
            secrets.update({k: v for k, v in file_secrets.items() if not secrets.get(k)})
            if not available and not any(secrets.values()):
                available = False

        return secrets, available

    except Exception:
        return _load_file(secrets_path)


def get_api_key(provider: str) -> str | None:
    secrets, _ = load_secrets()
    if provider == "openrouter":
        return secrets.get("OPENROUTER_API_KEY", "") or None
    if provider == "ollama":
        return secrets.get("OLLAMA_API_KEY", "") or None
    return None


def get_app_secret() -> str:
    secrets, _ = load_secrets()
    return secrets.get("APP_SECRET_KEY", "change-me")
