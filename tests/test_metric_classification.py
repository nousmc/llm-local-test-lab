import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["APP_SECRET_KEY"] = "test-metrics-classification-key"


def test_summary_complete_not_bulleted():
    from app.services.metrics import compute_summarization_metrics

    expected = json.dumps({
        "required_points": ["Aprire ticket", "Assegnare operatore", "Verificare risoluzione"],
        "max_words": 200,
    })
    actual = json.dumps({
        "answer": {
            "summary": "Il processo inizia aprendo un ticket di supporto. Successivamente si assegna un operatore qualificato. Infine si verifica la risoluzione del problema.",
            "key_points": [
                "Aprire un ticket di supporto",
                "Assegnare un operatore qualificato",
                "Verificare la risoluzione del problema",
            ],
        }
    })

    doc = compute_summarization_metrics(expected, actual)

    assert doc["max_words_respected"] == 1.0, f"words: {doc['summary_word_count']}"
    assert doc["summary_is_bulleted"] == 0.0, "Should not be bulleted"
    assert doc["key_points_is_list"] == 1.0
    assert doc["key_points_count"] == 3.0


def test_classification_label_wrong_but_json_perfect():
    from app.services.metrics import compute_field_accuracy, check_json_validity
    from app.services.metrics import compute_schema_compliance

    expected = json.dumps({"expected": {"label": "order_status"}, "required_fields": ["label"]})
    actual = json.dumps({
        "answer": {"label": "technical_support"},
        "confidence": 0.9,
        "missing_information": [],
        "assumptions": [],
        "citations": [],
        "warnings": [],
    })

    assert check_json_validity(actual), "JSON should be valid"
    schema_ok, _ = compute_schema_compliance(actual, {"label": "string"})
    assert schema_ok, "Schema should be compliant"

    result = compute_field_accuracy(expected, actual, required_fields=["label"])
    assert result["field_accuracy"] == 0.0, f"Wrong label should give 0 accuracy: {result}"


def test_classification_label_correct_plus_invalid_missing_information():
    from app.services.metrics import compute_field_accuracy, check_json_validity
    from app.services.metrics import _check_top_level_wrapper

    expected = json.dumps({"expected": {"label": "order_status"}, "required_fields": ["label"]})
    actual = json.dumps({
        "answer": {
            "label": "order_status",
            "missing_information": ["Dati cliente non trovati"],
        },
        "confidence": 0.9,
        "missing_information": [],
    })

    assert check_json_validity(actual), "JSON should be valid"
    result = compute_field_accuracy(expected, actual, required_fields=["label"])
    assert result["field_accuracy"] == 1.0, "Correct label should give 1.0 accuracy"

    wrapper_ok, issues = _check_top_level_wrapper(actual)
    assert not wrapper_ok, f"Leaked technical field inside answer should be flagged: {issues}"
    assert "missing_information" in str(issues)

    import json as _json
    data = _json.loads(actual)
    answer = data.get("answer", {})
    if isinstance(answer, dict):
        leaked_fields = [k for k in answer
                         if k in {"confidence", "missing_information", "assumptions", "citations", "warnings"}]
        assert len(leaked_fields) == 1, f"Should detect 1 leaked field in answer, got {leaked_fields}"
        assert "missing_information" in leaked_fields


def test_rag_placeholder_citation_no_semantic_support():
    from app.services.metrics import compute_rag_metrics

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
            "answer_text": "Primo: aprire il bridge entro 15 minuti. Secondo: notificare l'incident manager.",
            "citations_used": ["Sezione 3.1 - Procedure"],
            "answer_absent": False,
        }
    })
    context = """SEZIONE 3 - GESTIONE INCIDENTI
Sezione 3.1 - Procedure
1. Aprire il bridge entro 15 minuti
2. Notificare incident manager
3. Aggiornare stakeholder"""

    rag = compute_rag_metrics(expected, actual, context)

    assert rag["citation_presence"] == 1.0
    assert rag["citation_exact_substring_match"] >= 0.0


def test_rag_wrong_answer_with_present_citation():
    from app.services.metrics import compute_rag_metrics

    expected = json.dumps({
        "answer_facts": ["verifica entro 3 giorni", "riaccredito entro 7 giorni"],
        "must_cite_context": True,
        "answer_absent": False,
    })
    actual = json.dumps({
        "answer": {
            "answer_text": "I rimborsi vengono verificati in 2 giorni lavorativi.",
            "citations_used": ["I rimborsi pagati con carta vengono verificati entro 3 giorni e riaccreditati entro 7 giorni"],
            "answer_absent": False,
        }
    })
    context = "I rimborsi pagati con carta vengono verificati entro 3 giorni e riaccreditati entro 7 giorni"

    rag = compute_rag_metrics(expected, actual, context)

    assert rag["citation_exact_substring_match"] >= 0.0
    assert rag["citation_presence"] == 1.0


