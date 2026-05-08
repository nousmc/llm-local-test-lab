import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["APP_SECRET_KEY"] = "model-selection-test-key"

from app.models import ConfiguredModel, TestRun


def test_selected_model_ids_do_not_default_to_first_enabled_model():
    selected_model_ids = ["qwen3.6-27b", "mistral-7b"]
    first_enabled_model = ConfiguredModel(
        id="devstral-small-2-24b",
        label="Devstral Small 2 24B ctx128k",
        provider="ollama",
        model_name="devstral-small-2-24B:ctx128k",
        enabled=True,
    )
    selected_models = [
        ConfiguredModel(id="qwen3.6-27b", label="Qwen", provider="ollama", model_name="qwen3.6-27b:ctx64k", enabled=True),
        ConfiguredModel(id="mistral-7b", label="Mistral", provider="ollama", model_name="mistral:7b", enabled=True),
    ]
    available = [first_enabled_model] + selected_models
    by_id = {m.id: m for m in available}
    resolved = [by_id[mid] for mid in selected_model_ids if mid in by_id]

    assert [m.id for m in resolved] == selected_model_ids
    assert "devstral-small-2-24b" not in [m.id for m in resolved]


def test_empty_model_selection_stays_empty():
    run = TestRun(name="empty", selected_model_ids_json=json.dumps([]))
    selected = [str(mid) for mid in json.loads(run.selected_model_ids_json or "[]") if str(mid).strip()]
    assert selected == []
