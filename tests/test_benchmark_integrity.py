import sys
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

os.environ["APP_SECRET_KEY"] = "test-key-2026"


def test_prompt_contamination_check():
    from app.services.metrics import check_prompt_contamination

    expected = json.dumps({"expected": {"label": "helpdesk_password_reset"}})
    prompt_clean = "Classifica questo ticket: Utente non puo accedere"
    prompt_dirty = "Il risultato atteso e helpdesk_password_reset. Classifica questo ticket"

    contaminated, info = check_prompt_contamination(prompt_clean, expected)
    assert not contaminated, f"Clean prompt marked contaminated: {info}"

    contaminated, info = check_prompt_contamination(prompt_dirty, expected)
    assert contaminated, "Contaminated prompt not detected"


def test_data_extraction_perfect():
    from app.services.metrics import compute_field_accuracy, extract_json_from_text, compute_exact_match, values_equal, check_json_validity

    response = json.dumps({"answer": {"invoice_number": "42", "date": "2026-04-15", "supplier": "ACME SRL", "total": 1280.40, "currency": "EUR"}, "confidence": 1.0, "missing_information": []})
    expected = json.dumps({"expected": {"invoice_number": "42", "date": "2026-04-15", "supplier": "ACME SRL", "total": 1280.40, "currency": "EUR"}, "required_fields": ["invoice_number", "date", "supplier", "total", "currency"]})

    result = compute_field_accuracy(expected, response, required_fields=["invoice_number", "date", "supplier", "total", "currency"])
    assert result["field_accuracy"] == 1.0, f"Expected 1.0, got {result['field_accuracy']}"
    assert len(result["missing_fields"]) == 0, f"Unexpected missing: {result['missing_fields']}"
    assert len(result["hallucinated_fields"]) == 0, f"Unexpected hallucinated: {result['hallucinated_fields']}"
    assert result["correct_fields"] == 5, f"Expected 5 correct, got {result['correct_fields']}"


def test_data_extraction_missing_fields():
    from app.services.metrics import compute_field_accuracy

    response = json.dumps({"answer": {"invoice_number": "42", "date": "2026-04-15", "supplier": "ACME SRL"}, "confidence": 0.8})
    expected = json.dumps({"expected": {"invoice_number": "42", "date": "2026-04-15", "supplier": "ACME SRL", "total": 1280.40, "currency": "EUR"}, "required_fields": ["invoice_number", "date", "supplier", "total", "currency"]})

    result = compute_field_accuracy(expected, response, required_fields=["invoice_number", "date", "supplier", "total", "currency"])
    assert result["field_accuracy"] == 0.6, f"Expected 0.6, got {result['field_accuracy']}"
    assert sorted(result["missing_fields"]) == ["currency", "total"], f"Wrong missing: {result['missing_fields']}"
    assert result["correct_fields"] == 3


def test_data_extraction_extra_fields():
    from app.services.metrics import compute_field_accuracy

    response = json.dumps({"answer": {"invoice_number": "42", "date": "2026-04-15", "supplier": "ACME SRL", "total": 1280.40, "currency": "EUR", "extra_field": "xxx"}, "confidence": 0.9})
    expected = json.dumps({"expected": {"invoice_number": "42", "date": "2026-04-15", "supplier": "ACME SRL", "total": 1280.40, "currency": "EUR"}, "required_fields": ["invoice_number", "date", "supplier", "total", "currency"]})

    result = compute_field_accuracy(expected, response, required_fields=["invoice_number", "date", "supplier", "total", "currency"])
    assert "extra_field" in result["hallucinated_fields"], f"extra_field not flagged: {result['hallucinated_fields']}"
    assert result["field_accuracy"] == 1.0, "All required fields present, accuracy should be 1.0"


