import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["APP_SECRET_KEY"] = "test-validator-robustness-key"


def test_parse_complete_valid_json():
    from app.services.validator import _parse_validator_response

    text = json.dumps({
        "score": 0.85, "passed": True, "format_score": 0.9,
        "semantic_score": 0.8, "completeness_score": 0.75, "safety_score": 1.0,
        "hallucination_detected": False, "refusal_detected": False,
        "reasoning": "Risposta corretta e completa"
    })
    result, status, error = _parse_validator_response(text)
    assert status == "ok", f"Expected ok, got {status}: {error}"
    assert result["score"] == 0.85
    assert result["passed"] is True
    assert result["format_score"] == 0.9
    assert result["semantic_score"] == 0.8
    assert result["completeness_score"] == 0.75
    assert result["safety_score"] == 1.0
    assert result["hallucination_detected"] is False
    assert result["refusal_detected"] is False
    assert "reasoning" in result


def test_parse_json_in_markdown_fence():
    from app.services.validator import _parse_validator_response

    text = '```json\n{"score":0.7,"passed":true,"format_score":0.6,"semantic_score":0.5,"completeness_score":0.4,"safety_score":1.0,"hallucination_detected":false,"refusal_detected":false,"reasoning":"ok"}\n```'
    result, status, error = _parse_validator_response(text)
    assert status == "ok", f"Expected ok, got {status}: {error}"
    assert result["score"] == 0.7
    assert result["passed"] is True


def test_parse_alternative_keys():
    from app.services.validator import _parse_validator_response

    text = json.dumps({
        "overall_score": 0.9, "pass": True, "format": 0.8,
        "semantic": 0.7, "completeness": 0.6, "safety_score": 1.0,
        "hallucination": False, "refusal": False, "explanation": "Ok"
    })
    result, status, error = _parse_validator_response(text)
    assert status in ("ok", "mapping_error"), f"Unexpected status: {status}: {error}"
    assert result.get("score") == 0.9, f"overall_score not mapped to score: {result}"
    assert result.get("passed") is True, f"pass not mapped to passed: {result}"
    assert result.get("format_score") == 0.8, f"format not mapped to format_score: {result}"
    assert result.get("semantic_score") == 0.7
    assert result.get("completeness_score") == 0.6
    assert result.get("hallucination_detected") is False
    assert result.get("refusal_detected") is False


def test_parse_mixed_keys():
    from app.services.validator import _parse_validator_response

    text = json.dumps({
        "score": 0.5, "pass": True, "format_score": 0.4,
        "semantic_score": 0.3, "completeness": 0.2, "safety": 1.0,
        "has_hallucination": False, "has_refusal": False
    })
    result, status, error = _parse_validator_response(text)
    assert status in ("ok", "mapping_error")
    assert result["score"] == 0.5
    assert result["passed"] is True
    assert result["completeness_score"] == 0.2
    assert result["safety_score"] == 1.0
    assert result["hallucination_detected"] is False
    assert result["refusal_detected"] is False


def test_parse_partial_json_missing_critical_keys():
    from app.services.validator import _parse_validator_response

    text = json.dumps({"format_score": 0.5, "semantic_score": 0.6})
    result, status, error = _parse_validator_response(text)
    assert status in ("ok", "mapping_error"), f"Status: {status}"
    assert result.get("format_score") == 0.5
    assert result.get("semantic_score") == 0.6


def test_parse_non_json_text():
    from app.services.validator import _parse_validator_response

    text = "Il modello ha risposto correttamente. Score: 0.85. Approvato."
    result, status, error = _parse_validator_response(text)
    assert status == "invalid_json", f"Expected invalid_json, got {status}"
    assert result["score"] is None


def test_parse_empty_response():
    from app.services.validator import _parse_validator_response

    text = ""
    result, status, error = _parse_validator_response(text)
    assert status == "empty_response", f"Expected empty_response, got {status}"
    assert result["score"] is None


def test_parse_empty_whitespace_only():
    from app.services.validator import _parse_validator_response

    text = "   \n\t  "
    result, status, error = _parse_validator_response(text)
    assert status == "empty_response"


def test_string_to_float_conversion():
    from app.services.validator import _parse_validator_response

    text = json.dumps({
        "score": "0.75", "passed": "true", "format_score": "0.8",
        "semantic_score": "0.6", "completeness_score": 0.5, "safety_score": "1.0",
        "hallucination_detected": "false", "refusal_detected": "false"
    })
    result, status, error = _parse_validator_response(text)
    assert status in ("ok", "mapping_error"), f"{status}: {error}"
    assert result["score"] == 0.75
    assert result["passed"] is True
    assert result["format_score"] == 0.8


