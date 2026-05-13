import sys
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
os.environ["APP_SECRET_KEY"] = "test-key-2026"


from app.services.prompt_builder import (
    PROMPT_TEMPLATES, _extract_expected_schema, _build_field_list,
    _build_field_placeholders, _get_allowed_labels, validate_prompt,
)
from app.models import TestCase, TestType


def _make_tc(test_type_id, input_text, expected=None, description="", context="", rules=None):
    return TestCase(
        test_type_id=test_type_id, title="Test", input_text=input_text,
        description=description, context_text=context,
        expected_output_json=json.dumps(expected) if expected else None,
        rules=rules,
    )


def _make_tt(test_type_id, label=""):
    return TestType(id=test_type_id, label=label or test_type_id.replace("_", " ").title())


def _build(test_type_id, input_text, expected=None, description="", context="", rules=None):
    from app.services.test_runner import _build_prompt
    tc = _make_tc(test_type_id, input_text, expected, description, context, rules=rules)
    tt = _make_tt(test_type_id)
    return _build_prompt(tc, tt)


# ============================================================
# Classification tests
# ============================================================
def test_classification_has_allowed_labels():
    expected = {"label": "helpdesk_password_reset",
                "allowed_labels": ["helpdesk_password_reset", "network_issue", "billing", "other"]}
    prompt = _build("classification", "Ticket: non riesco ad accedere dopo cambio password", expected)
    assert "helpdesk_password_reset" in prompt, "Prompt must include allowed labels"
    assert "network_issue" in prompt
    assert "billing" in prompt
    assert "Classi ammesse" in prompt, "Must have allowed classes section"
    assert "label" in prompt.lower(), "Must have answer structure with label field"


def test_classification_no_expected_values_in_prompt():
    expected = {"label": "helpdesk_password_reset",
                "allowed_labels": ["helpdesk_password_reset", "network_issue", "billing", "other"]}
    prompt = _build("classification", "Ticket: non riesco ad accedere dopo cambio password", expected)
    assert "label corretta" not in prompt.lower(), "Correct label hint must not be in prompt"
    assert '"helpdesk_password_reset"' not in prompt.lower() or prompt.lower().count('"helpdesk_password_reset"') <= 1


def test_classification_allowed_label_is_not_contamination():
    from app.services.metrics import check_prompt_contamination

    expected = {"schema": {"label": "string"},
                "expected": {"label": "helpdesk_password_reset"},
                "required_fields": ["label"],
                "allowed_labels": ["helpdesk_password_reset", "network_issue", "billing", "other"]}
    prompt = _build("classification", "Ticket: non riesco ad accedere dopo cambio password", expected)
    contaminated, info = check_prompt_contamination(prompt, json.dumps(expected))
    assert not contaminated, f"Allowed classification label should not be contamination: {info}"


def test_classification_has_explicit_structure():
    expected = {"label": "helpdesk_password_reset",
                "allowed_labels": ["helpdesk_password_reset", "network_issue"]}
    prompt = _build("classification", "Test input", expected)
    assert '"label"' in prompt, "Must have explicit label field in answer structure"
    assert '"answer"' in prompt
    assert 'classification_expected' not in prompt.lower(), "No generic schema placeholder"


def test_classification_no_allowed_labels_invalid():
    expected = {"label": "helpdesk_password_reset"}
    tc = _make_tc("classification", "Test", expected)
    tt = _make_tt("classification")
    from app.services.test_runner import _build_prompt as bp
    prompt = bp(tc, tt)
    valid, issues, status = validate_prompt(prompt, "classification", tc.expected_output_json)
    assert "missing_allowed_labels" in issues, f"Should detect missing allowed labels, got: {issues}"


# ============================================================
# Data extraction tests
# ============================================================
def test_data_extraction_has_field_list():
    expected = {"schema": {"invoice_number": "string", "date": "date", "total": "number"},
                "expected": {"invoice_number": "42", "date": "2026-04-15", "total": 1280.40},
                "required_fields": ["invoice_number", "total"]}
    rules = "Se un dato non e presente o non e leggibile, usa null per quel campo."
    prompt = _build("data_extraction", "Fattura 42 del 15/04/2026: 1280.40 EUR", expected, rules=rules)
    assert "invoice_number" in prompt, "Must list field names"
    assert "total" in prompt
    assert "date" in prompt
    assert "null" in prompt.lower(), "Must mention null for missing data"