def test_technical_fields_not_counted():
    from app.services.metrics import compute_field_accuracy, TECHNICAL_RESPONSE_FIELDS

    assert "confidence" in TECHNICAL_RESPONSE_FIELDS
    assert "answer" in TECHNICAL_RESPONSE_FIELDS
    assert "missing_information" in TECHNICAL_RESPONSE_FIELDS

    response = json.dumps({"answer": {"label": "helpdesk_password_reset"}, "confidence": 0.95, "missing_information": [], "assumptions": [], "citations": [], "warnings": []})
    expected = json.dumps({"expected": {"label": "helpdesk_password_reset"}})

    result = compute_field_accuracy(expected, response, required_fields=["label"])
    assert len(result["hallucinated_fields"]) == 0, f"Technical fields counted as hallucinated: {result['hallucinated_fields']}"
    assert result["field_accuracy"] == 1.0


def test_classification_correct():
    from app.services.metrics import compute_field_accuracy, values_equal, check_json_validity

    response = json.dumps({"answer": {"label": "helpdesk_password_reset"}, "confidence": 0.95})
    expected = json.dumps({"expected": {"label": "helpdesk_password_reset"}})

    assert check_json_validity(response), "Valid JSON not recognized"
    result = compute_field_accuracy(expected, response, required_fields=["label"])
    assert result["field_accuracy"] == 1.0, f"Classification should be 1.0, got {result['field_accuracy']}"


def test_validator_cannot_override_perfect_deterministic():
    from app.services.test_runner import _compute_final_score

    score = _compute_final_score(
        deterministic_score=1.0,
        validator_score=0.2,
        format_score=0.3,
        latency_ms=500,
        max_latency_ms=30000,
        has_invalid_json=False,
        has_schema_violation=False,
        hallucination_detected=False,
        refusal_detected=False,
        error_type=None,
        tokens_per_second=10,
        estimated_cost=0.001,
        test_type_id="data_extraction",
        deterministic_is_perfect=True,
        validator_conflict=True,
    )
    assert score >= 0.70, f"Score should be high with perfect deterministic, got {score}"


def test_structured_deterministic_score_ignores_exact_text_metrics():
    from app.services.test_runner import _compute_deterministic_score_for_type

    metrics = [
        {"name": "json_validity", "value": 1.0},
        {"name": "schema_compliance", "value": 1.0},
        {"name": "exact_match", "value": 0.0},
        {"name": "semantic_similarity", "value": 0.44},
        {"name": "field_accuracy", "value": 1.0},
        {"name": "missing_fields_count", "value": 0.0},
        {"name": "hallucinated_fields_count", "value": 0.0},
        {"name": "incorrect_fields_count", "value": 0.0},
    ]
    score = _compute_deterministic_score_for_type("data_extraction", metrics)
    assert score == 1.0, f"Structured perfect answer should score 1.0, got {score}"


def test_perfect_classification_final_score_is_one_even_with_old_text_metrics():
    from app.services.test_runner import _compute_deterministic_score_for_type, _compute_final_score

    metrics = [
        {"name": "json_validity", "value": 1.0},
        {"name": "schema_compliance", "value": 1.0},
        {"name": "exact_match", "value": 0.0},
        {"name": "semantic_similarity", "value": 0.0915},
        {"name": "field_accuracy", "value": 1.0},
        {"name": "missing_fields_count", "value": 0.0},
        {"name": "hallucinated_fields_count", "value": 0.0},
        {"name": "incorrect_fields_count", "value": 0.0},
    ]
    det = _compute_deterministic_score_for_type("classification", metrics)
    assert det == 1.0
    final = _compute_final_score(
        deterministic_score=det,
        validator_score=1.0,
        format_score=1.0,
        latency_ms=20000,
        max_latency_ms=60000,
        has_invalid_json=False,
        has_schema_violation=False,
        hallucination_detected=False,
        refusal_detected=False,
        error_type=None,
        tokens_per_second=1.0,
        estimated_cost=0.01,
        test_type_id="classification",
        deterministic_is_perfect=True,
        validator_conflict=False,
    )
    assert final == 1.0


