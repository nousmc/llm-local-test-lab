import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["APP_SECRET_KEY"] = "test-seed-quality-key"

from app.models import TestCase, TestType
from app.services.metrics import check_prompt_contamination, compute_field_accuracy
from app.services.prompt_builder import validate_prompt
from app.services.seed_test_cases import SEED_TEST_CASES
from app.services.test_runner import _build_prompt


TEST_TYPES = {
    "classification",
    "data_extraction",
    "rag_qa",
    "summarization",
    "code_analysis",
    "code_documentation",
    "refactoring",
    "image_description",
    "ocr_extraction",
    "speech_to_text_postprocess",
}


def _expected(case):
    return json.loads(case["expected_output_json"])


def _prompt(case):
    tc = TestCase(
        test_type_id=case["test_type_id"],
        title=case["title"],
        description=case.get("description"),
        input_text=case.get("input_text"),
        context_text=case.get("context_text"),
        expected_output_json=case.get("expected_output_json"),
    )
    tt = TestType(id=case["test_type_id"], label=case["test_type_id"].replace("_", " ").title())
    return _build_prompt(tc, tt)


def test_seed_library_covers_all_types():
    found = {c["test_type_id"] for c in SEED_TEST_CASES}
    assert found == TEST_TYPES
    assert len(SEED_TEST_CASES) >= 20


def test_all_seed_cases_have_valid_json_payloads():
    titles = set()
    for case in SEED_TEST_CASES:
        assert case["title"] not in titles, f"Titolo duplicato: {case['title']}"
        titles.add(case["title"])
        assert case["test_type_id"] in TEST_TYPES
        assert case.get("description"), f"Descrizione mancante: {case['title']}"
        assert case.get("input_text"), f"Input mancante: {case['title']}"
        assert isinstance(_expected(case), dict), case["title"]
        assert isinstance(json.loads(case["rubric_json"]), dict), case["title"]
        assert isinstance(json.loads(case["tags_json"]), list), case["title"]


def test_seed_library_expected_json_is_valid_for_all_demo_cases():
    for case in SEED_TEST_CASES:
        json.loads(case["expected_output_json"])

    from app.services.seed_libraries import SEED_LIBRARY_TEST_CASES
    assert SEED_LIBRARY_TEST_CASES
    for case in SEED_LIBRARY_TEST_CASES:
        json.loads(case["expected_output_json"])


def test_all_seed_prompts_are_valid_and_expanded():
    generic_placeholders = [
        "classification_expected", "json_expected", "rag_expected", "summary_expected",
        "code_expected", "code_doc_expected", "refactoring_expected", "vision_expected",
        "ocr_expected", "stt_expected", "{ ... i dati del task ... }",
    ]
    for case in SEED_TEST_CASES:
        prompt = _prompt(case)
        source = "\n".join([case.get("input_text") or "", case.get("context_text") or ""])
        valid, issues, status = validate_prompt(prompt, case["test_type_id"], case["expected_output_json"], allowed_source_text=source)
        assert valid, f"Prompt non valido per {case['title']}: {issues}"
        for placeholder in generic_placeholders:
            assert placeholder not in prompt.lower(), f"Placeholder non espanso in {case['title']}: {placeholder}"
        assert '"answer"' in prompt, f"Container answer assente: {case['title']}"
        contaminated, info = check_prompt_contamination(prompt, case["expected_output_json"], allowed_source_text=source)
        assert not contaminated, f"Prompt contaminato per {case['title']}: {info}"


def test_classification_seed_structure():
    for case in [c for c in SEED_TEST_CASES if c["test_type_id"] == "classification"]:
        exp = _expected(case)
        assert "schema" in exp and exp["schema"] == {"label": "string"}
        assert "expected" in exp and set(exp["expected"].keys()) == {"label"}
        assert exp.get("required_fields") == ["label"]
        labels = exp.get("allowed_labels", [])
        assert len(labels) >= 2
        assert exp["expected"]["label"] in labels
        prompt = _prompt(case)
        for label in labels:
            assert label in prompt, f"Classe ammessa non visibile nel prompt: {case['title']} -> {label}"


def test_extraction_seed_schema_expected_required_consistency():
    for case in [c for c in SEED_TEST_CASES if c["test_type_id"] == "data_extraction"]:
        exp = _expected(case)
        schema = set(exp.get("schema", {}).keys())
        expected = set(exp.get("expected", {}).keys())
        required = set(exp.get("required_fields", []))
        assert schema, case["title"]
        assert expected == schema, f"expected deve coprire lo schema: {case['title']}"
        assert required.issubset(schema), f"required fuori schema: {case['title']}"


def test_ocr_seed_expected_fields_are_used_as_task_fields():
    for case in [c for c in SEED_TEST_CASES if c["test_type_id"] == "ocr_extraction"]:
        exp = _expected(case)
        fields = exp.get("expected_fields", {})
        assert fields, case["title"]
        prompt = _prompt(case)
        for field in fields:
            assert f'"{field}"' in prompt or field in prompt, f"Campo OCR assente nel prompt: {case['title']} -> {field}"


def test_perfect_structured_seed_answers_score_perfect():
    structured = {"classification", "data_extraction", "ocr_extraction"}
    for case in [c for c in SEED_TEST_CASES if c["test_type_id"] in structured]:
        exp = _expected(case)
        if "expected" in exp:
            answer = exp["expected"]
            required = exp.get("required_fields") or list(answer.keys())
        elif "expected_fields" in exp:
            answer = exp["expected_fields"]
            required = list(answer.keys())
        else:
            continue
        actual = json.dumps({"answer": answer, "confidence": 1.0, "warnings": []})
        result = compute_field_accuracy(case["expected_output_json"], actual, required_fields=required)
        assert result["field_accuracy"] == 1.0, case["title"]
        assert not result["missing_fields"], case["title"]
        assert not result["hallucinated_fields"], case["title"]


def test_semantic_seed_cases_do_not_expose_hidden_expected_lists():
    hidden_keys = {
        "answer_facts", "required_points", "forbidden_points", "expected_findings",
        "expected_recommendations", "must_include", "required_objects", "forbidden_objects",
        "clean_transcript_contains", "action_items",
    }
    for case in SEED_TEST_CASES:
        exp = _expected(case)
        prompt = _prompt(case)
        for key in hidden_keys.intersection(exp.keys()):
            values = exp[key]
            if isinstance(values, list):
                for value in values:
                    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
                    if len(text) > 12:
                        source = "\n".join([case.get("input_text") or "", case.get("context_text") or ""])
                        if text in source:
                            continue
                        assert text not in prompt, f"Valore di valutazione '{key}' nel prompt: {case['title']}"