def test_data_extraction_no_expected_values():
    expected = {"schema": {"invoice_number": "string", "total": "number"},
                "expected": {"invoice_number": "42", "total": 1280.40}}
    prompt = _build("data_extraction", "Fattura 42: 1280.40 EUR", expected)
    assert "42" not in prompt or "Fattura 42" in prompt
    assert "1280.40" not in prompt or "1280.40 EUR" in prompt


def test_data_extraction_explicit_structure():
    expected = {"expected": {"name": "Mario", "city": "Roma"}}
    prompt = _build("data_extraction", "Mario vive a Roma", expected)
    assert '"name"' in prompt
    assert '"city"' in prompt
    assert '"answer"' in prompt
    assert 'json_expected' not in prompt.lower()


# ============================================================
# RAG tests
# ============================================================
def test_rag_has_answer_absent_rule():
    expected = {"answer_absent": False,
                "answer_facts": ["Aprire bridge entro 15 minuti"],
                "must_cite_context": True}
    prompt = _build("rag_qa", "Quali sono i passi da seguire?", expected,
                    context="PROCEDURA: 1. Aprire bridge entro 15 minuti. 2. Notificare manager.")
    assert "answer_absent" in prompt.lower(), "Must mention answer_absent behavior"
    assert "Contesto" in prompt


def test_rag_no_expected_facts_in_prompt():
    expected = {"answer_absent": False,
                "answer_facts": ["Aprire bridge entro 15 minuti", "Notificare incident manager"]}
    prompt = _build("rag_qa", "Quali sono i passi?", expected,
                    context="PROCEDURA: 1. Aprire bridge. 2. Notificare manager.")
    assert "Aprire bridge entro 15 minuti" not in prompt, "Expected facts must NOT be in prompt"


# ============================================================
# Summarization tests
# ============================================================
def test_summarization_has_word_limit():
    expected = {"max_words": 180, "format": "bullet_list"}
    prompt = _build("summarization", "Lungo testo da riassumere...", expected)
    assert "180" in prompt, "Must include word limit"
    assert "bullet_list" in prompt.lower() or "puntato" in prompt.lower(), "Must include format constraint"


def test_summarization_explicit_structure():
    expected = {"max_words": 100}
    prompt = _build("summarization", "Testo da riassumere", expected)
    assert '"summary"' in prompt, "Must have explicit summary field in answer"


# ============================================================
# Code analysis tests
# ============================================================
def test_code_analysis_has_severity_scale():
    prompt = _build("code_analysis", "def f():\n    return 1/0")
    assert "severity" in prompt.lower()
    assert "low" in prompt.lower() or "medium" in prompt.lower() or "high" in prompt.lower()


def test_code_analysis_explicit_structure():
    prompt = _build("code_analysis", "def f(): return 1/0")
    assert '"findings"' in prompt
    assert '"type"' in prompt


# ============================================================
# Code documentation tests
# ============================================================
def test_code_documentation_has_style():
    expected = {"style": "docstring_google", "language": "it"}
    prompt = _build("code_documentation", "def validate(x): return True", expected)
    assert "docstring_google" in prompt.lower() or "Stile" in prompt


def test_code_documentation_explicit_structure():
    prompt = _build("code_documentation", "def f(): pass")
    assert '"parameters"' in prompt
    assert '"returns"' in prompt


# ============================================================
# Refactoring tests
# ============================================================
def test_refactoring_has_constraints():
    expected = {"constraints": ["non cambiare signature", "non aggiungere dipendenze"],
                "target": "ridurre duplicazione"}
    prompt = _build("refactoring", "def f(x): return x*2", expected)
    assert "signature" in prompt.lower()


def test_refactoring_no_behavior_change():
    prompt = _build("refactoring", "def f(x): return x")
    assert "comportamento" in prompt.lower() or "preserved" in prompt.lower()


# ============================================================
# Image description tests
# ============================================================
def test_image_description_explicit_structure():
    prompt = _build("image_description", "[Immagine: strada con bici]")
    assert '"description"' in prompt
    assert '"objects_detected"' in prompt


def test_image_description_no_hallucination_rule():
    rules = "Descrivi solo oggetti visibili nell'immagine.\nNon indicare oggetti assenti o solo probabili."
    prompt = _build("image_description", "[Immagine: ufficio]", rules=rules)
    assert "assenti" in prompt.lower() or "visibili" in prompt.lower() or "non presenti" in prompt.lower()


# ============================================================
# OCR tests
# ============================================================
def test_ocr_explicit_structure():
    expected = {"expected_fields": {"name": "Mario", "date": "2026-04-15"}}
    rules = "Se un campo non e leggibile o assente, usa null."
    prompt = _build("ocr_extraction", "Cognome: Rossi. Nome: Mario. Data: 15/04/2026", expected, rules=rules)
    assert '"name"' in prompt
    assert '"date"' in prompt
    assert "null" in prompt.lower(), "Must mention null for unreadable fields"


