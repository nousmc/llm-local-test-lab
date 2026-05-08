import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from .settings import get_settings
from .database import init_db, SessionLocal
from .models import ConfiguredModel, ProviderConfig, ValidatorConfig, SecretConfig, TestType
from .services.config_loader import (
    load_config, ensure_directories,
    get_models_from_config, get_test_types_from_config,
)
from .services.secret_loader import load_secrets
from .routers import dashboard, configs, models, test_types, test_cases, test_runs, reports, api, providers, validator_config, secrets_config, test_libraries

settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.app_debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

base_dir = Path(__file__).resolve().parent

import json as _json
templates = Jinja2Templates(directory=str(base_dir / "templates"))
templates.env.filters["from_json_or"] = lambda text, key, default: (
    _json.loads(text).get(key, default) if text else default
)

app.state.templates = templates

static_dir = base_dir / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

uploads_dir = base_dir / "uploads"
if uploads_dir.exists():
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

app.include_router(dashboard.router)
app.include_router(configs.router)
app.include_router(models.router)
app.include_router(test_types.router)
app.include_router(test_cases.router)
app.include_router(test_runs.router)
app.include_router(reports.router)
app.include_router(api.router)
app.include_router(providers.router)
app.include_router(validator_config.router)
app.include_router(secrets_config.router)
app.include_router(test_libraries.router)


@app.on_event("startup")
async def startup_event():
    print(f"Starting {settings.app_name} on port {settings.app_port}")

    ensure_directories()

    config = load_config()
    print(f"Config loaded: {len(config.get('models', []))} models, {len(config.get('test_types', []))} test types")

    secrets, secrets_ok = load_secrets(settings.secrets_file)
    if secrets_ok:
        print("Secrets loaded successfully")
        keys_status = {k: "configured" if v else "missing" for k, v in secrets.items() if k != "APP_SECRET_KEY"}
        print(f"API keys: {keys_status}")
    else:
        print(f"Warning: secrets file not found at {settings.secrets_file}")

    init_db()
    print("Database initialized")

    _sync_config_to_db()


