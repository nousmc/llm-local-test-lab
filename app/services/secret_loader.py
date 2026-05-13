from ..security import load_secrets_from_file as _load_file, encrypt_value, decrypt_value


def load_secrets(secrets_path: str = "secrets/secret.key"):
    try:
        from ..database import SessionLocal
        from ..models import SecretConfig
        db = SessionLocal()
        db_secrets = db.query(SecretConfig).all()
        db.close()

        secrets = {s.key: decrypt_value(s.value) or "" for s in db_secrets}

        if any(secrets.values()):
            return secrets, True

        file_secrets, available = _load_file(secrets_path)
        secrets.update({k: v for k, v in file_secrets.items() if not secrets.get(k)})
        return secrets, available or bool(any(secrets.values()))

    except Exception:
        return _load_file(secrets_path)


def get_api_key(provider: str) -> str | None:
    # Prima: cerca la chiave associata al provider nel DB
    try:
        from ..database import SessionLocal
        from ..models import ProviderConfig, SecretConfig
        db = SessionLocal()
        prov = db.query(ProviderConfig).filter(
            ProviderConfig.name == provider,
            ProviderConfig.enabled == True,
        ).first()
        if prov and prov.api_key_name:
            sc = db.query(SecretConfig).filter(SecretConfig.key == prov.api_key_name).first()
            db.close()
            if sc:
                return decrypt_value(sc.value) or None
        db.close()
    except Exception:
        pass

    # Fallback: convenzione nome per retrocompatibilità
    secrets, _ = load_secrets()
    if provider == "openrouter":
        return secrets.get("OPENROUTER_API_KEY", "") or None
    if provider == "ollama":
        return secrets.get("OLLAMA_API_KEY", "") or None
    return None


def get_app_secret() -> str:
    secrets, _ = load_secrets()
    return secrets.get("APP_SECRET_KEY", "change-me")
