import json

ALLOWED_EVALUATION_MODES = {"deterministic", "heuristic", "llm"}


def _d(name, category, legacy_aliases=None):
    return {
        "name": name,
        "evaluation_mode": "deterministic",
        "category": category,
        "owner": "metrics.py",
        "legacy_aliases": legacy_aliases or [],
    }


def _h(name, category, legacy_aliases=None):
    return {
        "name": name,
        "evaluation_mode": "heuristic",
        "category": category,
        "owner": "metrics.py",
        "legacy_aliases": legacy_aliases or [],
    }


def _l(name, category, legacy_aliases=None):
    return {
        "name": name,
        "evaluation_mode": "llm",
        "category": category,
        "owner": "validator.py",
        "legacy_aliases": legacy_aliases or [],
    }


METRICS_REGISTRY = {
    # ── Deterministic ──
    "json_validity":                     _d("json_validity", "format"),
    "json_extracted_validity":           _d("json_extracted_validity", "format"),
    "raw_format_compliance":             _d("raw_format_compliance", "format"),
    "schema_compliance":                _d("schema_compliance", "format"),
    "missing_fields_count":             _d("missing_fields_count", "structured"),
    "extra_fields_count":               _d("extra_fields_count", "structured"),
    "hallucinated_fields_count":         _d("extra_fields_count", "structured", ["hallucinated_fields"]),
    "incorrect_fields_count":           _d("incorrect_fields_count", "structured"),
    "required_top_level_fields_present": _d("required_top_level_fields_present", "format"),
    "technical_fields_inside_answer_count": _d("technical_fields_inside_answer_count", "format"),
    "examples_schema_violation":        _d("examples_schema_violation", "code_doc"),
    "confidence_range_valid":           _d("confidence_range_valid", "format"),

    "label_in_allowed_classes":          _d("label_in_allowed_classes", "classification"),
    "field_accuracy":                    _d("field_accuracy", "structured", ["structured_score"]),
    "per_field_exact_match":             _d("per_field_exact_match", "structured"),
    "per_field_normalized_match":        _d("per_field_normalized_match", "structured"),
    "null_correctness":                  _d("null_correctness", "structured"),
    "numeric_normalized_match":          _d("numeric_normalized_match", "structured"),
    "date_normalized_match":             _d("date_normalized_match", "structured"),
    "string_normalized_match":           _d("string_normalized_match", "structured"),

    "answer_absent_flag_match":          _d("answer_absent_flag_match", "rag"),
    "citation_presence":                 _d("citation_presence", "rag"),
    "citation_exactness_normalized":     _d("citation_exactness_normalized", "rag"),
    "citation_exactness":                _d("citation_exactness", "rag", ["citation_found"]),
    "citations_empty_count":             _d("citations_empty_count", "rag"),
    "citations_nonempty_count":          _d("citations_nonempty_count", "rag"),
    "top_level_citations_present":       _d("top_level_citations_present", "rag"),
    "answer_text_empty_when_absent":     _d("answer_text_empty_when_absent", "rag"),
    "answer_text_present_when_not_absent": _d("answer_text_present_when_not_absent", "rag"),

    "summary_word_count":                _d("summary_word_count", "summarization"),
    "max_words_respected":               _d("max_words_respected", "summarization"),
    "summary_is_bulleted":               _d("summary_is_bulleted", "summarization"),
    "key_points_is_list":                _d("key_points_is_list", "summarization"),
    "key_points_count":                  _d("key_points_count", "summarization"),
    "task_format_compliance_deterministic": _d("task_format_compliance_deterministic", "summarization"),

    "documentation_structure":           _d("documentation_structure", "code_doc"),
    "missing_doc_sections_count":        _d("missing_doc_sections_count", "code_doc"),
    "documented_parameters_accuracy":    _d("documented_parameters_accuracy", "code_doc"),
    "missing_documented_parameters_count": _d("missing_documented_parameters_count", "code_doc"),
    "hallucinated_parameters_count":     _d("hallucinated_parameters_count", "code_doc"),
    "style_sections_presence":           _d("style_sections_presence", "code_doc"),
    "google_args_section_present":       _d("google_args_section_present", "code_doc"),
    "google_returns_section_present":    _d("google_returns_section_present", "code_doc"),
    "google_raises_section_present":     _d("google_raises_section_present", "code_doc"),
    "hallucinated_exception_count":      _d("hallucinated_exception_count", "code_doc"),

    "action_items_schema_valid":         _d("action_items_schema_valid", "stt"),
    "owner_null_when_missing":           _d("owner_null_when_missing", "stt"),
    "deadline_null_when_missing":        _d("deadline_null_when_missing", "stt"),
    "entities_schema_valid":             _d("entities_schema_valid", "stt"),
    "prompt_echo_exact_indicator_found": _d("prompt_echo_exact_indicator_found", "stt"),
    "clean_transcript_present":          _d("clean_transcript_present", "stt"),
    "filler_terms_remaining_count":      _d("filler_terms_remaining_count", "stt"),

    "exact_match":                       _d("exact_match", "general", ["text_match"]),

    # ── Heuristic ──
    "lexical_similarity":                _h("lexical_similarity", "general", ["semantic_similarity"]),
    "heuristic_similarity":              _h("heuristic_similarity", "general"),
    "token_overlap":                     _h("token_overlap", "general"),
    "normalized_token_coverage":         _h("normalized_token_coverage", "general"),

    "heuristic_answer_facts_coverage":   _h("heuristic_answer_facts_coverage", "rag", ["answer_facts_coverage"]),
    "heuristic_citation_semantic_support": _h("heuristic_citation_semantic_support", "rag", ["citation_semantic_support"]),
    "heuristic_citation_coverage":       _h("heuristic_citation_coverage", "rag", ["citation_coverage"]),
    "citation_support":                  _h("citation_support", "rag"),
    "citation_derived_support":          _h("citation_derived_support", "rag"),
    "heuristic_formula_match":           _h("heuristic_formula_match", "rag"),
    "heuristic_answer_relevance":        _h("heuristic_answer_relevance", "rag"),

    "heuristic_required_points_coverage": _h("heuristic_required_points_coverage", "summarization", ["required_points_coverage"]),
    "heuristic_forbidden_points_violation": _h("heuristic_forbidden_points_violation", "summarization", ["forbidden_points_violation"]),
    "heuristic_factual_overlap":         _h("heuristic_factual_overlap", "summarization"),
    "heuristic_compression_quality":     _h("heuristic_compression_quality", "summarization"),

    "heuristic_returns_type_match":      _h("heuristic_returns_type_match", "code_doc"),
    "heuristic_raises_condition_match":  _h("heuristic_raises_condition_match", "code_doc"),
    "heuristic_docstring_content_overlap": _h("heuristic_docstring_content_overlap", "code_doc"),

    "top_level_field_misuse_heuristic":  _h("top_level_field_misuse_heuristic", "classification"),
    "invalid_missing_information_count_heuristic": _h("invalid_missing_information_count_heuristic", "classification"),

    "heuristic_clean_transcript_quality": _h("heuristic_clean_transcript_quality", "stt"),
    "heuristic_entity_overlap":          _h("heuristic_entity_overlap", "stt"),
    "heuristic_action_item_overlap":     _h("heuristic_action_item_overlap", "stt"),

    "documentation_completeness":        _h("documentation_completeness", "code_doc", ["heuristic_documentation_completeness"]),
    "style_compliance":                  _h("style_compliance", "code_doc"),

    # ── LLM-validated ──
    "semantic_score":                    _l("semantic_score", "general"),
    "completeness_score":                _l("completeness_score", "general"),
    "hallucination_detected":            _l("hallucination_detected", "general", ["validator_hallucination"]),
    "refusal_detected":                  _l("refusal_detected", "general"),
    "explicit_refusal":                  _l("explicit_refusal", "general"),
    "task_non_execution":                _l("task_non_execution", "general"),
    "prompt_echo_detected":              _l("prompt_echo_detected", "general"),
    "unsupported_claims":                _l("unsupported_claims", "general"),
    "contradictions":                    _l("contradictions", "general"),
    "contradiction_rate":                _l("contradiction_rate", "general"),
    "over_answering_detected":           _l("over_answering_detected", "general"),
    "over_answering_rate":               _l("over_answering_rate", "general"),
    "factual_consistency":               _l("factual_consistency", "general"),
    "answer_relevance":                  _l("answer_relevance", "general"),

    "llm_unsupported_claim_rate":        _l("llm_unsupported_claim_rate", "rag", ["unsupported_claim_rate"]),
    "llm_answer_facts_coverage":         _l("llm_answer_facts_coverage", "rag"),
    "llm_citation_semantic_support":     _l("llm_citation_semantic_support", "rag"),
    "llm_citation_coverage":             _l("llm_citation_coverage", "rag"),
    "llm_contradiction_rate":            _l("llm_contradiction_rate", "rag"),
    "llm_over_answering_rate":           _l("llm_over_answering_rate", "rag"),
    "llm_answer_relevance":              _l("llm_answer_relevance", "rag"),
    "main_fact_correct":                 _l("main_fact_correct", "rag"),
    "accessory_facts_missing":           _l("accessory_facts_missing", "rag"),
    "supported_extra_content":           _l("supported_extra_content", "rag"),

    "llm_required_points_coverage":      _l("llm_required_points_coverage", "summarization"),
    "llm_factual_consistency":           _l("llm_factual_consistency", "summarization"),
    "hallucinated_summary_claims":       _l("hallucinated_summary_claims", "summarization"),
    "forbidden_content_semantic_violation": _l("forbidden_content_semantic_violation", "summarization"),
    "llm_compression_quality":           _l("llm_compression_quality", "summarization"),
    "llm_summary_completeness":          _l("llm_summary_completeness", "summarization"),

    "finding_accuracy":                  _l("finding_accuracy", "code_analysis"),
    "finding_groundedness":              _l("finding_groundedness", "code_analysis"),
    "severity_correctness":             _l("severity_correctness", "code_analysis"),
    "location_specificity":             _l("location_specificity", "code_analysis"),
    "recommendation_relevance":          _l("recommendation_relevance", "code_analysis"),
    "false_positive_count":             _l("false_positive_count", "code_analysis"),
    "false_negative_count":             _l("false_negative_count", "code_analysis"),
    "invented_bug_count":               _l("invented_bug_count", "code_analysis"),

    "documentation_completeness_semantic": _l("documentation_completeness_semantic", "code_doc"),
    "returns_correctness":              _l("returns_correctness", "code_doc"),
    "raises_correctness":               _l("raises_correctness", "code_doc"),
    "parameter_description_correctness": _l("parameter_description_correctness", "code_doc"),
    "behavior_documentation_correctness": _l("behavior_documentation_correctness", "code_doc"),
    "hallucinated_behavior_count":       _l("hallucinated_behavior_count", "code_doc"),
    "hallucinated_exception_semantic_count": _l("hallucinated_exception_semantic_count", "code_doc"),

    "behavior_preservation":             _l("behavior_preservation", "refactoring"),
    "refactoring_quality":              _l("refactoring_quality", "refactoring"),
    "introduced_bug_detected":           _l("introduced_bug_detected", "refactoring"),
    "requirement_preservation":          _l("requirement_preservation", "refactoring"),

    "object_presence_correctness":       _l("object_presence_correctness", "image_description"),
    "hallucinated_object_count":         _l("hallucinated_object_count", "image_description"),
    "visual_detail_accuracy":            _l("visual_detail_accuracy", "image_description"),

    "clean_transcript_quality_semantic": _l("clean_transcript_quality_semantic", "stt"),
    "action_item_accuracy":              _l("action_item_accuracy", "stt"),
    "owner_deadline_correctness_semantic": _l("owner_deadline_correctness_semantic", "stt"),
    "entity_extraction_accuracy_semantic": _l("entity_extraction_accuracy_semantic", "stt"),

    # ── Scoring composites ──
    "final_score":                       _d("final_score", "scoring"),
    "deterministic_score":               _d("deterministic_score", "scoring"),
    "heuristic_score":                   _h("heuristic_score", "scoring"),
    "llm_score":                         _l("llm_score", "scoring"),

    "validator_unavailable_warning":     _d("validator_unavailable_warning", "diagnostic"),
    "validator_conflict_warning":        _d("validator_conflict_warning", "diagnostic"),
}


