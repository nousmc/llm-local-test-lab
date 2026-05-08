# AGENTS.md — LLM Local Test Lab

**CRITICAL: Never commit or push to GitHub unless explicitly asked by the user.**

## Run the app

```bash
uvicorn app.main:app --host 0.0.0.0 --port 7357
```

Opens at **http://localhost:7357**. On first start, SQLite DB is auto-created in `data/` and seeded from `config/config.yaml` (models, providers, test types, demo test cases, libraries).

## Run tests

```bash
export APP_SECRET_KEY=test-key
pytest tests/ -v
```

Test files also support standalone execution: `python tests/test_benchmark_integrity.py`. Both modes need `APP_SECRET_KEY` in env.

## Config & secrets

- **Config:** `config/config.yaml` — defines providers, models, validator, execution params, test types, thresholds.
- **Secrets:** `secrets/secret.key` (gitignored, `KEY=VALUE` lines). Required keys: `OPENROUTER_API_KEY`, `OLLAMA_API_KEY`, `APP_SECRET_KEY`.
- Secrets are loaded from file, encrypted (XOR+B64), and stored in the DB. Never exposed in UI.
- Environment overrides: Pydantic `Settings` reads env vars with `LLM_` prefix.

## Architecture

- **`app/main.py`** — FastAPI entrypoint, startup event, config→DB sync, seed data, migration helpers.
- **`app/routers/`** — Thin HTTP handlers (12 routers). Web UI uses Jinja2; JSON API in `api.py`.
- **`app/services/`** — All business logic. Key files:
  - `test_runner.py` — Test execution, deterministic scoring, final scoring with protection rules, pass/fail logic.
  - `metrics.py` — Deterministic and heuristic metric calculators.
  - `metric_registry.py` — Registry of all metrics with `evaluation_mode` (deterministic/heuristic/llm), `category`, `legacy_aliases`.
  - `validator.py` — LLM validator client with retry, alternative key mapping, type-specific prompt hints.
  - `prompt_builder.py` — Prompt templates for 11 test types (loaded from `config/prompt_templates.yaml`, hardcoded fallback).
- **`config/prompt_templates.yaml`** — Editable prompt templates for all test types. Change prompts without touching Python.
- **`app/models.py`** — 11 SQLAlchemy ORM models. ValidationResult has `validator_status`, `validator_error_message`, `validator_raw_response`, `validator_attempts`.
- **`app/database.py`** — SQLite in WAL mode, `busy_timeout=5000`, retry_commit helper.

## Startup seeding

Idempotent: tables are seeded **only if empty**. Also runs migration helpers and `backfill_test_case_prompt_templates()`.

To reset state: stop app, delete `data/app.db`, restart.

## Scoring rules (critical invariants)

### Per-type deterministic formulas in `_compute_deterministic_score_for_type()`

| Type | Formula |
|---|---|
| classification, data_extraction, ocr | `0.25*jv + 0.25*sc + 0.50*field_accuracy` |
| code_analysis | `0.15*jv + 0.15*sc + 0.15*findings_schema + 0.15*type_valid + 0.15*sev_valid + 0.05*lang` |
| code_documentation | `0.20*jv + 0.35*structure + 0.35*completeness + 0.10*style` with penalties for missing/hallucinated params, exceptions, examples violations |
| rag_qa | `0.30*jv + 0.70*answer_absent_correctness` |
| summarization | `0.30*jv + 0.70*max_words_respected` |
| image_description | `0.20*jv + 0.40*required_fields_present + 0.40*max_words_respected` |
| speech_to_text_postprocess | `0.15*jv + 0.15*sc + 0.25*clean_present + 0.15*action_schema + 0.15*entity_schema + 0.15*filler_quality - echo_penalty(0.15)` |
| refactoring | `0.15*jv + 0.15*sc + 0.20*lexical_similarity` |
| contextual_insight | `0.15*jv + 0.15*sc + 0.15*insight_range + 0.15*must_cover + 0.10*refs + 0.10*fu - must_avoid_penalty(0.20)` |

### `_compute_final_score()` protection rules

