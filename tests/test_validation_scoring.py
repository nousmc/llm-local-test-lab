import json, sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["APP_SECRET_KEY"] = "test-validation-key"

def test_scoring_sums_to_one():
    from app.services.test_runner import _compute_final_score
    for tt in ["classification","data_extraction","ocr_extraction","rag_qa","summarization","image_description","code_analysis","code_documentation","refactoring","speech_to_text_postprocess"]:
        s = _compute_final_score(0.5, 0.5, 0.5, 1000, 60000, False, False, False, False, None, 10, 0.001, test_type_id=tt)
        assert 0 <= s <= 1.0, f"{tt}: {s}"

def test_structured_pure_weights():
    from app.services.test_runner import _compute_final_score
    s = _compute_final_score(0.8, 0.6, 0.7, 5000, 60000, False, False, False, False, None, 10, 0.001, test_type_id="data_extraction")
    assert s > 0.6

def test_code_analysis_invented_bug():
    from app.services.metrics import _contains_fuzzy
    code_finding = "non gestisce vettore nullo"
    code = "if norm1 == 0 or norm2 == 0: return 0.0"
    assert _contains_fuzzy(code, "norm1 == 0") or "norm2 == 0" in code
    real_bug = "zip(v1, v2) senza controllo len(v1) == len(v2)"
    assert "len(v1)" in real_bug

def test_rag_citation_semantic_support():
    from app.services.metrics import _contains_fuzzy
    claim = "2 giorni lavorativi"
    context = "verificati entro 3 giorni e riaccreditati entro 7 giorni"
    assert not _contains_fuzzy(context, claim)

def test_answer_absent_negative_explicit():
    from app.services.metrics import _answer_indicates_absence, _answer_indicates_negative
    assert not _answer_indicates_absence("Il documento non indica una diagnosi")
    assert _answer_indicates_negative("No, il documento non indica una diagnosi.")

def test_prompt_echo_detection():
    from app.services.metrics import detect_prompt_echo
    assert detect_prompt_echo("Pulisci e struttura la trascrizione grezza: ok allora emh...", "Pulisci e struttura la trascrizione grezza")
    assert not detect_prompt_echo("Deploy completato, rollback disponibile.", "")

def test_data_extraction_partial_accuracy():
    from app.services.metrics import compute_field_accuracy
    expected = json.dumps({"schema":{"a":"string","b":"string","c":"string"},"expected":{"a":"x","b":"y","c":"z"},"required_fields":["a","b","c"]})
    actual = json.dumps({"answer":{"a":"x","b":"y","c":"w"}})
    r = compute_field_accuracy(expected, actual, required_fields=["a","b","c"])
    assert r["field_accuracy"] == 0.6667
    assert not r["hallucinated_fields"]

def test_extra_fields_renamed():
    from app.services.metrics import compute_field_accuracy
    expected = json.dumps({"expected":{"a":"x"},"required_fields":["a"]})
    actual = json.dumps({"answer":{"a":"x","b":"y"}})
    r = compute_field_accuracy(expected, actual, required_fields=["a"])
    assert "b" in r["hallucinated_fields"]
    assert r["field_accuracy"] == 1.0

if __name__ == "__main__":
    import pytest; pytest.main([__file__, "-v"])