def test_code_doc_hallucinated_params_regression():
    from app.services.metrics import compute_code_documentation_metrics

    expected = json.dumps({
        "must_include": ["parametri", "valore restituito", "eccezioni"],
        "style": "docstring_google",
        "expected_parameters": [
            {"name": "email", "type": "str"},
        ],
        "expected_return_type": "tuple[bool, str]",
        "expected_exceptions": [
            {"type": "TypeError", "condition": "email non e una stringa"},
            {"type": "ValueError", "condition": "email vuota o solo spazi"},
        ],
    })
    actual = json.dumps({
        "answer": {
            "docstring": "Valida un indirizzo email verificandone formato e dominio.",
            "parameters": [
                {"name": "email", "type": "str", "description": "Indirizzo email da validare"},
                {"name": "tipo", "type": "str", "description": "Tipo di validazione"},
                {"name": "descrizione", "type": "str", "description": "Descrizione"},
            ],
            "returns": {
                "type": "tuple",
                "description": "Tupla con booleano e messaggio stringa di errore",
            },
            "raises": [
                {"type": "TypeError", "description": "Se email non e stringa"},
                {"type": "ValueError", "description": "Se email vuota"},
            ],
            "examples": [],
        }
    })

    doc = compute_code_documentation_metrics(expected, actual)
    assert doc["hallucinated_parameters_count"] == 2.0
    assert doc["hallucinated_exception_count"] == 0.0
    assert doc["documented_parameters_accuracy"] == 1.0
    assert doc["missing_documented_parameters_count"] == 0.0
    assert doc["documentation_structure"] == 1.0


def test_rag_answer_absent_does_not_auto_set_citations():
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
    assert rag["answer_absent_correctness"] == 1.0
    assert rag["citation_presence"] == 0.0
    assert rag["citation_exact_substring_match"] == 0.0


def test_summarization_deterministic_format_compliance():
    from app.services.metrics import compute_summarization_metrics

    expected = json.dumps({
        "required_points": ["Punto 1", "Punto 2"],
        "max_words": 100,
    })
    actual = json.dumps({
        "answer": {
            "summary": "- Primo punto importante da riassumere\n- Secondo punto con dettagli",
            "key_points": ["Punto 1", "Punto 2"],
        }
    })

    doc = compute_summarization_metrics(expected, actual)
    assert doc["max_words_respected"] == 1.0
    assert doc["summary_is_bulleted"] == 1.0
    assert doc["key_points_is_list"] == 1.0
    assert doc["key_points_count"] == 2.0
    assert doc["task_format_compliance_deterministic"] >= 0.7


def test_lexical_similarity_renamed_from_semantic():
    from app.services.metrics import compute_lexical_similarity, compute_semantic_similarity

    r1 = compute_lexical_similarity("Ciao mondo", "Ciao mondo grande")
    r2 = compute_semantic_similarity("Ciao mondo", "Ciao mondo grande")
    assert r1 == r2, "legacy alias must return same value"
    assert 0.0 < r1 < 1.0


def test_metric_registry_coverage():
    from app.services.metric_registry import METRICS_REGISTRY, get_evaluation_mode, get_metric_meta

    assert get_evaluation_mode("json_validity") == "deterministic"
    assert get_evaluation_mode("heuristic_answer_facts_coverage") == "heuristic"
    assert get_evaluation_mode("llm_unsupported_claim_rate") == "llm"

    meta = get_metric_meta("semantic_similarity")
    assert meta is not None, "legacy alias should resolve to metric meta"
    assert meta["evaluation_mode"] == "heuristic"

    meta = get_metric_meta("answer_facts_coverage")
    assert meta is not None
    assert meta["evaluation_mode"] == "heuristic"


def run_all():
    tests = [
        ("summary_complete_not_bulleted", test_summary_complete_not_bulleted),
        ("classification_label_wrong_json_perfect", test_classification_label_wrong_but_json_perfect),
        ("classification_label_correct_invalid_missing_info", test_classification_label_correct_plus_invalid_missing_information),
        ("rag_placeholder_citation_no_semantic_support", test_rag_placeholder_citation_no_semantic_support),
        ("rag_wrong_answer_with_present_citation", test_rag_wrong_answer_with_present_citation),
        ("code_doc_hallucinated_params_regression", test_code_doc_hallucinated_params_regression),
        ("rag_answer_absent_does_not_auto_set_citations", test_rag_answer_absent_does_not_auto_set_citations),
        ("summarization_deterministic_format_compliance", test_summarization_deterministic_format_compliance),
        ("lexical_similarity_renamed_from_semantic", test_lexical_similarity_renamed_from_semantic),
        ("metric_registry_coverage", test_metric_registry_coverage),
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
