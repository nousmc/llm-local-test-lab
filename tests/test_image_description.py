import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["APP_SECRET_KEY"] = "test-image-desc-key"


def test_image_description_complete_and_objective_passes():
    from app.services.metrics import compute_image_description_metrics

    expected = json.dumps({})
    actual = json.dumps({
        "answer": {
            "description": "Ufficio moderno con scrivanie bianche, monitor curvo, due laptop chiusi, tablet acceso con grafico a barre, pianta in vaso verde, libreria con libri tecnici, lavagna con post-it colorati, finestra su cortile alberato. Luce naturale diffusa.",
            "objects_detected": [
                "scrivanie bianche", "monitor curvo", "laptop chiusi", "tablet acceso",
                "pianta in vaso", "libreria", "lavagna", "finestra"
            ],
            "scene_type": "ufficio",
            "dominant_colors": ["bianco", "grigio", "verde", "nero"]
        }
    })

    doc = compute_image_description_metrics(expected, actual)
    assert doc["required_fields_present"] == 1.0, f"fields: {doc}"
    assert doc["objects_detected_is_list"] == 1.0
    assert doc["dominant_colors_is_list"] == 1.0
    assert doc["scene_type_present"] == 1.0
    assert doc["description_word_count"] > 0


def test_image_description_complete_response_does_not_hit_field_accuracy():
    from app.services.test_runner import _compute_deterministic_score_for_type

    metrics = [
        {"name": "json_validity", "value": 1.0},
        {"name": "required_fields_present", "value": 1.0},
        {"name": "max_words_respected", "value": 1.0},
    ]
    score = _compute_deterministic_score_for_type("image_description", metrics)
    assert score >= 0.80, f"Expected >= 0.80, got {score}"


def test_image_description_no_field_accuracy_fallback():
    from app.services.test_runner import STRUCTURED_TEST_TYPES, SEMANTIC_TEST_TYPES

    assert "image_description" not in STRUCTURED_TEST_TYPES
    assert "image_description" in SEMANTIC_TEST_TYPES


def test_image_description_missing_scene_type():
    from app.services.metrics import compute_image_description_metrics

    expected = json.dumps({})
    actual = json.dumps({
        "answer": {
            "description": "Un ufficio con scrivania.",
            "objects_detected": ["scrivania"],
            "dominant_colors": ["bianco"],
        }
    })

    doc = compute_image_description_metrics(expected, actual)
    assert doc["required_fields_present"] < 1.0, f"Scene type missing should reduce fields: {doc}"


def test_image_description_over_max_words():
    from app.services.metrics import compute_image_description_metrics

    expected = json.dumps({"max_words": 10})
    long_desc = " ".join(["parola" for _ in range(20)])
    actual = json.dumps({
        "answer": {
            "description": long_desc,
            "objects_detected": ["x"],
            "scene_type": "ufficio",
            "dominant_colors": ["bianco"],
        }
    })

    doc = compute_image_description_metrics(expected, actual)
    assert doc["max_words_respected"] == 0.0


def test_image_description_objects_not_list():
    from app.services.metrics import compute_image_description_metrics

    expected = json.dumps({})
    actual = json.dumps({
        "answer": {
            "description": "Ufficio.",
            "objects_detected": "scrivania, monitor",
            "scene_type": "ufficio",
            "dominant_colors": ["bianco"],
        }
    })

    doc = compute_image_description_metrics(expected, actual)
    assert doc["objects_detected_is_list"] == 0.0


def run_all():
    tests = [
        ("image_desc_complete_and_objective", test_image_description_complete_and_objective_passes),
        ("image_desc_no_field_accuracy", test_image_description_complete_response_does_not_hit_field_accuracy),
        ("image_desc_not_structured", test_image_description_no_field_accuracy_fallback),
        ("image_desc_missing_scene_type", test_image_description_missing_scene_type),
        ("image_desc_over_max_words", test_image_description_over_max_words),
        ("image_desc_objects_not_list", test_image_description_objects_not_list),
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
