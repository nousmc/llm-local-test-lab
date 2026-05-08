import json
import time
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import TestRun, TestResult, ValidationResult, MetricResult, TestCase, ConfiguredModel, TestType
from .config_loader import get_validator_config, get_execution_config, get_thresholds_config
from .provider_router import get_provider_client
from .validator import validate_response
from .metrics import (
    compute_exact_match,
    compute_lexical_similarity,
    check_json_validity,
    extract_json_from_text,
    compute_field_accuracy,
    compute_schema_compliance,
    classify_error,
    compute_rag_metrics,
    compute_summarization_metrics,
    compute_code_documentation_metrics,
    compute_code_analysis_deterministic_metrics,
    compute_image_description_metrics,
    compute_speech_to_text_postprocess_metrics,
)

from .prompt_builder import (
    PROMPT_TEMPLATES,
    MESSAGE_CONTAINER_TEMPLATE,
    ST_HEADER,
    _extract_expected_schema,
    _build_field_list,
    _build_field_placeholders,
    _get_allowed_labels,
    _get_constraints_text,
    _get_format_constraint,
    _get_length_constraint,
    validate_prompt,
)

BENCHMARK_PROMPT_TEMPLATE = ST_HEADER


def _render_prompt_template(template: str, test_case: TestCase, test_type: TestType, expected: dict) -> str:
    replacements = {
        "test_type": test_type.label if test_type else test_case.test_type_id,
        "instructions": test_case.description or (test_type.label if test_type else test_case.test_type_id),
        "input_text": test_case.input_text or "",
        "context": test_case.context_text or "(nessun contesto fornito)",
        "field_list": _build_field_list(expected),
        "field_placeholders": _build_field_placeholders(expected),
        "allowed_labels": _get_allowed_labels(expected),
        "target": expected.get("target", "migliorare il codice"),
        "constraints": _get_constraints_text(expected),
        "format_constraint": _get_format_constraint(expected),
        "length_constraint": _get_length_constraint(expected),
        "style": expected.get("style", "descrizione_neutra"),
        "language": expected.get("language", "it"),
        "doc_style": expected.get("style", "docstring_google"),
        "answer_absent_rule": "IMPORTANTE: se la risposta NON e presente nel contesto, imposta answer_absent a true e lascia answer_text vuoto."
        if expected.get("answer_absent") is not None else "",
    }
    prompt = template
    for key, value in replacements.items():
        prompt = prompt.replace("{" + key + "}", str(value))
        prompt = prompt.replace("{{ " + key + " }}", str(value))
        prompt = prompt.replace("{{" + key + "}}", str(value))
    return prompt


def _build_generated_prompt(test_case: TestCase, test_type: TestType) -> str:
    tid = test_type.id if test_type else test_case.test_type_id
    template = PROMPT_TEMPLATES.get(tid)

    if not template:
        template = PROMPT_TEMPLATES.get("classification")
        tid = "classification"

    expected = _extract_expected_schema(test_case.expected_output_json)
    return _render_prompt_template(template, test_case, test_type, expected)


def _build_prompt(test_case: TestCase, test_type: TestType) -> str:
    expected = _extract_expected_schema(test_case.expected_output_json)
    if test_case.user_prompt_template and test_case.user_prompt_template.strip():
        return _render_prompt_template(test_case.user_prompt_template, test_case, test_type, expected)
    return _build_generated_prompt(test_case, test_type)


def _compute_deterministic_metrics(
    response_text: str,
    response_json: str | None,
    expected_json: str | None,
    expected_text: str | None,
    test_type: TestType,
) -> list[dict]:
    results = []

    exact_match = compute_exact_match(expected_text or "", response_text)
    results.append({"name": "exact_match", "value": exact_match})

    if response_json:
        results.append({"name": "json_validity", "value": 1.0})
        if expected_json:
            try:
                schema = json.loads(expected_json)
                if isinstance(schema, dict):
                    s_ok, _ = compute_schema_compliance(response_json, schema)
                    results.append({"name": "schema_compliance", "value": 1.0 if s_ok else 0.0})

                    field_result = compute_field_accuracy(expected_json, response_json)
                    results.append({"name": "field_accuracy", "value": field_result["field_accuracy"]})
                    results.append({"name": "missing_fields_count", "value": float(len(field_result["missing_fields"]))})
                    results.append({"name": "hallucinated_fields_count", "value": float(len(field_result["hallucinated_fields"]))})
            except Exception:
                pass
    else:
        results.append({"name": "json_validity", "value": 0.0})

    similarity = compute_lexical_similarity(expected_text or "", response_text)
    results.append({"name": "lexical_similarity", "value": similarity})
    results.append({"name": "semantic_similarity", "value": similarity})

    return results