- Perfect deterministic (1.0) + validator ≥ 0.90 → final = 1.0.
- Perfect deterministic + validator conflict → floor: 0.90 (structured), 0.85 (hybrid), 0.75 (semantic).
- Invalid JSON caps final at 0.30; schema violation at 0.50; refusal at 0.10.
- Hard gate: `json_validity=0` or `schema_compliance=0` → validator `passed` forced `False`, `format_score` capped.
- Three separate pass fields: `deterministic_passed`, `validator_passed`, `final_passed`.
- All pass fields initialized to `False` at top of scoring block (before any conditional branches) to prevent `referenced before assignment` errors.
- When validator_conflict on semantic/hybrid → `needs_review=true`, `final_score_mode="validator_conflict_adjusted"`.
- If validator unavailable → `final_score_mode="validator_fallback"`, `needs_review=true`.

## Metric evaluation modes

Every metric has a canonical `evaluation_mode` in `app/services/metric_registry.py`:

| Mode | Meaning | Decisive for scoring? |
|---|---|---|
| `deterministic` | Objectively computable (JSON validity, counts, types, presence) | Yes |
| `heuristic` | Generic signal (lexical_similarity, heuristics) | No (diagnostic only) |
| `llm` | From validator LLM (semantic_score, hallucination_detected, finding_accuracy, etc.) | Yes for semantic/hybrid tasks |

Legacy aliases (e.g. `semantic_similarity` → `lexical_similarity`, `hallucinated_fields_count` → `extra_fields_count`) are tracked in the registry. To resolve a metric name: `get_metric_meta(name)`.

## Per-type metric routing

Each test type has its own metric calculator, enforced via explicit `elif` checks in `test_runner.py`. A metric from one type will **never** leak into another type's result.

## Important metric behaviors

- **`answer_absent`**: Flag-based (`expected.answer_absent == actual.answer_absent`). Text-based absence detection is separate (`answer_absent_textual_absence_detected`). "Non contiene/non riporta" are **negative answers** (explicit statements), NOT absence ("non specifica" is absence).
- **`citation_exact_substring_match`**: Strict normalized substring — no SequenceMatcher, no fuzzy. Uses `_exact_normalized_substring()` with accent normalization.
- **`top_level_citations_present`**: 1.0 only if `actual.citations` has non-empty items. `[]` or `[""]` → 0.0.
- **`_normalize_text_for_match`**: Lowercase + NFKD accent removal + non-alpha stripped + whitespace collapsed.
- **`_answer_indicates_absence`**: patterns like "non specificato", "non menzionato", "non presente". NOT "non contiene"/"non riporta".
- **`_answer_indicates_negative`**: patterns like "il documento non indica", "non sono riportate", "non e presente alcun".
- **`ALLOWED_FINDING_TYPES`**: `{"bug", "security", "best_practice", "performance"}` — matches prompt.
- **Filler terms**: Regex word-boundary matching via `_FILLER_PATTERN` defined at module level (no import dependency).
- **Schema compliance**: Supports nested types: `array`, `object`, `array[string]`, `array[object]`. Checks `examples` items for string type.

## Validator prompt hints

Type-specific guidance appended to validator prompt:
- **code_analysis**: LLM metrics fields (finding_accuracy, invented_bug_count, etc.)
- **speech_to_text_postprocess**: "Se formato corretto, semantic_score >= 0.7. MAI score 0 se task eseguito."
- **rag_qa**: "completeness misura fatti presenti nella risposta. N fatti richiesti e tutti presenti → completeness=1.0."

## No tooling

No linter, formatter, typechecker, pre-commit, or CI. No `pyproject.toml`, `pytest.ini`, or `conftest.py`. Only `requirements.txt` (11 deps).

## Language

Codebase is in Italian (comments, UI, docstrings, labels). Test expectations and variable names are in English.

## Test suite

- `tests/__init__.py` is empty. Tests import from `app.services.*` using absolute paths.
- Run with `pytest tests/ -v` from project root. Standalone: `python tests/test_*.py`.
- Requires `APP_SECRET_KEY` in env.
- 10 test files, ~141 tests covering: benchmark integrity, formula matching, prompt quality, seed library quality, validation scoring, validator robustness, metric classification, coherence regression, code analysis, image description, contextual insight.
