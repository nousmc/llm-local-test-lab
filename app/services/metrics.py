import re
import json
import datetime
import unicodedata
from difflib import SequenceMatcher

FILLER_TERMS_LIST = ["emh", "ehm", "uhm", "mhm", "eh", "ah", "mh", "mmh", "beh", "mah"]
_FILLER_PATTERN = re.compile(r'\b(' + '|'.join(FILLER_TERMS_LIST) + r')\b')


TECHNICAL_RESPONSE_FIELDS = {
    "answer", "confidence", "missing_information", "assumptions",
    "citations", "warnings", "notes", "metadata"
}


def normalize_value(val):
    if val is None:
        return None
    if isinstance(val, str):
        return val.strip()
    return val


def values_equal(expected_val, actual_val) -> bool:
    exp = normalize_value(expected_val)
    act = normalize_value(actual_val)

    if exp is None and act is None:
        return True
    if exp is None or act is None:
        return False
    if exp == "" and act == "":
        return True

    if isinstance(exp, (int, float)) or isinstance(act, (int, float)):
        try:
            return abs(float(exp) - float(act)) < 1e-9
        except (ValueError, TypeError):
            pass

    if isinstance(exp, str) and isinstance(act, str):
        try:
            d1 = _parse_date(exp)
            d2 = _parse_date(act)
            if d1 and d2:
                return d1 == d2
        except Exception:
            pass
        return exp.lower().strip() == act.lower().strip()

    if isinstance(exp, str) and isinstance(act, str):
        try:
            d1 = _parse_date(exp)
            d2 = _parse_date(act)
            if d1 and d2:
                return d1 == d2
        except Exception:
            pass

    return exp == act


def _parse_date(s: str) -> str | None:
    formats = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
        "%Y%m%d", "%d %B %Y", "%d %b %Y",
    ]
    s = s.strip()
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def compute_exact_match(expected: str, actual: str) -> float:
    if not expected or not actual:
        return 0.0
    return 1.0 if expected.strip().lower() == actual.strip().lower() else 0.0


def compute_lexical_similarity(expected: str, actual: str) -> float:
    if not expected or not actual:
        return 0.0
    return round(SequenceMatcher(None, expected.lower(), actual.lower()).ratio(), 4)


compute_semantic_similarity = compute_lexical_similarity  # DEPRECATED legacy alias


