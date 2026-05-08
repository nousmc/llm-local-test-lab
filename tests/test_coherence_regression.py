import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["APP_SECRET_KEY"] = "test-coherence-key"


def test_code_analysis_allowed_types():
    from app.services.metrics import compute_code_analysis_deterministic_metrics, ALLOWED_FINDING_TYPES

    assert "best_practice" in ALLOWED_FINDING_TYPES
    assert "bug" in ALLOWED_FINDING_TYPES
    assert "security" in ALLOWED_FINDING_TYPES
    assert "performance" in ALLOWED_FINDING_TYPES
    assert "style" not in ALLOWED_FINDING_TYPES

    expected = json.dumps({"expected_findings": [{"type": "bug", "severity": "high"}]})
    actual = json.dumps({"answer": {"findings": [
        {"type": "best_practice", "severity": "medium", "description": "Usare parametri", "location": "line 10"}
    ]}})
    ca = compute_code_analysis_deterministic_metrics(expected, actual)
    assert ca["allowed_type_valid"] == 1.0, f"best_practice should be valid: {ca}"


def test_rag_top_level_citations_empty():
    from app.services.metrics import compute_rag_metrics

    expected = json.dumps({"answer_facts": [], "must_cite_context": False, "answer_absent": True})
    actual_empty = json.dumps({"citations": [], "answer": {"answer_text": "", "citations_used": [], "answer_absent": True}})
    rag = compute_rag_metrics(expected, actual_empty, "")
    assert rag["top_level_citations_present"] == 0.0, f"Empty list should be 0.0: {rag}"

    actual_space = json.dumps({"citations": [""], "answer": {"answer_text": "", "citations_used": [], "answer_absent": True}})
    rag2 = compute_rag_metrics(expected, actual_space, "")
    assert rag2["top_level_citations_present"] == 0.0, f"Whitespace-only should be 0.0"

    actual_ok = json.dumps({"citations": ["testo"], "answer": {"answer_text": "", "citations_used": [], "answer_absent": True}})
    rag3 = compute_rag_metrics(expected, actual_ok, "")
    assert rag3["top_level_citations_present"] == 1.0


def test_rag_exact_citation_not_fuzzy():
    from app.services.metrics import compute_rag_metrics

    expected = json.dumps({"answer_facts": ["Rimborsi entro 14 giorni"], "must_cite_context": True, "answer_absent": False})
    context = "Rimborsi entro 14 giorni su stesso metodo."

    actual_exact = json.dumps({"answer": {"answer_text": "OK", "citations_used": ["Rimborsi entro 14 giorni"], "answer_absent": False}})
    rag = compute_rag_metrics(expected, actual_exact, context)
    assert rag["citation_exact_substring_match"] == 1.0, f"Exact should be 1.0: {rag}"

    actual_fuzzy = json.dumps({"answer": {"answer_text": "OK", "citations_used": ["rimborso metodo originale"], "answer_absent": False}})
    rag2 = compute_rag_metrics(expected, actual_fuzzy, context)
    assert rag2["citation_exact_substring_match"] == 0.0, f"Fuzzy without exact match should be 0.0: {rag2}"


def test_rag_answer_absent_flag_vs_text():
    from app.services.metrics import compute_rag_metrics

    expected = json.dumps({"answer_facts": [], "must_cite_context": False, "answer_absent": True})
    actual = json.dumps({"answer": {
        "answer_text": "Non è presente nel contesto",
        "citations_used": [],
        "answer_absent": False,
    }})

    rag = compute_rag_metrics(expected, actual, "")
    assert rag["answer_absent_flag_match"] == 0.0, f"Flag mismatch: {rag}"
    assert rag["answer_absent_textual_absence_detected"] == 1.0, f"Textual should be 1.0: {rag}"
    assert rag["answer_absent_correctness"] == 0.0, f"Legacy should follow flag: {rag}"


def test_stt_routing_no_image_metrics():
    from app.services.metrics import compute_speech_to_text_postprocess_metrics

    expected = json.dumps({})
    actual = json.dumps({"answer": {
        "clean_transcript": "Ok allora emh dobbiamo fissare la riunione per venerdì.",
        "action_items": [
            {"owner": "Mario", "task": "Fissare riunione", "deadline": "2026-05-10"},
        ],
        "entities_mentioned": [
            {"name": "Mario", "type": "person"},
            {"name": "2026-05-10", "type": "date"},
        ],
    }})

    stt = compute_speech_to_text_postprocess_metrics(expected, actual)
    assert stt["clean_transcript_present"] == 1.0
    assert stt["action_items_is_list"] == 1.0
    assert stt["action_items_schema_valid"] == 1.0
    assert stt["entities_mentioned_is_list"] == 1.0
    assert stt["entities_schema_valid"] == 1.0
    assert stt["owner_null_or_string_valid"] == 1.0
    assert stt["deadline_null_or_string_valid"] == 1.0
    assert stt["filler_terms_remaining_count"] == 1.0

    for key in ["description_word_count", "objects_detected_is_list", "dominant_colors_is_list", "scene_type_present"]:
        assert key not in stt, f"STT should not have {key}"