def _compute_final_score(
    deterministic_score: float,
    validator_score: float | None,
    format_score: float | None,
    latency_ms: float,
    max_latency_ms: float,
    has_invalid_json: bool,
    has_schema_violation: bool,
    hallucination_detected: bool,
    refusal_detected: bool,
    error_type: str | None,
    tokens_per_second: float | None,
    estimated_cost: float | None,
    test_type_id: str = "",
    deterministic_is_perfect: bool = False,
    validator_conflict: bool = False,
) -> float:
    if error_type in ("timeout", "provider_unavailable"):
        return 0.0

    # ---- Task-class detection ----
    STRUCTURED_PURE = {"classification", "data_extraction", "ocr_extraction"}
    HYBRID = {"code_analysis", "code_documentation", "refactoring", "speech_to_text_postprocess"}
    SEMANTIC = {"rag_qa", "summarization", "image_description"}

    if test_type_id in STRUCTURED_PURE:
        det_weight, val_weight, fmt_weight = 0.50, 0.25, 0.10
    elif test_type_id in HYBRID:
        det_weight, val_weight, fmt_weight = 0.35, 0.40, 0.10
    else:
        det_weight, val_weight, fmt_weight = 0.30, 0.45, 0.10
    lat_weight, stab_weight, cost_weight = 0.05, 0.05, 0.05

    # ---- Cap penalties ----
    if has_invalid_json:
        cap = 0.30
    elif has_schema_violation:
        cap = 0.50
    elif refusal_detected:
        cap = 0.10
    else:
        cap = None

    # ---- Perfect deterministic with validator agreement ----
    if (
        deterministic_is_perfect
        and not has_invalid_json
        and not has_schema_violation
        and not hallucination_detected
        and not refusal_detected
        and not error_type
        and (validator_score is None or validator_score >= 0.90)
        and (format_score is None or format_score >= 0.90)
    ):
        return 1.0

    # ---- Validator conflict protection ----
    if deterministic_is_perfect and validator_conflict and not has_invalid_json and not has_schema_violation and not error_type:
        if test_type_id in STRUCTURED_PURE:
            return max(0.90, round(float(deterministic_score or 0.0), 4))
        elif test_type_id in HYBRID:
            return max(0.85, round(float(deterministic_score or 0.0), 4))
        else:
            return max(0.75, round(float(deterministic_score or 0.0), 4))

    latency_score = max(0, 1.0 - (latency_ms / max_latency_ms)) if max_latency_ms > 0 else 1.0
    stability_score = 1.0 if not error_type else 0.0
    cost_score = 0.5
    if estimated_cost is not None and estimated_cost >= 0:
        cost_score = max(0, 1.0 - estimated_cost / 0.01)

    if deterministic_is_perfect and validator_conflict:
        val_weight = 0.0
        fmt_weight = 0.0

    components, weights = [], []
    if deterministic_score is not None:
        components.append(deterministic_score); weights.append(det_weight)
    if validator_score is not None and val_weight > 0:
        components.append(validator_score); weights.append(val_weight)
    if format_score is not None:
        components.append(format_score); weights.append(fmt_weight)
    components.append(latency_score); weights.append(lat_weight)
    components.append(stability_score); weights.append(stab_weight)
    components.append(cost_score); weights.append(cost_weight)

    total_weight = sum(weights)
    if total_weight > 0:
        normalized = [w / total_weight for w in weights]
        base_score = sum(c * nw for c, nw in zip(components, normalized))
    else:
        base_score = 0.0

    final = round(base_score, 4)
    if cap is not None:
        final = min(final, cap)
    return max(0.0, final)