def test_rag_semantically_correct_answer_scores_high():
    from app.services.metrics import compute_rag_metrics
    from app.services.test_runner import _compute_deterministic_score_for_type, _compute_final_score

    expected = json.dumps({
        "answer_facts": [
            "Aprire il bridge entro 15 minuti",
            "Notificare incident manager",
            "Aggiornare stakeholder ogni 30 minuti",
        ],
        "must_cite_context": True,
        "answer_absent": False,
    })
    actual = json.dumps({
        "answer": {
            "answer_text": "I primi tre passi sono: aprire il bridge entro 15 minuti, notificare l'incident manager e aggiornare gli stakeholder ogni 30 minuti.",
            "citations_used": [
                "1. Aprire il bridge entro 15 minuti dalla rilevazione",
                "2. Notificare l'incident manager di turno via telefono",
                "3. Aggiornare gli stakeholder ogni 30 minuti fino a risoluzione",
            ],
            "answer_absent": False,
        }
    })
    context = """1. Aprire il bridge entro 15 minuti dalla rilevazione
2. Notificare l'incident manager di turno via telefono
3. Aggiornare gli stakeholder ogni 30 minuti fino a risoluzione"""
    rag = compute_rag_metrics(expected, actual, context)
    metrics = [
        {"name": "json_validity", "value": 1.0},
        {"name": "schema_compliance", "value": 1.0},
        {"name": "answer_absent_correctness", "value": rag["answer_absent_correctness"]},
    ]
    det = _compute_deterministic_score_for_type("rag_qa", metrics)
    assert det >= 0.70
    final = _compute_final_score(
        deterministic_score=det,
        validator_score=1.0,
        format_score=1.0,
        latency_ms=20000,
        max_latency_ms=60000,
        has_invalid_json=False,
        has_schema_violation=False,
        hallucination_detected=False,
        refusal_detected=False,
        error_type=None,
        tokens_per_second=1.0,
        estimated_cost=0.01,
        test_type_id="rag_qa",
        deterministic_is_perfect=True,
        validator_conflict=False,
    )
    assert final >= 0.80


def test_rag_absent_answer_text_scores_high_even_if_flag_false_and_validator_zero():
    from app.services.metrics import compute_rag_metrics
    from app.services.test_runner import _compute_deterministic_score_for_type, _compute_final_score

    expected = json.dumps({
        "answer_facts": [],
        "must_cite_context": True,
        "answer_absent": True,
    })
    actual = json.dumps({
        "answer": {
            "answer_text": "Il budget annuale allocato per la formazione del personale non è specificato nel contesto.",
            "citations_used": ["Il contesto non menziona un budget annuale allocato per la formazione del personale."],
            "answer_absent": False,
        },
        "confidence": 1.0,
    })
    context = "Corsi erogati nel Q1: Python base. Totale ore formazione Q1: 72 ore. Nessun budget indicato."
    rag = compute_rag_metrics(expected, actual, context)
    assert rag["answer_absent_flag_match"] == 0.0
    assert rag["answer_absent_textual_absence_detected"] == 1.0

    metrics = [
        {"name": "json_validity", "value": 1.0},
        {"name": "schema_compliance", "value": 1.0},
        {"name": "answer_absent_correctness", "value": rag["answer_absent_correctness"]},
    ]
    det = _compute_deterministic_score_for_type("rag_qa", metrics)
    final = _compute_final_score(
        deterministic_score=det,
        validator_score=0.0,
        format_score=0.0,
        latency_ms=20000,
        max_latency_ms=60000,
        has_invalid_json=False,
        has_schema_violation=False,
        hallucination_detected=False,
        refusal_detected=False,
        error_type=None,
        tokens_per_second=1.0,
        estimated_cost=0.01,
        test_type_id="rag_qa",
        deterministic_is_perfect=True,
        validator_conflict=True,
    )
    assert final >= 0.75