def test_image_routing_no_stt_metrics():
    from app.services.metrics import compute_image_description_metrics

    expected = json.dumps({})
    actual = json.dumps({"answer": {
        "description": "Ufficio.",
        "objects_detected": ["scrivania"],
        "scene_type": "ufficio",
        "dominant_colors": ["bianco"],
    }})

    img = compute_image_description_metrics(expected, actual)
    for key in ["action_items_schema_valid", "entities_schema_valid", "filler_terms_remaining_count",
                "clean_transcript_present", "entities_mentioned_is_list"]:
        assert key not in img, f"Image should not have {key}"


def test_code_doc_examples_schema_violation():
    from app.services.metrics import compute_code_documentation_metrics, compute_schema_compliance

    expected = json.dumps({"must_include": ["esempio"]})
    actual = json.dumps({"answer": {
        "docstring": "OK",
        "parameters": [],
        "returns": {"type": "str"},
        "raises": [],
        "examples": [{"code": "f()"}],
    }})

    doc = compute_code_documentation_metrics(expected, actual)
    assert doc["examples_schema_violation"] == 1.0, f"Should detect 1 violation: {doc}"

    ok, violations = compute_schema_compliance(actual, {})
    has_examples_violation = any("examples" in v for v in violations)
    if not ok:
        assert has_examples_violation, f"Should have examples violation: {violations}"


def test_heuristic_language_compliance_ignores_code():
    from app.services.metrics import compute_code_analysis_deterministic_metrics

    expected = json.dumps({"expected_findings": [], "language": "it"})
    actual = json.dumps({"answer": {"findings": []}})
    response_text = "È necessario gestire ValueError e TypeError. La funzione deve validare con try-except."

    ca = compute_code_analysis_deterministic_metrics(expected, actual, response_text)
    assert ca["heuristic_language_compliance"] == 1.0, f"IT response should be 1.0: {ca}"


def test_summarization_bullet_vs_paragraph():
    from app.services.metrics import compute_summarization_metrics

    expected = json.dumps({"max_words": 100})
    actual_para = json.dumps({"answer": {
        "summary": "Questo è un riassunto non puntato con frasi continue che descrivono il processo.",
        "key_points": ["Punto 1", "Punto 2"],
    }})
    doc = compute_summarization_metrics(expected, actual_para)
    assert doc["summary_is_bulleted"] == 0.0
    assert doc["key_points_is_list"] == 1.0
    assert doc["task_format_compliance_deterministic"] < 1.0

    actual_bullet = json.dumps({"answer": {
        "summary": "- Primo punto di riassunto\n- Secondo punto della sintesi",
        "key_points": ["Punto 1", "Punto 2"],
    }})
    doc2 = compute_summarization_metrics(expected, actual_bullet)
    assert doc2["summary_is_bulleted"] == 1.0
    assert doc2["task_format_compliance_deterministic"] >= 0.7


def test_stt_scoring_uses_own_metrics():
    from app.services.test_runner import _compute_deterministic_score_for_type

    metrics = [
        {"name": "json_validity", "value": 1.0},
        {"name": "schema_compliance", "value": 1.0},
        {"name": "clean_transcript_present", "value": 1.0},
        {"name": "action_items_schema_valid", "value": 1.0},
        {"name": "entities_schema_valid", "value": 1.0},
        {"name": "filler_terms_remaining_count", "value": 0.0},
        {"name": "prompt_echo_exact_indicator_found", "value": 0.0},
    ]
    score = _compute_deterministic_score_for_type("speech_to_text_postprocess", metrics)
    assert score >= 0.75, f"STT with perfect formal metrics should score >= 0.75, got {score}"


def test_rag_negative_answer_not_absence():
    from app.services.metrics import compute_rag_metrics

    expected = json.dumps({
        "answer_facts": [],
        "must_cite_context": True,
        "answer_absent": False,
    })
    actual = json.dumps({
        "answer": {
            "answer_text": "Il documento non indica alcuna diagnosi.",
            "citations_used": ["Non sono riportate diagnosi o terapie."],
            "answer_absent": False,
        }
    })
    context = "Contesto: orari ambulatorio, recapiti. Non sono riportate diagnosi o terapie."

    rag = compute_rag_metrics(expected, actual, context)
    assert rag["answer_absent_flag_match"] == 1.0, f"Flag should match: {rag}"
    assert rag["answer_absent_correctness"] == 1.0, f"Should be correct: {rag}"
    assert rag["citation_presence"] == 1.0