STRUCTURED_TEST_TYPES = {"classification", "data_extraction", "ocr_extraction"}
HYBRID_TEST_TYPES = {"code_analysis", "code_documentation", "refactoring", "speech_to_text_postprocess"}
SEMANTIC_TEST_TYPES = {"rag_qa", "summarization", "image_description"}

STRUCTURE_ONLY_TYPES = {"code_documentation", "code_analysis", "refactoring"}


def _infer_schema_from_expected(expected: dict) -> dict:
    if isinstance(expected.get("schema"), dict):
        return expected["schema"]

    source = expected.get("expected") or expected.get("expected_fields") or {}
    if not isinstance(source, dict):
        return {}

    schema = {}
    for key, value in source.items():
        if isinstance(value, bool):
            schema[key] = "boolean"
        elif isinstance(value, int) and not isinstance(value, bool):
            schema[key] = "integer"
        elif isinstance(value, float):
            schema[key] = "number"
        elif key.lower() in {"date", "deadline", "created_at", "updated_at"}:
            schema[key] = "date"
        else:
            schema[key] = "string"
    return schema


def _metric_value(metrics: list[dict], name: str, default: float = 0.0) -> float:
    for metric in metrics:
        if metric["name"] == name:
            return float(metric["value"] or 0.0)
    return default


def _compute_deterministic_score_for_type(test_type_id: str, metrics: list[dict]) -> float:
    if test_type_id == "code_documentation":
        json_validity = _metric_value(metrics, "json_validity")
        structure = _metric_value(metrics, "documentation_structure")
        completeness = _metric_value(metrics, "heuristic_documentation_completeness",
                                       _metric_value(metrics, "documentation_completeness"))
        style = _metric_value(metrics, "style_compliance")
        missing = _metric_value(metrics, "missing_doc_sections_count")
        hallucinated_params = _metric_value(metrics, "hallucinated_parameters_count", 0.0)
        missing_params = _metric_value(metrics, "missing_documented_parameters_count", 0.0)
        hallucinated_exc = _metric_value(metrics, "hallucinated_exception_count", 0.0)
        examples_violation = _metric_value(metrics, "examples_schema_violation", 0.0)
        score = 0.20 * json_validity + 0.35 * structure + 0.35 * completeness + 0.10 * style
        penalty = missing * 0.03 + hallucinated_params * 0.05 + missing_params * 0.05 + hallucinated_exc * 0.10 + examples_violation * 0.05
        return round(max(0.0, score - min(0.25, penalty)), 4)

    if test_type_id in STRUCTURED_TEST_TYPES:
        json_validity = _metric_value(metrics, "json_validity")
        schema_compliance = _metric_value(metrics, "schema_compliance", 1.0)
        field_accuracy = _metric_value(metrics, "field_accuracy", 0.0)
        missing = _metric_value(metrics, "missing_fields_count")
        extra = _metric_value(metrics, "extra_fields_count")
        incorrect = _metric_value(metrics, "incorrect_fields_count")
        score = 0.25 * json_validity + 0.25 * schema_compliance + 0.50 * field_accuracy
        penalty = min(0.25, 0.05 * missing + 0.05 * extra + 0.05 * incorrect)
        return round(max(0.0, score - penalty), 4)

    if test_type_id == "rag_qa":
        absent = _metric_value(metrics, "answer_absent_correctness")
        json_validity = _metric_value(metrics, "json_validity")
        score = 0.30 * json_validity + 0.70 * absent
        return round(max(0.0, score), 4)

    if test_type_id in ("code_analysis", "refactoring"):
        json_validity = _metric_value(metrics, "json_validity")
        schema = _metric_value(metrics, "schema_compliance", 1.0)
        if test_type_id == "code_analysis":
            findings_schema = _metric_value(metrics, "findings_schema_valid", 1.0)
            type_valid = _metric_value(metrics, "allowed_type_valid", 1.0)
            sev_valid = _metric_value(metrics, "allowed_severity_valid", 1.0)
            lang = _metric_value(metrics, "language_compliance_deterministic", 1.0)
            score = 0.15 * json_validity + 0.15 * schema + 0.15 * findings_schema + 0.15 * type_valid + 0.15 * sev_valid + 0.05 * lang
            return round(max(0.0, score), 4)
        similarity = _metric_value(metrics, "lexical_similarity",
                                    _metric_value(metrics, "semantic_similarity", 0.0))
        return round(0.15 * json_validity + 0.15 * schema + 0.20 * similarity, 4)

    if test_type_id == "speech_to_text_postprocess":
        json_validity = _metric_value(metrics, "json_validity")
        schema = _metric_value(metrics, "schema_compliance", 1.0)
        clean_present = _metric_value(metrics, "clean_transcript_present", 1.0)
        action_schema = _metric_value(metrics, "action_items_schema_valid", 1.0)
        entity_schema = _metric_value(metrics, "entities_schema_valid", 1.0)
        filler = _metric_value(metrics, "filler_terms_remaining_count")
        prompt_echo = _metric_value(metrics, "prompt_echo_exact_indicator_found")
        eco_penalty = 0.15 if prompt_echo > 0 else 0.0
        score = 0.15 * json_validity + 0.15 * schema + 0.25 * clean_present + 0.15 * action_schema + 0.15 * entity_schema + 0.15 * (1.0 - min(filler / 10, 1.0))
        return round(max(0.0, score - eco_penalty), 4)

    if test_type_id == "summarization":
        max_words = _metric_value(metrics, "max_words_respected", 1.0)
        json_validity = _metric_value(metrics, "json_validity")
        score = 0.30 * json_validity + 0.70 * max_words
        return round(max(0.0, score), 4)

    if test_type_id == "image_description":
        json_validity = _metric_value(metrics, "json_validity")
        required_present = _metric_value(metrics, "required_fields_present", 1.0)
        max_words = _metric_value(metrics, "max_words_respected", 1.0)
        score = 0.20 * json_validity + 0.40 * required_present + 0.40 * max_words
        return round(max(0.0, score), 4)

    exact = _metric_value(metrics, "exact_match")
    similarity = _metric_value(metrics, "semantic_similarity")
    json_validity = _metric_value(metrics, "json_validity")
    return round(0.15 * json_validity + 0.25 * exact + 0.60 * similarity, 4)


