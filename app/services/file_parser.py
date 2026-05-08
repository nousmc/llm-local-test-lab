from pathlib import Path

ALLOWED_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".pdf", ".png", ".jpg", ".jpeg"}
MAX_SIZE_MB = 50


def read_uploaded_file(filepath: str) -> str:
    path = Path(filepath)
    if not path.exists():
        return ""
    ext = path.suffix.lower()
    if ext in {".txt", ".md", ".csv", ".json"}:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""
    return ""


def validate_upload(filename: str, size_bytes: int) -> tuple[bool, str]:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Estensione non consentita: {ext}. Consentite: {ALLOWED_EXTENSIONS}"
    if size_bytes > MAX_SIZE_MB * 1024 * 1024:
        return False, f"File troppo grande. Massimo {MAX_SIZE_MB} MB"
    return True, ""