def check_json_validity(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def extract_json_from_text(text: str) -> str | None:
    text = text.strip()
    if text.startswith("{"):
        json_end = text.rfind("}")
        if json_end != -1:
            try:
                parsed = json.loads(text[: json_end + 1])
                return json.dumps(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        try:
            parsed = json.loads(text[brace_start: brace_end + 1])
            return json.dumps(parsed)
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def extract_answer_data(response_json: str) -> dict | None:
    try:
        data = json.loads(response_json)
        if isinstance(data, dict):
            answer = data.get("answer", data)
            if isinstance(answer, dict):
                return answer
            if isinstance(data, dict) and "answer" in data:
                return data
            return data
        return data
    except Exception:
        return None


def _check_top_level_wrapper(actual_json: str) -> tuple[bool, list[str]]:
    issues = []
    try:
        data = json.loads(actual_json)
    except Exception:
        return False, ["invalid_json"]
    if not isinstance(data, dict):
        return False, ["schema_not_object"]
    top_expected = {"confidence", "missing_information", "assumptions", "citations", "warnings"}
    answer = data.get("answer")
    if isinstance(answer, dict):
        leaked = [k for k in answer if k in top_expected]
        if leaked:
            issues.append(f"technical_fields_inside_answer: {leaked}")
    return len(issues) == 0, issues


def _validate_examples_schema(examples) -> tuple[bool, int]:
    if not isinstance(examples, list):
        return False, 0
    non_string = sum(1 for e in examples if not isinstance(e, str))
    return non_string == 0, non_string


def compute_schema_compliance(actual_json: str, schema: dict) -> tuple[bool, list[str]]:
    violations = []
    try:
        actual = json.loads(actual_json)
    except Exception:
        return False, ["invalid_json"]

    wrapper_ok, wrapper_issues = _check_top_level_wrapper(actual_json)
    violations.extend(wrapper_issues)

    answer = actual.get("answer", actual) if isinstance(actual, dict) else actual
    if not isinstance(answer, dict):
        return False, ["schema_not_object"]

    # Check examples schema inside answer
    examples = answer.get("examples")
    if examples is not None:
        if not isinstance(examples, list):
            violations.append("examples_not_list")
        else:
            non_string = sum(1 for e in examples if not isinstance(e, str))
            if non_string > 0:
                violations.append(f"examples_item_type_mismatch:{non_string}")

    for field, expected_type in schema.items():
        if field not in answer:
            violations.append(f"missing_field:{field}")
            continue
        value = answer[field]
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "date": str,
            "array": list,
            "object": dict,
        }
        if expected_type in type_map:
            py_type = type_map[expected_type]
            if value is None:
                continue
            if not isinstance(value, py_type):
                violations.append(f"type_mismatch:{field}:expected_{expected_type}")
        elif expected_type.startswith("array[") and expected_type.endswith("]"):
            if not isinstance(value, list):
                violations.append(f"type_mismatch:{field}:expected_{expected_type}")
            else:
                inner = expected_type[6:-1].strip()
                inner_type = type_map.get(inner)
                if inner_type:
                    bad = sum(1 for item in value if not isinstance(item, inner_type))
                    if bad > 0:
                        violations.append(f"array_item_type_mismatch:{field}:expected_{inner_type}:count_{bad}")
        else:
            violations.append(f"unknown_type:{field}:{expected_type}")

    return len(violations) == 0, violations


def compute_field_accuracy(expected_json: str, actual_json: str, required_fields: list[str] | None = None) -> dict:
    result = {
        "field_accuracy": 0.0,
        "missing_fields": [],
        "hallucinated_fields": [],
        "incorrect_fields": [],
        "correct_fields": 0,
        "total_expected": 0,
    }
    try:
        expected = json.loads(expected_json)
        actual = json.loads(actual_json)
    except Exception:
        return result

    if not isinstance(expected, dict):
        return result

    if not isinstance(actual, dict):
        return result

    if isinstance(expected.get("expected"), dict):
        expected_data = expected["expected"]
    elif isinstance(expected.get("expected_fields"), dict):
        expected_data = expected["expected_fields"]
    else:
        expected_data = {
            k: v for k, v in expected.items()
            if k not in {
                "allowed_labels", "required_fields", "schema", "rubric",
                "normalization", "expected_text", "answer_facts",
                "must_cite_context", "answer_absent", "required_points",
                "forbidden_points", "max_words", "format", "constraints",
                "target", "tests_should_pass", "must_preserve_behavior",
                "expected_findings", "expected_recommendations",
                "must_include", "style", "language", "required_objects",
                "forbidden_objects", "clean_transcript_contains", "action_items"
            }
        }

    required = required_fields if required_fields else expected.get("required_fields") or list(expected_data.keys())
    required = [r for r in required if r not in TECHNICAL_RESPONSE_FIELDS]

    schema_fields = expected.get("schema", {}) if isinstance(expected.get("schema"), dict) else {}
    allowed_fields = set(schema_fields.keys()) or set(expected_data.keys()) or set(required)

    answer = actual.get("answer", actual) if isinstance(actual, dict) and "answer" in actual else actual
    if not isinstance(answer, dict):
        answer = actual

    result["total_expected"] = len(required)

    correct = 0
    for field in required:
        if field not in answer:
            result["missing_fields"].append(field)
        elif values_equal(expected_data.get(field), answer.get(field)):
            correct += 1
        else:
            result["incorrect_fields"].append(field)

    result["correct_fields"] = correct
    if result["total_expected"] > 0:
        result["field_accuracy"] = round(correct / result["total_expected"], 4)

    answer_keys = {k for k in answer.keys() if k not in TECHNICAL_RESPONSE_FIELDS}
    extra_fields = answer_keys - allowed_fields
    result["hallucinated_fields"] = list(extra_fields)

    return result


def _normalize_text_for_match(text: str) -> str:
    text = (text or "").lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[\u0300-\u036f]", "", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _contains_fuzzy(haystack: str, needle: str) -> bool:
    h = _normalize_text_for_match(haystack)
    n = _normalize_text_for_match(needle)
    if not n:
        return True
    if n in h:
        return True
    return SequenceMatcher(None, h, n).ratio() >= 0.80


def _exact_normalized_substring(haystack: str, needle: str) -> bool:
    if not haystack or not needle:
        return False
    h = _normalize_text_for_match(haystack)
    n = _normalize_text_for_match(needle)
    return n in h


def compute_rag_metrics(expected_json: str, actual_json: str, context_text: str = "") -> dict:
    result = {
        "answer_absent_correctness": 0.0,
        "answer_absent_flag_match": 0.0,
        "answer_absent_textual_absence_detected": 0.0,
        "citation_presence": 0.0,
        "citation_exact_substring_match": 0.0,
        "citation_exactness": 0.0,
        "citations_empty_count": 0.0,
        "citations_nonempty_count": 0.0,
        "top_level_citations_present": 0.0,
        "answer_text_empty_when_absent": 0.0,
        "answer_text_present_when_not_absent": 0.0,
    }
    try:
        expected = json.loads(expected_json)
        actual = json.loads(actual_json)
    except Exception:
        return result

    answer = actual.get("answer", actual) if isinstance(actual, dict) else {}
    if not isinstance(answer, dict):
        return result

    answer_text = str(answer.get("answer_text") or "")
    citations = answer.get("citations_used") or []
    if not isinstance(citations, list):
        citations = [str(citations)]

    top_level_citations = actual.get("citations") if isinstance(actual, dict) else None
    if top_level_citations is not None and isinstance(top_level_citations, list):
        non_empty_tl = [c for c in top_level_citations if str(c).strip()]
        result["top_level_citations_present"] = 1.0 if non_empty_tl else 0.0

    expected_absent = bool(expected.get("answer_absent", False))
    actual_absent = bool(answer.get("answer_absent", False))
    textual_absent = _answer_indicates_absence(answer_text)
    result["answer_absent_flag_match"] = 1.0 if expected_absent == actual_absent else 0.0
    result["answer_absent_textual_absence_detected"] = 1.0 if textual_absent else 0.0
    result["answer_absent_correctness"] = result["answer_absent_flag_match"]

    if actual_absent or textual_absent:
        result["answer_text_empty_when_absent"] = 1.0 if not answer_text.strip() else 0.0
    else:
        result["answer_text_present_when_not_absent"] = 1.0 if answer_text.strip() else 0.0

    if citations:
        non_empty = [c for c in citations if str(c).strip()]
        empty_count = len(citations) - len(non_empty)
        result["citation_presence"] = 1.0 if non_empty else 0.0
        result["citations_empty_count"] = float(empty_count)
        result["citations_nonempty_count"] = float(len(non_empty))

        exact = sum(1 for c in non_empty if _exact_normalized_substring(context_text, str(c)))
        result["citation_exact_substring_match"] = round(exact / len(citations), 4) if citations else 0.0
        result["citation_exactness"] = result["citation_exact_substring_match"]

    return result


def _answer_indicates_absence(text: str) -> bool:
    normalized = _normalize_text_for_match(text)
    absence_patterns = [
        "non e specificato", "non è specificato", "non specificato",
        "non si specifica", "non viene specificato", "non specifica",
        "non presente", "non e presente", "non è presente",
        "non menzion", "non viene menzionato", "non menziona",
        "non indicato", "non viene indicato",
        "non disponibile",
        "assenza di informazioni", "nessuna informazione",
    ]
    return any(_normalize_text_for_match(pattern) in normalized for pattern in absence_patterns)
    return any(_normalize_text_for_match(pattern) in normalized for pattern in absence_patterns)


def _answer_indicates_negative(text: str) -> bool:
    normalized = _normalize_text_for_match(text)
    negative_patterns = [
        "no il documento non", "no non e presente", "no non ci sono",
        "no nessuna", "no non viene", "no non sono",
        "il documento non indica", "il documento non contiene",
        "il contesto non contiene", "il contesto non indica",
        "non sono riportat", "non sono riportate", "non è riportat",
        "non riporta", "non contiene", "non e presente alcun",
        "non indica alcun", "non risulta",
    ]
    return any(pattern in normalized for pattern in negative_patterns)


def detect_prompt_echo(answer_text: str, prompt_text: str) -> bool:
    """Detect if the model echoed prompt instructions in its answer."""
    if not answer_text or not prompt_text:
        return False
    echo_indicators = [
        "sei un modello in fase di benchmark",
        "devi completare il task richiesto",
        "rispondi esclusivamente con un json",
        "pulisci e struttura la trascrizione",
        "non aggiungere testo prima o dopo",
        "devi classificare il testo",
        "devi estrarre dati strutturati",
    ]
    answer_lower = answer_text.lower()
    return any(indicator in answer_lower for indicator in echo_indicators)


def compute_summarization_metrics(expected_json: str, actual_json: str) -> dict:
    result = {
        "max_words_respected": 1.0,
        "summary_word_count": 0.0,
        "summary_is_bulleted": 0.0,
        "key_points_is_list": 0.0,
        "key_points_count": 0.0,
        "task_format_compliance_deterministic": 0.0,
    }
    try:
        expected = json.loads(expected_json)
        actual = json.loads(actual_json)
    except Exception:
        return result
    answer = actual.get("answer", actual) if isinstance(actual, dict) else {}
    summary = str(answer.get("summary") or answer.get("answer_text") or "")
    key_points = answer.get("key_points")
    if not isinstance(key_points, list):
        key_points = []

    words = summary.split()
    result["summary_word_count"] = float(len(words))
    max_words = expected.get("max_words")
    if max_words:
        result["max_words_respected"] = 1.0 if len(words) <= int(max_words) else 0.0

    if summary.strip():
        lines = [l.strip() for l in summary.split("\n") if l.strip()]
        bullet_count = sum(1 for l in lines if l.startswith("-") or l.startswith("*") or l.startswith("•"))
        if bullet_count >= max(1, len(lines) * 0.5):
            result["summary_is_bulleted"] = 1.0

    if len(key_points) > 0:
        result["key_points_is_list"] = 1.0
        result["key_points_count"] = float(len(key_points))

    fmt_score = 0.0
    if result["max_words_respected"] > 0:
        fmt_score += 0.4
    if result["summary_is_bulleted"] > 0:
        fmt_score += 0.3
    if result["key_points_is_list"] > 0:
        fmt_score += 0.3
    result["task_format_compliance_deterministic"] = round(fmt_score, 4)
    return result


def _parse_param_name(p: dict) -> str | None:
    if not isinstance(p, dict):
        return None
    return str(p.get("name") or p.get("param") or "").strip().lower() or None


def _match_param(expected_param: dict, actual_params: list[dict]) -> bool:
    exp_name = _parse_param_name(expected_param)
    if not exp_name:
        return False
    for ap in actual_params:
        if not isinstance(ap, dict):
            continue
        act_name = _parse_param_name(ap)
        if act_name and act_name == exp_name:
            return True
    return False


def _check_google_style_sections(docstring: str) -> tuple[bool, bool, bool]:
    has_args = bool(re.search(r'\bArgs\s*:', docstring))
    has_returns = bool(re.search(r'\bReturns\s*:', docstring))
    has_raises = bool(re.search(r'\bRaises\s*:', docstring))
    return has_args, has_returns, has_raises


def _check_describes_type(description: str, expected_type: str) -> bool:
    if not description or not expected_type:
        return False
    desc_lower = _normalize_text_for_match(description)
    type_parts = [p.strip().lower() for p in re.split(r'[,\[\]]+', expected_type) if p.strip()]
    if not type_parts:
        return True
    words = set(desc_lower.split())
    matched = 0
    for part in type_parts:
        if part in words:
            matched += 1
        elif len(part) >= 4 and part in desc_lower:
            matched += 1
    return matched >= max(1, len(type_parts) - 1)


def _check_exception_coverage(actual_raises: list, expected_exceptions: list[dict]) -> tuple[int, int]:
    if not expected_exceptions:
        return 0, 0
    matched = 0
    for exc in expected_exceptions:
        exc_type = str(exc.get("type", "")).strip().lower()
        exc_condition = _normalize_text_for_match(str(exc.get("condition", "")))
        found = False
        for ar in (actual_raises or []):
            if not isinstance(ar, dict):
                continue
            ar_type = str(ar.get("type") or ar.get("exception") or "").strip().lower()
            ar_cond = _normalize_text_for_match(str(ar.get("condition") or ar.get("description") or ""))
            if exc_type and ar_type:
                if exc_type == ar_type:
                    found = True
                    break
                if exc_type in ar_type or ar_type in exc_type:
                    found = True
                    break
            if exc_condition and ar_cond and exc_condition in ar_cond:
                found = True
                break
        if found:
            matched += 1
    return matched, len(expected_exceptions)


def compute_code_documentation_metrics(expected_json: str, actual_json: str) -> dict:
    result = {
        "documentation_structure": 0.0,
        "heuristic_documentation_completeness": 0.0,
        "documentation_completeness": 0.0,
        "style_compliance": 0.0,
        "heuristic_style_compliance": 0.0,
        "missing_doc_sections_count": 0.0,
        "documented_parameters_accuracy": 0.0,
        "missing_documented_parameters_count": 0.0,
        "hallucinated_parameters_count": 0.0,
        "hallucinated_exception_count": 0.0,
        "examples_schema_violation": 0.0,
    }
    try:
        expected = json.loads(expected_json) if expected_json else {}
        actual = json.loads(actual_json)
    except Exception:
        return result

    answer = actual.get("answer", actual) if isinstance(actual, dict) else {}
    if not isinstance(answer, dict):
        return result

    expected_sections = {
        "docstring": str,
        "parameters": list,
        "returns": dict,
        "raises": list,
        "examples": list,
    }

    present = 0
    missing = []
    for field, expected_type in expected_sections.items():
        if field not in answer or not isinstance(answer[field], expected_type):
            missing.append(field)
        else:
            present += 1
    result["documentation_structure"] = round(present / len(expected_sections), 4)
    result["missing_doc_sections_count"] = float(len(missing))

    # ---- Parameter validation ----
    expected_params = expected.get("expected_parameters") or []
    actual_params = answer.get("parameters") or []
    if not isinstance(actual_params, list):
        actual_params = []
    if expected_params:
        missing_params = 0
        correct_params = 0
        for ep in expected_params:
            if not isinstance(ep, dict):
                continue
            if _match_param(ep, actual_params):
                correct_params += 1
            else:
                missing_params += 1
        total_expected_params = len(expected_params)
        result["documented_parameters_accuracy"] = round(correct_params / total_expected_params, 4) if total_expected_params else 1.0
        result["missing_documented_parameters_count"] = float(missing_params)

        actual_param_names = {_parse_param_name(ap) for ap in actual_params if isinstance(ap, dict)}
        expected_param_names = {_parse_param_name(ep) for ep in expected_params if isinstance(ep, dict)}
        hallucinated = actual_param_names - expected_param_names - {None}
        result["hallucinated_parameters_count"] = float(len(hallucinated))
    else:
        result["documented_parameters_accuracy"] = 1.0 if "parameters" not in missing else 0.0
        result["missing_documented_parameters_count"] = 0.0
        result["hallucinated_parameters_count"] = 0.0

    # ---- Examples schema validation ----
    examples = answer.get("examples")
    if examples is not None and isinstance(examples, list):
        _, non_string = _validate_examples_schema(examples)
        result["examples_schema_violation"] = float(non_string)

    # ---- Raises hallucination detection ----
    actual_raises = answer.get("raises") or []
    expected_exc = expected.get("expected_exceptions")
    if expected_exc is None:
        result["hallucinated_exception_count"] = 0.0
    elif not expected_exc:
        if isinstance(actual_raises, list) and len(actual_raises) > 0:
            result["hallucinated_exception_count"] = float(len(actual_raises))

    # ---- Completeness (checks correctness of content, not just presence) ----
    must_include = expected.get("must_include") or []
    aliases = {
        "parametri": "parameters",
        "parameters": "parameters",
        "valore restituito": "returns",
        "return": "returns",
        "returns": "returns",
        "eccezioni": "raises",
        "exceptions": "raises",
        "raises": "raises",
        "esempio": "examples",
        "esempi": "examples",
        "examples": "examples",
        "docstring": "docstring",
    }
    completeness_items = []
    if must_include:
        completeness_items = list(must_include)
    else:
        completeness_items = list(expected_sections.keys())

    total_checks = len(completeness_items)
    passed_checks = 0.0

    for item in completeness_items:
        section = aliases.get(str(item).lower().strip())
        if not section:
            if _contains_fuzzy(str(answer), str(item)):
                passed_checks += 1.0
            continue

        if section not in answer or not isinstance(answer[section], expected_sections.get(section, object)):
            continue

        val = answer[section]

        # Additional semantic checks per section
        if section == "returns":
            expected_ret = expected.get("expected_return_type")
            if expected_ret:
                ret_desc = str(val.get("description", "")) + " " + str(val.get("type", ""))
                if _check_describes_type(ret_desc, expected_ret):
                    passed_checks += 1.0
                else:
                    passed_checks += 0.4
            else:
                passed_checks += 1.0

        elif section == "raises":
            expected_exc = expected.get("expected_exceptions")
            if expected_exc is None:
                passed_checks += 1.0
            elif expected_exc:
                matched, total_exc = _check_exception_coverage(val, expected_exc)
                if total_exc > 0:
                    passed_checks += round(matched / total_exc, 4)
                else:
                    passed_checks += 1.0
            else:
                if isinstance(val, list) and len(val) > 0:
                    passed_checks += 0.0
                else:
                    passed_checks += 1.0

        elif section == "parameters":
            if expected_params:
                if result.get("documented_parameters_accuracy", 1.0) >= 1.0:
                    passed_checks += 1.0
                elif result.get("documented_parameters_accuracy", 0.0) > 0:
                    passed_checks += 0.6
                else:
                    passed_checks += 0.0
            else:
                passed_checks += 1.0

        else:
            passed_checks += 1.0

    result["heuristic_documentation_completeness"] = round(passed_checks / total_checks, 4) if total_checks else 0.0
    result["documentation_completeness"] = result["heuristic_documentation_completeness"]

    # ---- Style compliance ----
    style = str(expected.get("style", "")).lower()
    docstring = str(answer.get("docstring") or "")
    has_param_list = isinstance(answer.get("parameters"), list) and len(answer.get("parameters", []) or []) > 0
    has_return = isinstance(answer.get("returns"), dict)
    has_raises = isinstance(answer.get("raises"), list)

    has_enriched_fields = bool(expected_params or expected.get("expected_return_type") or expected.get("expected_exceptions"))

    if "google" in style and has_enriched_fields:
        style_score = 0.0
        has_args, has_ret_section, has_raise_section = _check_google_style_sections(docstring)
        if has_args:
            style_score += 0.3
        if has_ret_section:
            style_score += 0.2
        if has_raise_section:
            style_score += 0.2
        if has_param_list:
            style_score += 0.15
        if has_return:
            style_score += 0.15
        result["style_compliance"] = round(min(1.0, style_score), 4)
    elif "google" in style:
        result["style_compliance"] = 1.0 if docstring and has_param_list and has_return else 0.0
    else:
        result["style_compliance"] = 1.0 if docstring and has_param_list and has_return else 0.0
    result["heuristic_style_compliance"] = result["style_compliance"]

    return result


ALLOWED_FINDING_TYPES = {"bug", "security", "best_practice", "performance"}
ALLOWED_SEVERITIES = {"low", "medium", "high", "critical"}


def compute_code_analysis_deterministic_metrics(expected_json: str, actual_json: str, response_text: str = "") -> dict:
    result = {
        "findings_schema_valid": 0.0,
        "allowed_type_valid": 0.0,
        "allowed_severity_valid": 0.0,
        "finding_required_keys_present": 0.0,
        "language_compliance_deterministic": 0.0,
        "findings_count": 0.0,
    }
    try:
        expected = json.loads(expected_json) if expected_json else {}
        actual = json.loads(actual_json)
    except Exception:
        return result

    answer = actual.get("answer", actual) if isinstance(actual, dict) else {}
    if not isinstance(answer, dict):
        return result

    findings = answer.get("findings")
    if not isinstance(findings, list):
        findings = []

    result["findings_count"] = float(len(findings))

    if findings:
        result["findings_schema_valid"] = 1.0

    valid_type = 0
    valid_sev = 0
    valid_keys = 0
    total = len(findings)
    for f in findings:
        if not isinstance(f, dict):
            continue
        f_type = str(f.get("type") or "").strip().lower()
        f_sev = str(f.get("severity") or "").strip().lower()
        if f_type in ALLOWED_FINDING_TYPES:
            valid_type += 1
        if f_sev in ALLOWED_SEVERITIES:
            valid_sev += 1
        has_desc = isinstance(f.get("description"), str) and f["description"].strip()
        has_loc = isinstance(f.get("location"), str)
        if has_desc and has_loc:
            valid_keys += 1
        elif has_desc:
            valid_keys += 0.5

    if total > 0:
        result["allowed_type_valid"] = round(valid_type / total, 4)
        result["allowed_severity_valid"] = round(valid_sev / total, 4)
        result["finding_required_keys_present"] = round(valid_keys / total, 4)
    else:
        result["allowed_type_valid"] = 1.0
        result["allowed_severity_valid"] = 1.0
        result["finding_required_keys_present"] = 1.0

    result["language_compliance_deterministic"] = 0.0
    result["heuristic_language_compliance"] = 0.0
    expected_lang = expected.get("language")
    if expected_lang:
        response_lang = _detect_response_language(response_text)
        result["heuristic_language_compliance"] = 1.0 if response_lang == expected_lang else 0.0
        result["language_compliance_deterministic"] = result["heuristic_language_compliance"]

    return result


def _detect_response_language(text: str) -> str:
    if not text:
        return "unknown"
    filtered = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    filtered = re.sub(r'`[^`]+`', '', filtered)
    code_terms = {"bug", "security", "best_practice", "performance",
                  "low", "medium", "high", "critical",
                  "valueerror", "typeerror", "zerodivisionerror",
                  "exception", "keyboardinterrupt", "systemexit",
                  "sql injection", "xss", "csrf", "parameterized"}
    text_lower = filtered.lower()[:500]
    for ct in code_terms:
        text_lower = text_lower.replace(ct, " ")
    it_words = {" è ", " il ", " la ", " non ", " una ", " per ", " che ", " dei ", " con ", " nel ",
                " sono ", " questo ", " questa ", " codice ", " funzione ", " errore ", " deve ",
                " stato ", " già ", " anche ", " essere ", " stato ", " tutti ", " degli ", " dei "}
    en_words = {" is ", " the ", " and ", " not ", " for ", " that ", " with ", " this ",
                " should ", " must ", " code ", " function ", " error ", " already ", " also "}
    it_score = sum(1 for w in it_words if w in text_lower)
    en_score = sum(1 for w in en_words if w in text_lower)
    if it_score > en_score:
        return "it"
    elif en_score > it_score:
        return "en"
    return "unknown"


def compute_image_description_metrics(expected_json: str, actual_json: str) -> dict:
    result = {
        "required_fields_present": 0.0,
        "description_word_count": 0.0,
        "max_words_respected": 0.0,
        "objects_detected_is_list": 0.0,
        "dominant_colors_is_list": 0.0,
        "scene_type_present": 0.0,
    }
    try:
        expected = json.loads(expected_json) if expected_json else {}
        actual = json.loads(actual_json)
    except Exception:
        return result

    answer = actual.get("answer", actual) if isinstance(actual, dict) else {}
    if not isinstance(answer, dict):
        return result

    desc = str(answer.get("description") or "")
    words = desc.split()
    result["description_word_count"] = float(len(words))
    max_words = expected.get("max_words")
    if max_words:
        result["max_words_respected"] = 1.0 if len(words) <= int(max_words) else 0.0
    else:
        result["max_words_respected"] = 1.0

    objects = answer.get("objects_detected")
    if isinstance(objects, list):
        result["objects_detected_is_list"] = 1.0

    colors = answer.get("dominant_colors")
    if isinstance(colors, list):
        result["dominant_colors_is_list"] = 1.0

    scene = answer.get("scene_type")
    if isinstance(scene, str) and scene.strip():
        result["scene_type_present"] = 1.0

    required = {"description", "objects_detected", "scene_type", "dominant_colors"}
    present = sum(1 for r in required if r in answer and answer[r])
    result["required_fields_present"] = round(present / len(required), 4)

    return result


STT_ALLOWED_ENTITY_TYPES = {"person", "date", "project", "other"}


def compute_speech_to_text_postprocess_metrics(expected_json: str, actual_json: str, raw_transcript_text: str = "", prompt_text: str = "") -> dict:
    result = {
        "clean_transcript_present": 0.0,
        "action_items_is_list": 0.0,
        "action_items_schema_valid": 0.0,
        "entities_mentioned_is_list": 0.0,
        "entities_schema_valid": 0.0,
        "owner_null_or_string_valid": 0.0,
        "deadline_null_or_string_valid": 0.0,
        "filler_terms_remaining_count": 0.0,
        "prompt_echo_exact_indicator_found": 0.0,
    }
    try:
        expected = json.loads(expected_json) if expected_json else {}
        actual = json.loads(actual_json)
    except Exception:
        return result

    answer = actual.get("answer", actual) if isinstance(actual, dict) else {}
    if not isinstance(answer, dict):
        return result

    clean = str(answer.get("clean_transcript") or "")
    if clean.strip():
        result["clean_transcript_present"] = 1.0

        filler_count = len(_FILLER_PATTERN.findall(clean.lower()))
        result["filler_terms_remaining_count"] = float(filler_count)

    action_items = answer.get("action_items")
    if isinstance(action_items, list):
        result["action_items_is_list"] = 1.0
        valid = 0
        owner_ok = 0
        deadline_ok = 0
        total = len(action_items)
        for ai in action_items:
            if not isinstance(ai, dict):
                continue
            owner = ai.get("owner")
            task = ai.get("task")
            deadline = ai.get("deadline")
            has_owner = owner is None or isinstance(owner, str)
            has_task = isinstance(task, str) and task.strip()
            has_deadline = deadline is None or isinstance(deadline, str)
            if has_owner and has_task:
                valid += 1
            if has_owner:
                owner_ok += 1
            if has_deadline:
                deadline_ok += 1
        if total > 0:
            result["action_items_schema_valid"] = round(valid / total, 4)
            result["owner_null_or_string_valid"] = round(owner_ok / total, 4)
            result["deadline_null_or_string_valid"] = round(deadline_ok / total, 4)
        else:
            result["action_items_schema_valid"] = 1.0
            result["owner_null_or_string_valid"] = 1.0
            result["deadline_null_or_string_valid"] = 1.0

    entities = answer.get("entities_mentioned")
    if isinstance(entities, list):
        result["entities_mentioned_is_list"] = 1.0
        valid = 0
        total = len(entities)
        for e in entities:
            if not isinstance(e, dict):
                continue
            name = e.get("name")
            etype = str(e.get("type") or "").strip().lower()
            has_name = isinstance(name, str) and name.strip()
            has_type = etype in STT_ALLOWED_ENTITY_TYPES
            if has_name and has_type:
                valid += 1
        result["entities_schema_valid"] = round(valid / total, 4) if total > 0 else 1.0

    if prompt_text and clean.strip():
        if detect_prompt_echo(clean, prompt_text):
            result["prompt_echo_exact_indicator_found"] = 1.0

    return result


ALLOWED_DEPTH_VALUES = {"tecnico", "commerciale", "legale", "comunicazione", "strategico"}


def compute_contextual_insight_metrics(expected_json: str, actual_json: str) -> dict:
    result = {
        "insights_is_list": 0.0,
        "insight_count": 0.0,
        "insight_count_in_range": 0.0,
        "references_to_context_is_list": 0.0,
        "references_to_context_count": 0.0,
        "follow_up_is_list": 0.0,
        "follow_up_present": 0.0,
        "depth_valid": 0.0,
        "must_include_coverage": 0.0,
        "must_avoid_violation": 0.0,
    }
    try:
        expected = json.loads(expected_json) if expected_json else {}
        actual = json.loads(actual_json)
    except Exception:
        return result

    answer = actual.get("answer", actual) if isinstance(actual, dict) else {}
    if not isinstance(answer, dict):
        return result

    insights = answer.get("insights") or []
    if isinstance(insights, list):
        result["insights_is_list"] = 1.0
        non_empty = [s for s in insights if isinstance(s, str) and s.strip()]
        result["insight_count"] = float(len(non_empty))
        exp_min = expected.get("expected_insight_count", {}).get("min", 3) if isinstance(expected.get("expected_insight_count"), dict) else 3
        exp_max = expected.get("expected_insight_count", {}).get("max", 8) if isinstance(expected.get("expected_insight_count"), dict) else 8
        result["insight_count_in_range"] = 1.0 if exp_min <= len(non_empty) <= exp_max else 0.0

    refs = answer.get("references_to_context") or []
    if isinstance(refs, list):
        result["references_to_context_is_list"] = 1.0
        non_empty_refs = [r for r in refs if isinstance(r, str) and r.strip()]
        result["references_to_context_count"] = float(len(non_empty_refs))

    fu = answer.get("follow_up_questions") or []
    if isinstance(fu, list):
        result["follow_up_is_list"] = 1.0
        non_empty_fu = [q for q in fu if isinstance(q, str) and q.strip()]
        if non_empty_fu:
            result["follow_up_present"] = 1.0

    depth = str(answer.get("depth") or "").strip()
    if depth:
        result["depth_valid"] = 1.0

    must_include = expected.get("must_include_themes") or []
    if must_include:
        text = " ".join(str(v) for v in answer.values()) if isinstance(answer, dict) else str(answer)
        covered = sum(1 for theme in must_include if _contains_fuzzy(text, str(theme)))
        result["must_include_coverage"] = round(covered / len(must_include), 4)

    must_avoid = expected.get("must_avoid_themes") or []
    if must_avoid:
        text = " ".join(str(v) for v in answer.values()) if isinstance(answer, dict) else str(answer)
        violations = sum(1 for theme in must_avoid if _contains_fuzzy(text, str(theme)))
        result["must_avoid_violation"] = float(violations)

    return result


def check_prompt_contamination(prompt: str, expected_output_json: str | None, allowed_source_text: str = "") -> tuple[bool, str]:
    if not expected_output_json:
        return False, ""
    try:
        expected = json.loads(expected_output_json)
    except Exception:
        return False, ""

    prompt_lower = prompt.lower()
    allowed_source_lower = (allowed_source_text or "").lower()
    issues = []

    if isinstance(expected, dict):
        exp_data = expected.get("expected", expected)
        if isinstance(exp_data, dict):
            for key, val in exp_data.items():
                if key in {"style", "language", "format", "max_words", "target", "constraints", "tests_should_pass", "must_preserve_behavior", "depth", "domain", "must_include_themes", "must_avoid_themes", "expected_insight_count", "quality_criteria"}:
                    continue
                if key == "label" and _is_allowed_class_value(prompt, expected, val):
                    continue
                if isinstance(val, str) and val.lower() in allowed_source_lower:
                    continue
                if isinstance(val, str) and len(val) > 5 and val.lower() in prompt_lower:
                    issues.append(f"Campo '{key}' con valore '{val[:30]}...' trovato nel prompt")
                elif isinstance(val, (int, float)) and str(val) in prompt_lower:
                    pass
        if "expected_labels" in expected:
            labels = expected.get("expected_labels", {})
            for k, v in labels.items():
                if isinstance(v, str) and _is_allowed_class_value(prompt, expected, v):
                    continue
                if isinstance(v, str) and v.lower() in prompt_lower:
                    issues.append(f"Expected label '{v}' per '{k}' nel prompt")

    if issues:
        return True, "; ".join(issues)
    return False, ""


def _is_allowed_class_value(prompt: str, expected: dict, value) -> bool:
    if not isinstance(value, str):
        return False

    allowed_labels = expected.get("allowed_labels") or []
    if isinstance(allowed_labels, str):
        allowed_labels = [x.strip() for x in allowed_labels.split(",") if x.strip()]

    if value in allowed_labels:
        return True

    lower_prompt = prompt.lower()
    lower_value = value.lower()
    if "classi ammesse" in lower_prompt:
        # The allowed-class section is part of the task specification, not a leaked answer.
        section = lower_prompt.split("classi ammesse", 1)[1].split("input da classificare", 1)[0]
        return lower_value in section

    return False


def classify_error(error_msg: str) -> str:
    if not error_msg:
        return ""
    msg = error_msg.lower()
    if "contaminat" in msg:
        return "prompt_contamination"
    if "timeout" in msg:
        return "timeout"
    if "rate limit" in msg:
        return "rate_limit"
    if "auth" in msg or "unauthorized" in msg or "forbidden" in msg:
        return "auth_error"
    if "connect" in msg or "network" in msg or "refused" in msg:
        return "network_error"
    if "not found" in msg or "model" in msg:
        return "model_not_found"
    if "provider" in msg or "unavailable" in msg:
        return "provider_unavailable"
    if "json" in msg:
        return "invalid_json"
    return "unknown_error"