async def execute_test_run(run_id: int):
    db = SessionLocal()
    try:
        run = db.query(TestRun).filter(TestRun.id == run_id).first()
        if not run or run.status != "running":
            return

        exec_cfg = get_execution_config()
        thresholds = get_thresholds_config()
        parallelism = exec_cfg.get("parallelism", 2)
        retry_attempts = exec_cfg.get("retry_attempts", 2)
        max_latency = thresholds.get("max_latency_ms_warning", 30000)

        model_ids = [str(mid) for mid in json.loads(run.selected_model_ids_json or "[]") if str(mid).strip()]
        test_case_ids = [int(tid) for tid in json.loads(run.selected_test_case_ids_json or "[]")]

        if not model_ids or not test_case_ids:
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            run.execution_config_json = json.dumps({
                "error": "Run senza modelli o test case selezionati. Nessun fallback automatico al primo modello abilitato.",
                "selected_model_ids": model_ids,
                "selected_test_case_ids": test_case_ids,
            })
            db.commit()
            return

        models = db.query(ConfiguredModel).filter(
            ConfiguredModel.id.in_(model_ids),
            ConfiguredModel.enabled == True,
        ).all()
        models_by_id = {m.id: m for m in models}
        models = [models_by_id[mid] for mid in model_ids if mid in models_by_id]

        missing_models = [mid for mid in model_ids if mid not in models_by_id]
        if missing_models:
            run.execution_config_json = json.dumps({
                "warning": "Alcuni modelli selezionati non esistono o sono disabilitati e non verranno eseguiti",
                "missing_or_disabled_model_ids": missing_models,
                "executed_model_ids": [m.id for m in models],
            })
            db.commit()

        if not models:
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            run.execution_config_json = json.dumps({
                "error": "Nessun modello selezionato valido. Run bloccata: nessun fallback automatico.",
                "selected_model_ids": model_ids,
            })
            db.commit()
            return

        test_cases = db.query(TestCase).filter(
            TestCase.id.in_(test_case_ids),
            TestCase.enabled == True,
        ).all()
        test_cases_by_id = {tc.id: tc for tc in test_cases}
        test_cases = [test_cases_by_id[tid] for tid in test_case_ids if tid in test_cases_by_id]

        if not test_cases:
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            run.execution_config_json = json.dumps({
                "error": "Nessun test case selezionato valido. Run bloccata.",
                "selected_test_case_ids": test_case_ids,
            })
            db.commit()
            return

        print(f"Starting run {run.id} with models: {[m.model_name for m in models]}")

        tasks = []
        for tc in test_cases:
            for model in models:
                tasks.append(_run_single_test(run, tc, model, retry_attempts, max_latency, db))

        semaphore = asyncio.Semaphore(parallelism)

        async def limited(task):
            async with semaphore:
                return await task

        await asyncio.gather(*[limited(t) for t in tasks])

        total_results = db.query(TestResult).filter(TestResult.test_run_id == run_id).all()
        failed_count = sum(1 for r in total_results if r.status in ("failed", "timeout", "skipped"))
        if failed_count == len(total_results) and total_results:
            run.status = "failed"
        else:
            run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()

        try:
            from .report_builder import generate_executive_report
            report_text = await generate_executive_report(db, run_id)
            if report_text:
                run.executive_report_text = report_text
                db.commit()
        except Exception:
            pass

    except Exception as e:
        try:
            run = db.query(TestRun).filter(TestRun.id == run_id).first()
            if run:
                run.status = "failed"
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


