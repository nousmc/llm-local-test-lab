import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["APP_SECRET_KEY"] = "test-contextual-insight-key"


def test_contextual_insight_complete_good():
    from app.services.metrics import compute_contextual_insight_metrics

    expected = json.dumps({
        "expected_insight_count": {"min": 3, "max": 6},
        "must_include_themes": ["produttore", "rimborso"],
        "must_avoid_themes": ["penale"],
        "depth": "legale",
    })
    actual = json.dumps({
        "answer": {
            "insights": [
                "Azione contro il produttore ex D.Lgs. 206/2005 per prodotto difettoso",
                "Richiesta rimborso a MarketplaceX se non ha comunicato identita venditore",
                "Conservare fattura e foto del danno come prova",
            ],
            "references_to_context": [
                "Turno 1: cliente descrive acquisto e danno",
                "Turno 3: cliente conferma fattura e venditore privato",
            ],
            "follow_up_questions": [
                "La stampante aveva marcatura CE?",
                "Ci sono altri acquirenti con lo stesso problema?",
            ],
            "depth": "legale",
        }
    })

    ci = compute_contextual_insight_metrics(expected, actual)
    assert ci["insights_is_list"] == 1.0
    assert ci["insight_count_in_range"] == 1.0
    assert ci["insight_count"] == 3.0
    assert ci["references_to_context_is_list"] == 1.0
    assert ci["references_to_context_count"] == 2.0
    assert ci["follow_up_present"] == 1.0
    assert ci["depth_valid"] == 1.0
    assert ci["must_include_coverage"] == 1.0
    assert ci["must_avoid_violation"] == 0.0


def test_contextual_insight_avoid_theme_detected():
    from app.services.metrics import compute_contextual_insight_metrics

    expected = json.dumps({
        "must_include_themes": ["qualita"],
        "must_avoid_themes": ["penale", "dolo"],
    })
    actual = json.dumps({
        "answer": {
            "insights": [
                "Denuncia penale per dolo del venditore",
                "Migliorare controllo qualita",
            ],
            "references_to_context": ["Turno 1"],
            "follow_up_questions": ["ok"],
            "depth": "legale",
        }
    })

    ci = compute_contextual_insight_metrics(expected, actual)
    assert ci["must_avoid_violation"] >= 1.0


def test_contextual_insight_scoring():
    from app.services.test_runner import _compute_deterministic_score_for_type

    metrics = [
        {"name": "json_validity", "value": 1.0},
        {"name": "schema_compliance", "value": 1.0},
        {"name": "insight_count_in_range", "value": 1.0},
        {"name": "must_include_coverage", "value": 1.0},
        {"name": "must_avoid_violation", "value": 0.0},
        {"name": "references_to_context_count", "value": 2.0},
        {"name": "follow_up_present", "value": 1.0},
    ]
    score = _compute_deterministic_score_for_type("contextual_insight", metrics)
    assert score >= 0.80, f"Expected >= 0.80, got {score}"


def test_contextual_insight_too_few_insights():
    from app.services.metrics import compute_contextual_insight_metrics

    expected = json.dumps({"expected_insight_count": {"min": 3, "max": 6}})
    actual = json.dumps({
        "answer": {
            "insights": ["Una sola idea"],
            "references_to_context": ["r1"],
            "follow_up_questions": ["q"],
            "depth": "commerciale",
        }
    })

    ci = compute_contextual_insight_metrics(expected, actual)
    assert ci["insight_count_in_range"] == 0.0
    assert ci["insight_count"] == 1.0


def test_contextual_insight_depth_valid_accepts_any_string():
    from app.services.metrics import compute_contextual_insight_metrics

    expected = json.dumps({})
    actual = json.dumps({
        "answer": {
            "insights": ["a", "b", "c"],
            "references_to_context": ["r1"],
            "follow_up_questions": ["q"],
            "depth": "Go-to-Market Strategy for Japan",
        }
    })

    ci = compute_contextual_insight_metrics(expected, actual)
    assert ci["depth_valid"] == 1.0


def test_contextual_insight_depth_empty_fails():
    from app.services.metrics import compute_contextual_insight_metrics

    expected = json.dumps({})
    actual = json.dumps({
        "answer": {
            "insights": ["a", "b", "c"],
            "references_to_context": ["r1"],
            "follow_up_questions": ["q"],
            "depth": "",
        }
    })

    ci = compute_contextual_insight_metrics(expected, actual)
    assert ci["depth_valid"] == 0.0


def test_contextual_insight_no_field_accuracy():
    from app.services.test_runner import STRUCTURED_TEST_TYPES
    assert "contextual_insight" not in STRUCTURED_TEST_TYPES


def run_all():
    tests = [
        ("ci_complete_good", test_contextual_insight_complete_good),
        ("ci_avoid_theme_detected", test_contextual_insight_avoid_theme_detected),
        ("ci_scoring", test_contextual_insight_scoring),
        ("ci_too_few_insights", test_contextual_insight_too_few_insights),
        ("ci_depth_accepts_any_string", test_contextual_insight_depth_valid_accepts_any_string),
        ("ci_depth_empty_fails", test_contextual_insight_depth_empty_fails),
        ("ci_no_field_accuracy", test_contextual_insight_no_field_accuracy),
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
