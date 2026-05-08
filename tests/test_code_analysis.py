import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["APP_SECRET_KEY"] = "test-code-analysis-key"


def test_code_analysis_deterministic_metrics_good():
    from app.services.metrics import compute_code_analysis_deterministic_metrics

    expected = json.dumps({
        "expected_findings": [
            {"type": "security", "severity": "high", "description_contains": "SQL injection"}
        ],
        "expected_recommendations": ["Usare query parametrizzate"],
        "language": "it",
    })
    actual = json.dumps({
        "answer": {
            "findings": [
                {
                    "type": "security",
                    "severity": "medium",
                    "description": "SQL injection nel costrutto f-string. L'input username proviene direttamente dalla route Flask senza sanitizzazione.",
                    "location": "query = f\"SELECT * FROM users WHERE username = '{username}'\"",
                }
            ],
            "recommendations": [
                "Utilizzare query parametrizzate con placeholder %s",
                "Validare l'input username prima di usarlo nella query",
            ],
            "overall_assessment": "Vulnerabilita SQL injection critica. Correzione prioritaria richiesta.",
        }
    })

    ca = compute_code_analysis_deterministic_metrics(expected, actual)
    assert ca["findings_schema_valid"] == 1.0
    assert ca["allowed_type_valid"] == 1.0
    assert ca["allowed_severity_valid"] == 1.0
    assert ca["finding_required_keys_present"] == 1.0
    assert ca["findings_count"] == 1.0


def test_code_analysis_deterministic_language_english():
    from app.services.metrics import compute_code_analysis_deterministic_metrics

    expected = json.dumps({
        "expected_findings": [{"type": "security", "severity": "high", "description_contains": "SQL injection"}],
        "language": "it",
    })
    actual = json.dumps({
        "answer": {
            "findings": [
                {
                    "type": "security",
                    "severity": "medium",
                    "description": "SQL injection vulnerability in the f-string query. The username input comes directly from the Flask route without sanitization.",
                    "location": "query = f\"SELECT * FROM users WHERE username = '{username}'\"",
                }
            ],
            "recommendations": ["Use parameterized queries"],
        }
    })
    response_text = "Found a SQL injection vulnerability. Use parameterized queries instead of f-strings."

    ca = compute_code_analysis_deterministic_metrics(expected, actual, response_text)
    assert ca["language_compliance_deterministic"] == 0.0, f"English should not match Italian: {ca}"


def test_code_analysis_deterministic_language_italian():
    from app.services.metrics import compute_code_analysis_deterministic_metrics

    expected = json.dumps({
        "expected_findings": [{"type": "security", "severity": "high", "description_contains": "SQL injection"}],
        "language": "it",
    })
    actual = json.dumps({
        "answer": {
            "findings": [
                {
                    "type": "security",
                    "severity": "medium",
                    "description": "SQL injection nella query f-string. L'input utente non viene validato.",
                    "location": "query = f\"SELECT * FROM users WHERE username = '{username}'\"",
                }
            ],
            "recommendations": ["Usare query parametrizzate"],
        }
    })
    response_text = "Identificata vulnerabilita SQL injection. La query f-string e pericolosa perche l'input non e validato."

    ca = compute_code_analysis_deterministic_metrics(expected, actual, response_text)
    assert ca["language_compliance_deterministic"] == 1.0


def test_code_analysis_no_field_accuracy_used():
    from app.services.test_runner import STRUCTURED_TEST_TYPES, HYBRID_TEST_TYPES

    assert "code_analysis" not in STRUCTURED_TEST_TYPES
    assert "code_analysis" in HYBRID_TEST_TYPES


def test_code_analysis_deterministic_score_range():
    from app.services.test_runner import _compute_deterministic_score_for_type

    metrics = [
        {"name": "json_validity", "value": 1.0},
        {"name": "schema_compliance", "value": 1.0},
        {"name": "findings_schema_valid", "value": 1.0},
        {"name": "allowed_type_valid", "value": 1.0},
        {"name": "allowed_severity_valid", "value": 1.0},
        {"name": "language_compliance_deterministic", "value": 0.0},
    ]
    score = _compute_deterministic_score_for_type("code_analysis", metrics)
    assert score == 0.75, f"Expected 0.75, got {score}"


def test_code_analysis_deterministic_score_partial():
    from app.services.test_runner import _compute_deterministic_score_for_type

    metrics = [
        {"name": "json_validity", "value": 1.0},
        {"name": "schema_compliance", "value": 1.0},
        {"name": "findings_schema_valid", "value": 1.0},
        {"name": "allowed_type_valid", "value": 1.0},
        {"name": "allowed_severity_valid", "value": 0.0},
        {"name": "language_compliance_deterministic", "value": 1.0},
    ]
    score = _compute_deterministic_score_for_type("code_analysis", metrics)
    assert 0.45 <= score <= 0.70, f"Expected partial score, got {score}"


def test_code_analysis_invalid_finding_type():
    from app.services.metrics import compute_code_analysis_deterministic_metrics

    expected = json.dumps({"expected_findings": [{"type": "bug", "severity": "medium"}]})
    actual = json.dumps({
        "answer": {
            "findings": [
                {
                    "type": "invalid_type_name",
                    "severity": "medium",
                    "description": "Something",
                    "location": "somewhere",
                }
            ],
        }
    })

    ca = compute_code_analysis_deterministic_metrics(expected, actual)
    assert ca["allowed_type_valid"] == 0.0
    assert ca["findings_schema_valid"] == 1.0


def run_all():
    tests = [
        ("code_analysis_deterministic_metrics_good", test_code_analysis_deterministic_metrics_good),
        ("code_analysis_deterministic_language_english", test_code_analysis_deterministic_language_english),
        ("code_analysis_deterministic_language_italian", test_code_analysis_deterministic_language_italian),
        ("code_analysis_no_field_accuracy_used", test_code_analysis_no_field_accuracy_used),
        ("code_analysis_deterministic_score_range", test_code_analysis_deterministic_score_range),
        ("code_analysis_deterministic_score_partial", test_code_analysis_deterministic_score_partial),
        ("code_analysis_invalid_finding_type", test_code_analysis_invalid_finding_type),
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