def get_metric_meta(name: str) -> dict | None:
    if name in METRICS_REGISTRY:
        return METRICS_REGISTRY[name]
    for meta in METRICS_REGISTRY.values():
        if name in meta.get("legacy_aliases", []):
            return meta
    return None


def get_evaluation_mode(name: str) -> str:
    meta = get_metric_meta(name)
    return meta["evaluation_mode"] if meta else "unknown"


def get_category(name: str) -> str:
    meta = get_metric_meta(name)
    return meta["category"] if meta else "general"


def resolve_canonical_name(name: str) -> str:
    meta = get_metric_meta(name)
    return meta["name"] if meta else name


def build_structured_metric_entry(name: str, value: float, extra: dict | None = None) -> dict:
    meta = get_metric_meta(name)
    entry = {
        "value": value,
        "evaluation_mode": meta["evaluation_mode"] if meta else "unknown",
        "category": meta["category"] if meta else "general",
    }
    if meta and meta.get("legacy_aliases"):
        entry["legacy_aliases"] = meta["legacy_aliases"]
    if extra:
        entry.update(extra)
    return entry


def get_registry_summary() -> dict:
    by_mode = {"deterministic": [], "heuristic": [], "llm": []}
    for name, meta in METRICS_REGISTRY.items():
        mode = meta["evaluation_mode"]
        if mode in by_mode:
            by_mode[mode].append(name)
    return {
        "total": len(METRICS_REGISTRY),
        "deterministic_count": len(by_mode["deterministic"]),
        "heuristic_count": len(by_mode["heuristic"]),
        "llm_count": len(by_mode["llm"]),
        "by_mode": {k: sorted(v) for k, v in by_mode.items()},
    }


FILLER_TERMS = {"emh", "ehm", "uhm", "eh", "ah", "mh", "mmh", "beh", "mah"}
