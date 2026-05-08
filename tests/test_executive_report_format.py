import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.report_builder import _normalize_executive_report


def test_normalize_plain_text_keeps_sections():
    text = """Sintesi esecutiva
Risultati buoni.

Confronto tra modelli
Il modello A e migliore.
"""
    normalized = _normalize_executive_report(text)
    assert "Sintesi esecutiva" in normalized
    assert "Confronto tra modelli" in normalized


def test_normalize_removes_markdown_fences():
    text = "```markdown\n# Sintesi esecutiva\n**Risultati buoni**\n```"
    normalized = _normalize_executive_report(text)
    assert "```" not in normalized
    assert "#" not in normalized
    assert "**" not in normalized
    assert "Sintesi esecutiva" in normalized


def test_normalize_extracts_json_report_field():
    payload = {"executive_report": "Sintesi esecutiva\\nTutto ok.\\n\\nRaccomandazioni operative\\nUsare modello A."}
    normalized = _normalize_executive_report(json.dumps(payload))
    assert "executive_report" not in normalized
    assert "Sintesi esecutiva" in normalized
    assert "\n" in normalized
    assert "\\n" not in normalized


def test_normalize_extracts_json_section_fields():
    payload = {
        "sintesi_esecutiva": "Score alto.",
        "confronto_modelli": ["A meglio di B", "B piu lento"],
        "analisi_errori": "Nessun errore critico.",
        "raccomandazioni": "Usare A in produzione.",
    }
    normalized = _normalize_executive_report(json.dumps(payload))
    assert "Sintesi Esecutiva" in normalized
    assert "- A meglio di B" in normalized
    assert "Analisi Errori" in normalized


def test_normalize_numbered_sections():
    text = """1. Sintesi esecutiva
Ok.

2. Confronto tra modelli
A e migliore.
"""
    normalized = _normalize_executive_report(text)
    assert "1. Sintesi" not in normalized
    assert "Sintesi esecutiva" in normalized
    assert "Confronto tra modelli" in normalized
