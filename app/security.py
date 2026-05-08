import base64
import os
from pathlib import Path


def _get_cipher_key() -> bytes:
    key = os.environ.get("APP_SECRET_KEY", "change-me-llm-test-lab-2026")
    return key.encode().ljust(32, b'\x00')[:32]


def encrypt_value(plain: str) -> str:
    if not plain:
        return ""
    key = _get_cipher_key()
    data = plain.encode()
    encrypted = bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_value(encoded: str) -> str:
    if not encoded:
        return ""
    try:
        key = _get_cipher_key()
        encrypted = base64.urlsafe_b64decode(encoded.encode())
        data = bytes([encrypted[i] ^ key[i % len(key)] for i in range(len(encrypted))])
        return data.decode()
    except Exception:
        return ""


def load_secrets_from_file(secrets_path: str) -> dict:
    secrets = {
        "OPENROUTER_API_KEY": "",
        "OLLAMA_API_KEY": "",
        "APP_SECRET_KEY": "",
    }
    path = Path(secrets_path)
    if not path.exists():
        return secrets, False
    try:
        content = path.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                secrets[key.strip()] = val.strip().strip('"').strip("'")
        return secrets, True
    except Exception:
        return secrets, False


def save_secrets_to_file(secrets_path: str, secrets: dict) -> bool:
    try:
        lines = []
        for key, val in secrets.items():
            lines.append(f"{key}={val}")
        Path(secrets_path).write_text("\n".join(lines) + "\n")
        return True
    except Exception:
        return False