async def _run_single_test(
    run: TestRun,
    test_case: TestCase,
    model: ConfiguredModel,
    retry_attempts: int,
    max_latency: float,
    db: Session,
):
    test_type = db.query(TestType).filter(TestType.id == test_case.test_type_id).first()
    type_label = test_type.label if test_type else test_case.test_type_id

    for attempt in range(retry_attempts):
        result = TestResult(
            test_run_id=run.id,
            test_case_id=test_case.id,
            model_id=model.id,
            provider=model.provider,
            model_name=model.model_name,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(result)
        db.commit()
        db.refresh(result)

        try:
            prompt = _build_prompt(test_case, test_type)
            result.prompt_text = prompt

            allowed_source_text = "\n".join([test_case.input_text or "", test_case.context_text or ""])
            valid, issues, status = validate_prompt(
                prompt,
                test_case.test_type_id,
                test_case.expected_output_json,
                allowed_source_text=allowed_source_text,
            )
            if not valid:
                result.error_message = f"INVALID PROMPT ({status}): {issues}"
                result.error_type = "invalid_prompt"
                result.status = "invalid_prompt"
                result.completed_at = datetime.now(timezone.utc)
                db.commit()
                mm = MetricResult(test_result_id=result.id, metric_name="invalid_prompt", metric_value=1.0,
                                  metric_payload_json=json.dumps({"issues": issues}))
                db.add(mm)
                db.commit()
                return

            prompts = [{"role": "user", "content": prompt}]
            if test_case.system_prompt:
                prompts = [{"role": "system", "content": test_case.system_prompt}, {"role": "user", "content": prompt}]

            params = json.loads(model.default_params_json or "{}")
            temperature = params.get("temperature", 0.0)
            top_p = params.get("top_p", 0.9)
            max_tokens = params.get("max_tokens", 1024)

            response_format = "json" if model.supports_json else None

            client = get_provider_client(model.provider)
            response = await client.chat(
                model=model.model_name,
                messages=prompts,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                response_format=response_format,
            )

            result.response_text = response.get("text", "")
            result.raw_response_json = json.dumps(response.get("raw", {}))
            result.latency_ms = response.get("timing", {}).get("latency_ms", 0)
            result.prompt_tokens = response.get("usage", {}).get("prompt_tokens", 0)
            result.completion_tokens = response.get("usage", {}).get("completion_tokens", 0)
            result.total_tokens = response.get("usage", {}).get("total_tokens", 0)
            result.tokens_per_second = response.get("timing", {}).get("tokens_per_second", 0)
            result.completed_at = datetime.now(timezone.utc)

            error = response.get("error")
            if error:
                result.error_message = error
                result.error_type = classify_error(error)
                if attempt < retry_attempts - 1:
                    result.status = "failed"
                    db.commit()
                    backoff = get_execution_config().get("retry_backoff_seconds", 3)
                    await asyncio.sleep(backoff)
                    continue
                result.status = "failed"
                db.commit()
                return

            extracted_json = extract_json_from_text(result.response_text)
            result.response_json = extracted_json
            has_invalid_json = extracted_json is None

            determinant_is_perfect = True
            det_metrics_result = []

            if not has_invalid_json:
                det_metrics_result.append({"name": "json_validity", "value": 1.0})
            else:
                det_metrics_result.append({"name": "json_validity", "value": 0.0})
                determinant_is_perfect = False

            has_schema_violation = False
            if not has_invalid_json and test_case.expected_output_json:
                try:
                    expected = json.loads(test_case.expected_output_json)
                    if isinstance(expected, dict):
                        schema = _infer_schema_from_expected(expected)
                        if schema and test_case.test_type_id not in STRUCTURE_ONLY_TYPES:
                            s_ok, violations = compute_schema_compliance(extracted_json, schema)
                            has_schema_violation = not s_ok
                            if has_schema_violation:
                                determinant_is_perfect = False
                            det_metrics_result.append({"name": "schema_compliance", "value": 1.0 if s_ok else 0.0})
                        else:
                            det_metrics_result.append({"name": "schema_compliance", "value": 1.0})
                except Exception:
                    pass

            if test_case.test_type_id not in STRUCTURED_TEST_TYPES:
                exact_match = compute_exact_match(test_case.expected_text or "", result.response_text)
                det_metrics_result.append({"name": "exact_match", "value": exact_match})

                similarity = compute_lexical_similarity(test_case.expected_text or "", result.response_text)
                det_metrics_result.append({"name": "semantic_similarity", "value": similarity})

            if not has_invalid_json and test_case.expected_output_json:
                try:
                    expected = json.loads(test_case.expected_output_json)
                    if test_case.test_type_id == "rag_qa":
                        rag_result = compute_rag_metrics(test_case.expected_output_json, extracted_json, test_case.context_text or "")
                        for name in ["answer_absent_correctness",
                                       "answer_absent_flag_match",
                                       "answer_absent_textual_absence_detected",
                                       "citation_presence", "citation_exact_substring_match",
                                       "citation_exactness",
                                       "citations_nonempty_count", "citations_empty_count",
                                       "top_level_citations_present",
                                       "answer_text_empty_when_absent", "answer_text_present_when_not_absent"]:
                            value = rag_result.get(name, 0)
                            det_metrics_result.append({"name": name, "value": float(value)})
                        if rag_result["answer_absent_correctness"] < 1.0:
                            determinant_is_perfect = False
                    elif test_case.test_type_id == "summarization":
                        summary_result = compute_summarization_metrics(test_case.expected_output_json, extracted_json)
                        for name in summary_result:
                            det_metrics_result.append({"name": name, "value": float(summary_result[name])})
                        if summary_result["max_words_respected"] < 1.0:
                            determinant_is_perfect = False
                    elif test_case.test_type_id == "code_documentation":
                        doc_result = compute_code_documentation_metrics(test_case.expected_output_json, extracted_json)
                        for name, value in doc_result.items():
                            det_metrics_result.append({"name": name, "value": float(value)})
                        if (
                            doc_result["documentation_structure"] < 1.0
                            or doc_result["heuristic_documentation_completeness"] < 1.0
                            or doc_result["style_compliance"] < 1.0
                            or doc_result.get("hallucinated_parameters_count", 0) > 0
                            or doc_result.get("missing_documented_parameters_count", 0) > 0
                            or doc_result.get("hallucinated_exception_count", 0) > 0
                            or doc_result.get("examples_schema_violation", 0) > 0
                        ):
                            determinant_is_perfect = False
                    elif test_case.test_type_id == "code_analysis":
                        ca_result = compute_code_analysis_deterministic_metrics(
                            test_case.expected_output_json, extracted_json, result.response_text or "")
                        for name, value in ca_result.items():
                            det_metrics_result.append({"name": name, "value": float(value)})
                        if ca_result.get("findings_schema_valid", 1.0) < 1.0:
                            determinant_is_perfect = False
                    elif test_case.test_type_id == "image_description":
                        img_result = compute_image_description_metrics(test_case.expected_output_json, extracted_json)
                        for name, value in img_result.items():
                            det_metrics_result.append({"name": name, "value": float(value)})
                        if img_result.get("required_fields_present", 1.0) < 1.0:
                            determinant_is_perfect = False
                    elif test_case.test_type_id == "speech_to_text_postprocess":
                        stt_result = compute_speech_to_text_postprocess_metrics(
                            test_case.expected_output_json, extracted_json,
                            test_case.input_text or "",
                            prompt)
                        for name, value in stt_result.items():
                            det_metrics_result.append({"name": name, "value": float(value)})
                        if stt_result.get("clean_transcript_present") != 1.0:
                            determinant_is_perfect = False
                    elif isinstance(expected, dict):
                        required_fields = expected.get("required_fields")
                        schema_fields = expected.get("schema", {})
                        if isinstance(schema_fields, dict):
                            required_fields = list(schema_fields.keys())
                        elif not required_fields and "expected" in expected:
                            required_fields = list(expected["expected"].keys())

                        field_result = compute_field_accuracy(
                            test_case.expected_output_json,
                            extracted_json,
                            required_fields=required_fields,
                        )
                        det_metrics_result.append({"name": "field_accuracy", "value": field_result["field_accuracy"]})
                        det_metrics_result.append({"name": "missing_fields_count", "value": float(len(field_result["missing_fields"]))})
                        det_metrics_result.append({"name": "extra_fields_count", "value": float(len(field_result["hallucinated_fields"]))})
                        det_metrics_result.append({"name": "hallucinated_fields_count", "value": float(len(field_result["hallucinated_fields"]))})
                        det_metrics_result.append({"name": "incorrect_fields_count", "value": float(len(field_result.get("incorrect_fields", [])))})

                        if (
                            field_result["field_accuracy"] < 1.0
                            or field_result["missing_fields"]
                            or field_result["hallucinated_fields"]
                            or field_result.get("incorrect_fields")
                        ):
                            determinant_is_perfect = False
                except Exception:
                    pass

            for m in det_metrics_result:
                metric = MetricResult(
                    test_result_id=result.id,
                    metric_name=m["name"],
                    metric_value=m["value"],
                )
                db.add(metric)

            deterministic_score = _compute_deterministic_score_for_type(test_case.test_type_id, det_metrics_result)

            validation_result = await validate_response(
                test_type=type_label,
                input_payload=test_case.input_text or "",
                expected_output=test_case.expected_output_json or test_case.expected_text or "",
                model_output=result.response_text,
                rubric=test_case.rubric_json or "",
                json_validity=not has_invalid_json,
                schema_compliance=not has_schema_violation,
            )

            validator_status = validation_result.get("validator_status", "unknown")
            validator_error_message = validation_result.get("validator_error_message", "")
            validator_raw_response = validation_result.get("validator_raw_response", "")
            validator_attempts = validation_result.get("validator_attempts", 0)
            final_score_mode = "normal"
            deterministic_passed = False
            validator_passed = False
            final_passed = False
            needs_review = False

            validator_score_val = validation_result.get("score")
            format_score_val = validation_result.get("format_score")
            validator_passed = validation_result.get("passed") or False

            if has_invalid_json or has_schema_violation:
                validator_passed = False

            if not has_invalid_json and not has_schema_violation and format_score_val is not None and format_score_val < 0.80:
                format_score_val = 0.80

            if has_invalid_json:
                format_score_val = min(format_score_val or 0.0, 0.20)
                hallucination = False
            if has_schema_violation:
                format_score_val = min(format_score_val or 0.0, 0.50)

            hallucination = validation_result.get("hallucination_detected", False)
            refusal = validation_result.get("refusal_detected", False)

            if validator_status not in ("ok", "disabled"):
                validator_score_val = None
                format_score_val = None
                hallucination = False
                refusal = False
                final_score_mode = "validator_fallback"
                db.add(MetricResult(
                    test_result_id=result.id,
                    metric_name="validator_unavailable_warning",
                    metric_value=1.0,
                    metric_payload_json=json.dumps({
                        "message": "VALIDATORE NON DISPONIBILE",
                        "validator_status": validator_status,
                        "validator_error": validator_error_message,
                        "validator_attempts": validator_attempts,
                    }),
                ))

            validator_conflict = False
            if deterministic_score >= 0.85 and validator_score_val is not None and validator_score_val <= 0.25:
                validator_conflict = True
                db.add(MetricResult(
                    test_result_id=result.id,
                    metric_name="validator_conflict_warning",
                    metric_value=1.0,
                    metric_payload_json=json.dumps({
                        "message": "DETERMINISTICO ALTO ma VALIDATORE BASSO",
                        "deterministic_score": deterministic_score,
                        "validator_score": validator_score_val,
                    }),
                ))

            enriched_validation_json = validation_result.copy()

            vr = ValidationResult(
                test_result_id=result.id,
                validator_provider=validation_result.get("validator_provider", ""),
                validator_model=validation_result.get("validator_model", ""),
                validator_status=validator_status,
                validator_error_message=validator_error_message,
                validator_raw_response=validator_raw_response,
                validator_attempts=validator_attempts,
                score=validator_score_val,
                passed=validator_passed,
                faithfulness_score=None,
                format_score=format_score_val,
                semantic_score=validation_result.get("semantic_score"),
                safety_score=validation_result.get("safety_score"),
                completeness_score=validation_result.get("completeness_score"),
                error_score=None,
                hallucination_detected=hallucination,
                refusal_detected=refusal,
                validation_json=json.dumps(enriched_validation_json),
                validation_text=validation_result.get("validation_text", ""),
            )
            db.add(vr)

            approx_cost = 0.0
            if result.completion_tokens:
                approx_cost = result.completion_tokens * (0.5 / 1_000_000)
                if result.prompt_tokens:
                    approx_cost += result.prompt_tokens * (0.15 / 1_000_000)
            result.estimated_cost = round(approx_cost, 6)

            final_score = _compute_final_score(
                deterministic_score=deterministic_score,
                validator_score=validator_score_val,
                format_score=format_score_val,
                latency_ms=result.latency_ms or 0,
                max_latency_ms=max_latency,
                has_invalid_json=has_invalid_json,
                has_schema_violation=has_schema_violation,
                hallucination_detected=hallucination,
                refusal_detected=refusal,
                error_type=result.error_type,
                tokens_per_second=result.tokens_per_second,
                estimated_cost=result.estimated_cost,
                test_type_id=test_case.test_type_id,
                deterministic_is_perfect=determinant_is_perfect,
                validator_conflict=validator_conflict,
            )

            pass_threshold = get_thresholds_config().get("default_pass_score", 0.80)
            deterministic_passed = deterministic_score >= pass_threshold
            final_passed = final_score >= pass_threshold

            if validator_conflict:
                if final_score_mode == "normal":
                    final_score_mode = "validator_conflict_adjusted"

            needs_review = False
            if validator_conflict and test_case.test_type_id in (
                "rag_qa", "summarization", "image_description",
                "code_analysis", "code_documentation", "refactoring",
                "speech_to_text_postprocess",
            ):
                needs_review = True
            if final_score_mode == "validator_fallback":
                needs_review = True

            enriched_validation_json["deterministic_passed"] = deterministic_passed
            enriched_validation_json["validator_passed"] = validator_passed
            enriched_validation_json["final_passed"] = final_passed
            enriched_validation_json["final_score_mode"] = final_score_mode
            enriched_validation_json["needs_review"] = needs_review
            vr.validation_json = json.dumps(enriched_validation_json)

            mm = MetricResult(
                test_result_id=result.id,
                metric_name="final_score",
                metric_value=final_score,
            )
            db.add(mm)

            if "deterministic_passed" not in enriched_validation_json:
                enriched_validation_json["deterministic_passed"] = deterministic_passed
            if "validator_passed" not in enriched_validation_json:
                enriched_validation_json["validator_passed"] = validator_passed
            if "final_passed" not in enriched_validation_json:
                enriched_validation_json["final_passed"] = final_passed
            if "needs_review" not in enriched_validation_json:
                enriched_validation_json["needs_review"] = needs_review
            if "final_score_mode" not in enriched_validation_json:
                enriched_validation_json["final_score_mode"] = final_score_mode
            vr.validation_json = json.dumps(enriched_validation_json)

            result.status = "completed"
            db.commit()
            return

        except Exception as e:
            result.error_message = str(e)
            result.error_type = classify_error(str(e))
            result.status = "failed"
            result.completed_at = datetime.now(timezone.utc)
            db.commit()
            if attempt < retry_attempts - 1:
                await asyncio.sleep(3)
                continue
            return