def test_score_range_validation_clamps():
    from app.services.validator import _parse_validator_response

    text = json.dumps({
        "score": 2.5, "passed": True, "format_score": -0.5,
        "semantic_score": 1.5, "completeness_score": 0.5, "safety_score": 1.0,
        "hallucination_detected": False, "refusal_detected": False
    })
    result, status, error = _parse_validator_response(text)
    assert status in ("ok", "mapping_error")
    assert result["score"] <= 1.0, f"score not clamped: {result['score']}"
    assert result["format_score"] >= 0.0, f"format_score not clamped: {result['format_score']}"


def test_no_none_fields_when_status_ok():
    from app.services.validator import _parse_validator_response

    text = json.dumps({
        "score": 0.9, "passed": True, "format_score": 0.8,
        "semantic_score": 0.7, "completeness_score": 0.6, "safety_score": 1.0,
        "hallucination_detected": False, "refusal_detected": False,
        "reasoning": "OK"
    })
    result, status, error = _parse_validator_response(text)
    assert status == "ok", f"Expected ok, got {status}: {error}"
    score_fields = ["score", "passed", "format_score",
                     "semantic_score", "completeness_score", "safety_score"]
    for field in score_fields:
        assert result[field] is not None, f"{field} is None when status is ok"


def test_all_diagnostic_fields_present_in_empty_result():
    from app.services.validator import _empty_validation_result

    result = _empty_validation_result()
    assert "validator_status" not in result
    assert "validator_error_message" not in result
    assert "validator_raw_response" not in result
    assert "validator_attempts" not in result


def test_empty_validation_result_has_no_scores():
    from app.services.validator import _empty_validation_result

    result = _empty_validation_result()
    assert result["score"] is None
    assert result["passed"] is None
    assert result["format_score"] is None


def test_validate_response_returns_status_field():
    import asyncio
    from app.services.validator import validate_response

    result = asyncio.run(validate_response(
        test_type="classification",
        input_payload="test input",
        expected_output=json.dumps({"label": "cat"}),
        model_output=json.dumps({"answer": {"label": "cat"}}),
        rubric="",
    ))
    assert "validator_status" in result, f"Missing validator_status in {list(result.keys())}"
    assert validator_status_is_known(result["validator_status"]), \
        f"Unknown validator_status: {result['validator_status']}"


def test_result_has_diagnostic_keys():
    import asyncio
    from app.services.validator import validate_response

    result = asyncio.run(validate_response(
        test_type="classification",
        input_payload="test input",
        expected_output=json.dumps({"label": "cat"}),
        model_output=json.dumps({"answer": {"label": "cat"}}),
        rubric="",
    ))
    for key in ["validator_status", "validator_error_message",
                 "validator_raw_response", "validator_attempts"]:
        assert key in result, f"Missing key: {key}"
    assert isinstance(result["validator_attempts"], int)


KNOWN_STATUSES = {"ok", "provider_error", "timeout", "empty_response",
                   "invalid_json", "schema_error", "parse_error",
                   "mapping_error", "disabled", "unknown"}


def validator_status_is_known(status):
    return status in KNOWN_STATUSES


def run_all():
    tests = [
        ("parse_complete_valid_json", test_parse_complete_valid_json),
        ("parse_json_in_markdown_fence", test_parse_json_in_markdown_fence),
        ("parse_alternative_keys", test_parse_alternative_keys),
        ("parse_mixed_keys", test_parse_mixed_keys),
        ("parse_partial_json_missing_critical", test_parse_partial_json_missing_critical_keys),
        ("parse_non_json_text", test_parse_non_json_text),
        ("parse_empty_response", test_parse_empty_response),
        ("parse_empty_whitespace_only", test_parse_empty_whitespace_only),
        ("string_to_float_conversion", test_string_to_float_conversion),
        ("score_range_validation_clamps", test_score_range_validation_clamps),
        ("no_none_fields_when_status_ok", test_no_none_fields_when_status_ok),
        ("all_diagnostic_fields_in_empty", test_all_diagnostic_fields_present_in_empty_result),
        ("empty_validation_has_no_scores", test_empty_validation_result_has_no_scores),
        ("validate_response_returns_status", test_validate_response_returns_status_field),
        ("result_has_diagnostic_keys", test_result_has_diagnostic_keys),
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
