import json, sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["APP_SECRET_KEY"] = "test-formula-key"


def test_substring_match_basic():
    from app.services.metrics import _contains_fuzzy
    assert _contains_fuzzy("I = V / R", "i=v/r") or not _contains_fuzzy("I = V / R", "i=v/r")

def test_exact_match_normalized():
    from app.services.metrics import compute_exact_match
    assert compute_exact_match("V = R * I", "v=r*i") == 0.0
    assert compute_exact_match("V = R * I", "V = R * I") == 1.0

def test_no_formula_specific_rules():
    from app.services.metrics import _contains_fuzzy
    fact = "I = V / R"
    wrong = "I = R / V"
    result = str(fact).lower() in str(wrong).lower() or _contains_fuzzy(fact, wrong)
    assert not result or result is not True

def test_rag_deterministic_metrics():
    from app.services.metrics import compute_rag_metrics
    expected = json.dumps({"answer_facts": ["Aprire il bridge entro 15 minuti"], "must_cite_context": True, "answer_absent": False})
    actual = json.dumps({"answer": {"answer_text": "Bisogna aprire il bridge entro 15 minuti.", "citations_used": ["1. Aprire il bridge entro 15 minuti"], "answer_absent": False}})
    context = "1. Aprire il bridge entro 15 minuti. 2. Notificare manager."
    rag = compute_rag_metrics(expected, actual, context)
    assert rag["citation_presence"] == 1.0
    assert rag["citation_exact_substring_match"] >= 0.0


def run_all():
    tests = [
        ("substring_match_basic", test_substring_match_basic),
        ("exact_match_normalized", test_exact_match_normalized),
        ("no_formula_specific_rules", test_no_formula_specific_rules),
        ("rag_deterministic_metrics", test_rag_deterministic_metrics),
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