def test_rag_truly_absent_vs_negative():
    from app.services.metrics import compute_rag_metrics
    from app.services.metrics import _answer_indicates_absence, _answer_indicates_negative

    assert _answer_indicates_negative("Il documento non indica alcuna diagnosi.")
    assert not _answer_indicates_absence("Il documento non indica alcuna diagnosi.")
    assert not _answer_indicates_absence("Non sono riportate diagnosi o terapie")
    assert _answer_indicates_negative("Non sono riportate diagnosi o terapie")

    assert _answer_indicates_absence("Il contesto non specifica la diagnosi del paziente")
    assert not _answer_indicates_negative("Il contesto non specifica la diagnosi del paziente")


def test_rag_context_has_info_answer_not_absent():
    from app.services.metrics import compute_rag_metrics

    expected = json.dumps({
        "answer_facts": ["Diagnosi: bronchite"],
        "must_cite_context": True,
        "answer_absent": False,
    })
    actual = json.dumps({
        "answer": {
            "answer_text": "La diagnosi indicata è bronchite.",
            "citations_used": ["Diagnosi: bronchite"],
            "answer_absent": False,
        }
    })
    context = "Paziente con tosse. Diagnosi: bronchite. Terapia: antibiotico."

    rag = compute_rag_metrics(expected, actual, context)
    assert rag["answer_absent_flag_match"] == 1.0
    assert rag["answer_absent_correctness"] == 1.0


def test_rag_truly_absent_should_be_true():
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
    context = "Contesto con solo orari e recapiti."

    rag = compute_rag_metrics(expected, actual, context)
    assert rag["answer_absent_flag_match"] == 1.0
    assert rag["answer_absent_correctness"] == 1.0


def test_accent_normalization_for_citation():
    from app.services.metrics import _exact_normalized_substring

    context = "Contesto informativo: recapiti e modalità di prenotazione."
    citation = "modalita di prenotazione"
    assert _exact_normalized_substring(context, citation), "Accent-normalized citation should match"

    citation_no_accent = "recapiti e modalita"
    assert _exact_normalized_substring(context, citation_no_accent)


def test_rag_completeness_three_facts():
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
            "answer_text": "I tre passi sono: aprire il bridge entro 15 minuti, notificare l'incident manager e aggiornare gli stakeholder ogni 30 minuti.",
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
    assert rag["answer_absent_correctness"] == 1.0
    assert rag["citation_presence"] == 1.0
    assert rag["citation_exact_substring_match"] == 1.0
    assert rag["citation_exactness"] == 1.0


def test_rag_completeness_partial_one_fact():
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
            "answer_text": "Il primo passo è aprire il bridge entro 15 minuti.",
            "citations_used": ["1. Aprire il bridge entro 15 minuti dalla rilevazione"],
            "answer_absent": False,
        }
    })
    context = """1. Aprire il bridge entro 15 minuti dalla rilevazione
2. Notificare l'incident manager di turno via telefono
3. Aggiornare gli stakeholder ogni 30 minuti fino a risoluzione"""

    rag = compute_rag_metrics(expected, actual, context)
    assert rag["answer_absent_correctness"] == 1.0
    assert rag["citation_presence"] == 1.0


def run_all():
    tests = [
        ("code_analysis_allowed_types", test_code_analysis_allowed_types),
        ("rag_top_level_citations_empty", test_rag_top_level_citations_empty),
        ("rag_exact_citation_not_fuzzy", test_rag_exact_citation_not_fuzzy),
        ("rag_answer_absent_flag_vs_text", test_rag_answer_absent_flag_vs_text),
        ("stt_routing_no_image_metrics", test_stt_routing_no_image_metrics),
        ("image_routing_no_stt_metrics", test_image_routing_no_stt_metrics),
        ("code_doc_examples_schema_violation", test_code_doc_examples_schema_violation),
        ("heuristic_language_compliance", test_heuristic_language_compliance_ignores_code),
        ("summarization_bullet_vs_paragraph", test_summarization_bullet_vs_paragraph),
        ("stt_scoring_uses_own_metrics", test_stt_scoring_uses_own_metrics),
        ("rag_negative_answer_not_absence", test_rag_negative_answer_not_absence),
        ("rag_truly_absent_vs_negative", test_rag_truly_absent_vs_negative),
        ("rag_context_has_info_not_absent", test_rag_context_has_info_answer_not_absent),
        ("rag_truly_absent_should_be_true", test_rag_truly_absent_should_be_true),
        ("accent_normalization_for_citation", test_accent_normalization_for_citation),
        ("rag_completeness_three_facts", test_rag_completeness_three_facts),
        ("rag_completeness_partial_one_fact", test_rag_completeness_partial_one_fact),
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
