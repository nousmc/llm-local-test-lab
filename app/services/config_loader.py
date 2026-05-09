import os
from pathlib import Path

import yaml


DEFAULT_CONFIG = {
    "app": {"name": "LLM Local Test Lab", "database_url": "sqlite:///data/app.db"},
    "providers": {"ollama": {"enabled": True, "base_url": "http://localhost:11434", "timeout_seconds": 180}},
    "models": [],
    "validator": {"enabled": False},
    "execution": {"parallelism": 2, "retry_attempts": 2, "retry_backoff_seconds": 3},
    "benchmark_defaults": {"repeat_count": 3, "temperature_min": 0.1, "temperature_mid": 0.5, "temperature_max": 0.9},
    "metrics": {"enabled": []},
    "test_types": [],
    "thresholds": {"default_pass_score": 0.80, "json_validity_required": True, "max_latency_ms_warning": 30000},
}

_config_cache = None
_config_path = None


def load_config(config_path: str = "config/config.yaml") -> dict:
    global _config_cache, _config_path
    if _config_cache is not None and _config_path == config_path:
        return _config_cache

    path = Path(config_path)
    if not path.exists():
        _config_cache = DEFAULT_CONFIG.copy()
        _config_path = config_path
        return _config_cache

    try:
        data = yaml.safe_load(path.read_text())
        merged = DEFAULT_CONFIG.copy()
        if data:
            for section in DEFAULT_CONFIG:
                if section in data:
                    if isinstance(merged[section], dict):
                        merged[section].update(data[section])
                    else:
                        merged[section] = data[section]
        _config_cache = merged
        _config_path = config_path
        return merged
    except Exception:
        _config_cache = DEFAULT_CONFIG.copy()
        _config_path = config_path
        return _config_cache


def get_models_from_config() -> list[dict]:
    config = load_config()
    return config.get("models", [])


def get_test_types_from_config() -> list[dict]:
    config = load_config()
    return config.get("test_types", [])


def get_validator_config() -> dict:
    config = load_config()
    return config.get("validator", {})


def get_execution_config() -> dict:
    config = load_config()
    return config.get("execution", {})


def get_provider_config(provider: str) -> dict:
    config = load_config()
    return config.get("providers", {}).get(provider, {})


def get_metrics_config() -> dict:
    config = load_config()
    return config.get("metrics", {})


def get_benchmark_defaults() -> dict:
    config = load_config()
    return config.get("benchmark_defaults", {})


def get_thresholds_config() -> dict:
    config = load_config()
    return config.get("thresholds", {})


def ensure_directories(config_path: str = "config/config.yaml") -> None:
    config = load_config(config_path)
    paths = [
        config.get("paths", {}).get("uploads_dir", "app/uploads"),
        config.get("paths", {}).get("reports_dir", "data/reports"),
        config.get("paths", {}).get("exports_dir", "data/exports"),
    ]
    for p in paths:
        path = Path(p)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
    data_dir = Path("data")
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)


def reload_config():
    global _config_cache
    _config_cache = None
    return load_config(_config_path or "config/config.yaml")