def test_code_documentation_correct_response_scores_high_even_if_validator_zero():
    from app.services.metrics import compute_code_documentation_metrics
    from app.services.test_runner import _compute_deterministic_score_for_type, _compute_final_score

    expected = json.dumps({
        "must_include": ["parametri", "valore restituito", "eccezioni", "esempio"],
        "style": "docstring_google",
        "language": "it",
    })
    actual = json.dumps({
        "answer": {
            "docstring": "API per elencare gli ordini con paginazione e filtri.",
            "parameters": [
                {"name": "page", "type": "int", "description": "Numero pagina"},
                {"name": "limit", "type": "int", "description": "Limite pagina"},
                {"name": "status", "type": "str", "description": "Filtro stato"},
                {"name": "sort_by", "type": "str", "description": "Campo ordinamento"},
                {"name": "order", "type": "str", "description": "Direzione ordinamento"},
            ],
            "returns": {"type": "dict", "description": "Ordini, page, limit e total"},
            "raises": [],
            "examples": [],
        },
        "confidence": 1.0,
    })
    doc = compute_code_documentation_metrics(expected, actual)
    assert doc["documentation_structure"] == 1.0
    assert doc["heuristic_documentation_completeness"] == 1.0
    assert doc["style_compliance"] <= 1.0

    metrics = [
        {"name": "json_validity", "value": 1.0},
        {"name": "schema_compliance", "value": 1.0},
        {"name": "documentation_structure", "value": doc["documentation_structure"]},
        {"name": "heuristic_documentation_completeness", "value": doc["heuristic_documentation_completeness"]},
        {"name": "style_compliance", "value": doc["style_compliance"]},
        {"name": "missing_doc_sections_count", "value": doc["missing_doc_sections_count"]},
        {"name": "hallucinated_parameters_count", "value": doc["hallucinated_parameters_count"]},
        {"name": "missing_documented_parameters_count", "value": doc["missing_documented_parameters_count"]},
        {"name": "documented_parameters_accuracy", "value": doc["documented_parameters_accuracy"]},
        {"name": "field_accuracy", "value": 0.0},
        {"name": "hallucinated_fields_count", "value": 5.0},
    ]
    det = _compute_deterministic_score_for_type("code_documentation", metrics)
    assert det == 1.0
    final = _compute_final_score(
        deterministic_score=det,
        validator_score=0.0,
        format_score=0.0,
        latency_ms=20000,
        max_latency_ms=60000,
        has_invalid_json=False,
        has_schema_violation=False,
        hallucination_detected=False,
        refusal_detected=False,
        error_type=None,
        tokens_per_second=1.0,
        estimated_cost=0.01,
        test_type_id="code_documentation",
        deterministic_is_perfect=True,
        validator_conflict=True,
    )
    assert final >= 0.75