def _sync_config_to_db():
    db = SessionLocal()
    try:
        import json

        config = load_config()

        existing_providers = db.query(ProviderConfig).count()
        existing_validators = db.query(ValidatorConfig).count()
        existing_models = db.query(ConfiguredModel).count()
        existing_types = db.query(TestType).count()
        existing_secrets = db.query(SecretConfig).count()

        # Sync secrets — seed from file to DB on first run
        if existing_secrets == 0:
            from .security import encrypt_value
            file_secrets, _ = load_secrets(settings.secrets_file)
            for key in ["OPENROUTER_API_KEY", "OLLAMA_API_KEY", "APP_SECRET_KEY"]:
                val = file_secrets.get(key, "")
                if val:
                    sc = SecretConfig(key=key, value=encrypt_value(val))
                    db.add(sc)

        # Sync providers — seed only if table is empty (first run)
        if existing_providers == 0:
            providers_cfg = config.get("providers", {})
            for name, pdata in providers_cfg.items():
                if not isinstance(pdata, dict):
                    continue
                prov = ProviderConfig(
                    name=name,
                    label=pdata.get("label", name.title()),
                    base_url=pdata.get("base_url", ""),
                    timeout_seconds=pdata.get("timeout_seconds", 180),
                    enabled=pdata.get("enabled", True),
                    app_name=pdata.get("app_name"),
                    site_url=pdata.get("site_url"),
                )
                db.add(prov)

        # Sync validator — seed only if no validator exists
        if existing_validators == 0:
            validator_cfg = config.get("validator", {})
            if validator_cfg:
                vc = ValidatorConfig(
                    enabled=validator_cfg.get("enabled", False),
                    provider=validator_cfg.get("provider", "ollama"),
                    model=validator_cfg.get("model", ""),
                    fallback_provider=validator_cfg.get("fallback_provider"),
                    fallback_model=validator_cfg.get("fallback_model"),
                    validation_mode=validator_cfg.get("validation_mode", "rubric_json"),
                    temperature=validator_cfg.get("temperature", 0.0),
                    max_tokens=validator_cfg.get("max_tokens", 2048),
                )
                db.add(vc)

        # Sync models — seed only if table is empty (first run)
        if existing_models == 0:
            models_cfg = get_models_from_config()
            for m in models_cfg:
                model = ConfiguredModel(
                    id=m["id"],
                    label=m.get("label", m["id"]),
                    provider=m.get("provider", "ollama"),
                    model_name=m.get("model", m["id"]),
                    enabled=m.get("enabled", True),
                    family=m.get("family"),
                    size_b=m.get("size_b"),
                    context_window=m.get("context_window"),
                    supports_vision=m.get("supports_vision", False),
                    supports_json=m.get("supports_json", False),
                    default_params_json=json.dumps(m.get("default_params", {})),
                )
                db.add(model)
        else:
            existing_model_ids = {row[0] for row in db.query(ConfiguredModel.id).all()}
            models_cfg = get_models_from_config()
            for m in models_cfg:
                if m["id"] not in existing_model_ids:
                    model = ConfiguredModel(
                        id=m["id"],
                        label=m.get("label", m["id"]),
                        provider=m.get("provider", "ollama"),
                        model_name=m.get("model", m["id"]),
                        enabled=m.get("enabled", True),
                        family=m.get("family"),
                        size_b=m.get("size_b"),
                        context_window=m.get("context_window"),
                        supports_vision=m.get("supports_vision", False),
                        supports_json=m.get("supports_json", False),
                        default_params_json=json.dumps(m.get("default_params", {})),
                    )
                    db.add(model)
                    print(f"Migration: added missing model {m['id']}")

        # Sync test types — seed only if table is empty
        if existing_types == 0:
            test_types_cfg = get_test_types_from_config()
            for tt in test_types_cfg:
                ttype = TestType(
                    id=tt["id"],
                    label=tt.get("label", tt["id"]),
                    description=tt.get("description"),
                    expected_schema=tt.get("expected_schema"),
                    enabled=True,
                )
                db.add(ttype)
        else:
            existing_ids = {row[0] for row in db.query(TestType.id).all()}
            test_types_cfg = get_test_types_from_config()
            for tt in test_types_cfg:
                if tt["id"] not in existing_ids:
                    ttype = TestType(
                        id=tt["id"],
                        label=tt.get("label", tt["id"]),
                        description=tt.get("description"),
                        expected_schema=tt.get("expected_schema"),
                        enabled=True,
                    )
                    db.add(ttype)
                    print(f"Migration: added missing test type {tt['id']}")

        db.commit()
        provider_count = db.query(ProviderConfig).count()
        model_count = db.query(ConfiguredModel).count()
        type_count = db.query(TestType).count()
        val_count = db.query(ValidatorConfig).count()

        from .services.seed_test_cases import seed_test_cases
        seeded = seed_test_cases(db)
        if seeded > 0:
            db.commit()

        from .services.seed_libraries import (
            seed_libraries,
            seed_library_test_cases,
            migrate_legacy_tests_to_general_library,
            migrate_academy_library_to_stem,
        )
        libs_added = seed_libraries(db)
        if libs_added > 0:
            db.commit()
        lib_cases_added = seed_library_test_cases(db)
        if lib_cases_added > 0:
            db.commit()
        migrated = migrate_legacy_tests_to_general_library(db)
        if migrated > 0:
            db.commit()
        academy_migrated = migrate_academy_library_to_stem(db)
        if academy_migrated > 0:
            db.commit()

        _migrate_validation_result_columns(db)

        from .services.prompt_backfill import backfill_test_case_prompt_templates
        prompts_backfilled = backfill_test_case_prompt_templates(db)

        print(f"Synced {provider_count} providers, {val_count} validators, {model_count} models and {type_count} test types to database")
        if seeded > 0:
            print(f"Seeded {seeded} new test cases from library")
        if libs_added > 0:
            print(f"Seeded {libs_added} new test libraries")
        if lib_cases_added > 0:
            print(f"Seeded {lib_cases_added} new library test cases")
        if migrated > 0:
            print(f"Migrated {migrated} legacy test cases to general library")
        if academy_migrated > 0:
            print(f"Disabled {academy_migrated} old academy admin seed cases")
        if prompts_backfilled > 0:
            print(f"Backfilled {prompts_backfilled} test case prompt templates")
    except Exception as e:
        db.rollback()
        print(f"Error syncing config to DB: {e}")
    finally:
        db.close()


def _migrate_validation_result_columns(db):
    from sqlalchemy import text
    try:
        columns = db.execute(text("PRAGMA table_info(validation_results)")).fetchall()
        col_names = [c[1] for c in columns]
        new_cols = {
            "validator_status": "VARCHAR DEFAULT 'ok'",
            "validator_error_message": "TEXT",
            "validator_raw_response": "TEXT",
            "validator_attempts": "INTEGER DEFAULT 1",
        }
        for col_name, col_def in new_cols.items():
            if col_name not in col_names:
                db.execute(text(f"ALTER TABLE validation_results ADD COLUMN {col_name} {col_def}"))
                print(f"Migration: added column validation_results.{col_name}")
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Migration warning (validation_result columns): {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=settings.app_debug)