# ============================================================
# STT tests
# ============================================================
def test_stt_explicit_structure():
    prompt = _build("speech_to_text_postprocess", "ok allora emh... deploy oggi")
    assert '"clean_transcript"' in prompt
    assert '"action_items"' in prompt
    assert '"owner"' in prompt


# ============================================================
# Universal: no generic schema placeholders
# ============================================================
def test_no_generic_schema_placeholders():
    for test_type_id in ["classification", "data_extraction", "rag_qa", "summarization",
                          "code_analysis", "code_documentation", "refactoring",
                          "image_description", "ocr_extraction", "speech_to_text_postprocess"]:
        expected = {"label": "helpdesk_password_reset",
                    "allowed_labels": ["helpdesk_password_reset", "other"]} if test_type_id == "classification" else \
                   {"expected": {"name": "", "city": ""}} if test_type_id == "data_extraction" else \
                   {} if test_type_id != "ocr_extraction" else \
                   {"expected_fields": {"name": "Mario", "date": "2026-04-15"}}

        tc = _make_tc(test_type_id, "Test input", expected, "Test description", "Test context")
        tt = _make_tt(test_type_id)
        from app.services.test_runner import _build_prompt as bp
        prompt = bp(tc, tt)
        msg = f"Type {test_type_id}: No generic schema placeholder"
        assert 'classification_expected' not in prompt.lower(), msg
        assert 'json_expected' not in prompt.lower(), msg
        assert 'rag_expected' not in prompt.lower(), msg
        assert 'summary_expected' not in prompt.lower(), msg
        assert 'code_expected' not in prompt.lower(), msg
        assert 'code_doc_expected' not in prompt.lower(), msg
        assert 'refactoring_expected' not in prompt.lower(), msg
        assert 'vision_expected' not in prompt.lower(), msg
        assert 'ocr_expected' not in prompt.lower(), msg
        assert 'stt_expected' not in prompt.lower(), msg


def test_all_types_have_answer_container():
    for test_type_id in PROMPT_TEMPLATES:
        tc = _make_tc(test_type_id, "Test", {"label": "test"}, "Test desc")
        tt = _make_tt(test_type_id)
        from app.services.test_runner import _build_prompt as bp
        prompt = bp(tc, tt)
        assert '"answer"' in prompt, f"Type {test_type_id}: missing answer container"
        assert 'conf' in prompt.lower(), f"Type {test_type_id}: missing confidence field"


def test_none_prompt_has_expected_values():
    test_cases = [
        ("classification", "Classifica: blabla",
         {"label": "secret_label", "allowed_labels": ["secret_label", "other"]}),
        ("data_extraction", "Fattura 42: 1280.40 EUR",
         {"expected": {"invoice_number": "42", "total": 1280.40}}),
        ("rag_qa", "Che passi seguire?",
         {"answer_facts": ["passo segreto 1", "passo segreto 2"]}),
        ("summarization", "Lungo testo",
         {"required_points": ["Punto segreto 1"], "forbidden_points": ["Budget approvato"]}),
    ]
    for tid, inp, exp in test_cases:
        prompt = _build(tid, inp, exp, "Test", "Context")
        if tid == "classification":
            assert "secret_label" not in prompt or prompt.lower().count("secret_label") <= 1
        elif tid == "data_extraction":
            assert "passo segreto" not in prompt.lower()
        elif tid == "summarization":
            assert "Punto segreto 1" not in prompt or "required_points" not in prompt


def test_user_prompt_template_is_used_as_test_case_definition():
    from app.services.test_runner import _build_prompt
    from app.models import TestCase, TestType

    tc = TestCase(
        test_type_id="classification",
        title="Template test",
        description="Classifica",
        input_text="Ticket: problema spedizione",
        expected_output_json=json.dumps({
            "schema": {"label": "string"},
            "expected": {"label": "shipping"},
            "required_fields": ["label"],
            "allowed_labels": ["shipping", "billing"],
        }),
        user_prompt_template='CUSTOM PROMPT\nTipo: {test_type}\nInput: {input_text}\nClassi: {allowed_labels}\nJSON: {"answer": {"label": "classe_scelta"}}',
    )
    tt = TestType(id="classification", label="Classificazione")
    prompt = _build_prompt(tc, tt)
    assert prompt.startswith("CUSTOM PROMPT")
    assert "Ticket: problema spedizione" in prompt
    assert "shipping" in prompt and "billing" in prompt


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