def test_code_doc_hallucinated_params_reduce_score():
    from app.services.metrics import compute_code_documentation_metrics
    from app.services.test_runner import _compute_deterministic_score_for_type

    expected = json.dumps({
        "must_include": ["parametri", "valore restituito", "eccezioni", "esempio"],
        "style": "docstring_google",
        "expected_parameters": [
            {"name": "email", "type": "str"},
        ],
        "expected_return_type": "tuple[bool, str]",
        "expected_exceptions": [
            {"type": "TypeError", "condition": "email non è una stringa"},
            {"type": "ValueError", "condition": "email vuota o solo spazi"},
        ],
    })
    actual = json.dumps({
        "answer": {
            "docstring": "Valida un indirizzo email verificandone formato e dominio.",
            "parameters": [
                {"name": "email", "type": "str", "description": "Indirizzo email da validare"},
                {"name": "tipo", "type": "str", "description": "Tipo di validazione"},
                {"name": "descrizione", "type": "str", "description": "Descrizione aggiuntiva"},
            ],
            "returns": {
                "type": "tuple",
                "description": "Una tupla con una stringa e una stringa che indicano stato e messaggio",
            },
            "raises": [
                {"type": "ValueError", "description": "Se l'email non è valida"},
            ],
            "examples": [],
        }
    })

    doc = compute_code_documentation_metrics(expected, actual)

    assert doc["missing_doc_sections_count"] == 0.0
    assert doc["hallucinated_parameters_count"] == 2.0, f"Expected 2 hallucinated params, got {doc['hallucinated_parameters_count']}"
    assert doc["missing_documented_parameters_count"] == 0.0
    assert doc["documented_parameters_accuracy"] == 1.0
    assert doc["documentation_structure"] == 1.0
    assert doc["heuristic_documentation_completeness"] < 1.0, f"Completeness should be < 1.0: {doc['documentation_completeness']}"
    assert doc["style_compliance"] < 1.0, f"Style should be < 1.0: {doc['style_compliance']}"

    metrics = [
        {"name": "json_validity", "value": 1.0},
        {"name": "schema_compliance", "value": 1.0},
        {"name": "documentation_structure", "value": doc["documentation_structure"]},
        {"name": "heuristic_documentation_completeness", "value": doc["heuristic_documentation_completeness"]},
        {"name": "style_compliance", "value": doc["style_compliance"]},
        {"name": "missing_doc_sections_count", "value": doc["missing_doc_sections_count"]},
        {"name": "hallucinated_parameters_count", "value": doc["hallucinated_parameters_count"]},
        {"name": "missing_documented_parameters_count", "value": doc["missing_documented_parameters_count"]},
        {"name": "documented_parameters_accuracy", "value": doc["documented_parameters_accuracy"]},
    ]
    det = _compute_deterministic_score_for_type("code_documentation", metrics)
    assert det < 1.0, f"Score should be < 1.0, got {det}"
    assert det > 0.55, f"Score should be > 0.55 (some correct info), got {det}"


def test_code_doc_wrong_return_type_reduces_completeness():
    from app.services.metrics import compute_code_documentation_metrics

    expected = json.dumps({
        "must_include": ["parametri", "valore restituito", "eccezioni"],
        "style": "docstring_google",
        "expected_parameters": [{"name": "email", "type": "str"}],
        "expected_return_type": "tuple[bool, str]",
    })
    actual = json.dumps({
        "answer": {
            "docstring": "Valida un indirizzo email.",
            "parameters": [
                {"name": "email", "type": "str", "description": "Indirizzo email da validare"},
            ],
            "returns": {
                "type": "tuple",
                "description": "Una tupla con una stringa e una stringa che indicano stato e messaggio",
            },
            "raises": [],
            "examples": [],
        }
    })

    doc = compute_code_documentation_metrics(expected, actual)
    assert doc["heuristic_documentation_completeness"] < 1.0, f"Got {doc['documentation_completeness']}"
    assert doc["style_compliance"] < 1.0, f"Got {doc['style_compliance']}"


def test_invalid_json_cannot_pass():
    from app.services.test_runner import _compute_final_score

    score = _compute_final_score(
        deterministic_score=0.5,
        validator_score=0.6,
        format_score=0.8,
        latency_ms=1000,
        max_latency_ms=60000,
        has_invalid_json=True,
        has_schema_violation=False,
        hallucination_detected=False,
        refusal_detected=False,
        error_type=None,
        tokens_per_second=10,
        estimated_cost=0.001,
        test_type_id="code_documentation",
        deterministic_is_perfect=False,
        validator_conflict=False,
    )
    assert score <= 0.30, f"Score with invalid JSON should be <= 0.30, got {score}"


def test_schema_violation_caps_score():
    from app.services.test_runner import _compute_final_score

    score = _compute_final_score(
        deterministic_score=0.9,
        validator_score=0.9,
        format_score=0.9,
        latency_ms=1000,
        max_latency_ms=60000,
        has_invalid_json=False,
        has_schema_violation=True,
        hallucination_detected=False,
        refusal_detected=False,
        error_type=None,
        tokens_per_second=10,
        estimated_cost=0.001,
        test_type_id="code_documentation",
        deterministic_is_perfect=False,
        validator_conflict=False,
    )
    assert score <= 0.50, f"Score with schema violation should be <= 0.50, got {score}"


def test_examples_objects_not_strings_schema_violation():
    from app.services.metrics import compute_code_documentation_metrics

    expected = json.dumps({
        "must_include": ["parametri", "esempio"],
        "style": "docstring_google",
        "expected_parameters": [{"name": "email", "type": "str"}],
    })
    actual = json.dumps({
        "answer": {
            "docstring": "Valida un indirizzo email.",
            "parameters": [
                {"name": "email", "type": "str", "description": "Indirizzo email da validare"},
            ],
            "returns": {"type": "tuple", "description": "bool e messaggio"},
            "raises": [],
            "examples": [
                {"title": "Esempio 1", "code": "validate_email(\"test@example.com\")"},
                {"title": "Esempio 2", "code": "validate_email(\"\")"},
            ],
        }
    })

    doc = compute_code_documentation_metrics(expected, actual)
    assert doc["examples_schema_violation"] == 2.0, f"Expected 2 schema violations, got {doc['examples_schema_violation']}"


def test_raises_hallucinated_when_none_expected():
    from app.services.metrics import compute_code_documentation_metrics

    expected = json.dumps({
        "must_include": ["parametri", "valore restituito", "eccezioni"],
        "style": "docstring_google",
        "expected_parameters": [{"name": "email", "type": "str"}],
        "expected_exceptions": [],
    })
    actual = json.dumps({
        "answer": {
            "docstring": "Valida un indirizzo email.",
            "parameters": [
                {"name": "email", "type": "str", "description": "Indirizzo email"},
            ],
            "returns": {"type": "bool", "description": "True se valida, False altrimenti"},
            "raises": [
                {"type": "ValueError", "description": "Se l'email non rispetta il formato"},
            ],
            "examples": [],
        }
    })

    doc = compute_code_documentation_metrics(expected, actual)
    assert doc["hallucinated_exception_count"] == 1.0, f"Expected 1 hallucinated exception, got {doc['hallucinated_exception_count']}"


def test_top_level_wrapper_schema_check():
    from app.services.metrics import _check_top_level_wrapper

    ok = json.dumps({
        "answer": {"label": "test"},
        "confidence": 0.9,
        "missing_information": [],
    })
    valid, issues = _check_top_level_wrapper(ok)
    assert valid, f"Valid wrapper flagged: {issues}"

    bad = json.dumps({
        "answer": {
            "label": "test",
            "confidence": 0.9,
            "missing_information": [],
        },
    })
    valid, issues = _check_top_level_wrapper(bad)
    assert not valid, f"Invalid wrapper should be flagged"


def test_schema_compliance_with_wrapper_check():
    from app.services.metrics import compute_schema_compliance

    ok = json.dumps({
        "answer": {"label": "test"},
        "confidence": 0.9,
    })
    ok, violations = compute_schema_compliance(ok, {"label": "string"})
    assert ok, f"Valid wrapper flagged: {violations}"

    bad = json.dumps({
        "answer": {"label": "test", "confidence": 0.9},
    })
    ok, violations = compute_schema_compliance(bad, {"label": "string"})
    assert not ok, f"Invalid wrapper not flagged"


def test_normalization():
    from app.services.metrics import values_equal

    assert values_equal("ACME SRL", "acme srl")
    assert values_equal("  hello  ", "hello")
    assert values_equal(1280.40, 1280.4)
    assert values_equal(42, "42")
    assert values_equal("2026-04-15", "15/04/2026")
    assert values_equal(None, None)
    assert values_equal("", "")
    assert not values_equal("ACME SRL", "ACME SpA")


def test_rag_deterministic_citation_metrics():
    from app.services.metrics import compute_rag_metrics

    expected = json.dumps({
        "answer_facts": [
            "Aprire il bridge entro 15 minuti",
        ],
        "must_cite_context": True,
        "answer_absent": False,
    })
    actual = json.dumps({
        "answer": {
            "answer_text": "Aprire il bridge entro 15 minuti dalla rilevazione.",
            "citations_used": [
                "1. Aprire il bridge entro 15 minuti dalla rilevazione",
            ],
            "answer_absent": False,
        }
    })
    context = """1. Aprire il bridge entro 15 minuti dalla rilevazione
2. Notificare l'incident manager di turno via telefono"""

    rag = compute_rag_metrics(expected, actual, context)
    assert rag["citation_presence"] == 1.0
    assert rag["citation_exact_substring_match"] >= 0.0
    assert rag["answer_absent_correctness"] == 1.0


def test_rag_citation_presence_when_absent():
    from app.services.metrics import compute_rag_metrics

    expected = json.dumps({
        "answer_facts": [],
        "must_cite_context": False,
        "answer_absent": True,
    })
    actual = json.dumps({
        "answer": {
            "answer_text": "",
            "citations_used": [],
            "answer_absent": True,
        }
    })
    context = "Documento con informazioni varie."
    rag = compute_rag_metrics(expected, actual, context)
    assert rag["citation_presence"] == 0.0
    assert rag["citations_nonempty_count"] == 0.0


def test_prompt_build_no_expected():
    from app.services.test_runner import _build_prompt
    from app.models import TestCase, TestType

    tc = TestCase(
        test_type_id="data_extraction",
        title="Test",
        input_text="Invoice #42 from ACME SRL: 1280.40 EUR",
        expected_output_json=json.dumps({
            "expected": {"invoice_number": "42", "supplier": "ACME SRL", "total": 1280.40},
            "required_fields": ["invoice_number", "supplier", "total"]
        }),
    )
    tt = TestType(id="data_extraction", label="Estrazione dati", expected_schema="json_expected")

    prompt = _build_prompt(tc, tt)
    assert "ACME SRL" not in prompt.lower(), "Expected value ACME SRL leaked into prompt!"
    assert "helpdesk_password_reset" not in prompt.lower()
    assert "42" not in prompt or "Invoice #42" in prompt, "Invoice #42 is input, not expected value leak"


def test_pass_fields_always_initialized():
    from app.services.test_runner import _compute_final_score

    score = _compute_final_score(
        deterministic_score=0.9,
        validator_score=0.9,
        format_score=0.9,
        latency_ms=1000,
        max_latency_ms=60000,
        has_invalid_json=False,
        has_schema_violation=False,
        hallucination_detected=False,
        refusal_detected=False,
        error_type=None,
        tokens_per_second=10,
        estimated_cost=0.001,
        test_type_id="rag_qa",
        deterministic_is_perfect=True,
        validator_conflict=False,
    )
    assert score >= 0.80, f"RAG with good deterministic+validator should score high, got {score}"


def run_all():
    tests = [
        ("prompt_contamination_check", test_prompt_contamination_check),
        ("data_extraction_perfect", test_data_extraction_perfect),
        ("data_extraction_missing_fields", test_data_extraction_missing_fields),
        ("data_extraction_extra_fields", test_data_extraction_extra_fields),
        ("technical_fields_not_counted", test_technical_fields_not_counted),
        ("classification_correct", test_classification_correct),
        ("validator_override_protection", test_validator_cannot_override_perfect_deterministic),
        ("normalization", test_normalization),
        ("rag_deterministic_citation_metrics", test_rag_deterministic_citation_metrics),
        ("rag_citation_presence_when_absent", test_rag_citation_presence_when_absent),
        ("prompt_build_no_expected", test_prompt_build_no_expected),
        ("pass_fields_always_initialized", test_pass_fields_always_initialized),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 40}")
    print(f"Results: {passed}/{len(tests)} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
