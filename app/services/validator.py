import json
import re
import asyncio

from .config_loader import get_validator_config as _get_cfg
from .provider_router import get_provider_client

VALIDATOR_PROMPT_TEMPLATE = """Sei un valutatore automatico di benchmark LLM.

Valuta la risposta del modello rispetto al risultato atteso, con precisione e gradualita.

REGOLE FONDAMENTALI:
- NON assegnare score 0.0 se la risposta contiene elementi corretti sostanziali.
- Usa punteggi graduati: 0.0=sbagliato, 0.3=parzialmente accettabile, 0.6=buono, 0.8=molto buono, 1.0=perfetto.
- Contenuti presenti nel contesto ma non richiesti = over_answering, NON hallucination.
- Claim inventati o contrari al contesto = hallucination.
- Se il modello rifiuta esplicitamente il task, segna refusal_detected=true.
- Se il modello copia istruzioni del prompt nella risposta, segna prompt_echo_detected=true.

GUIDA AI PUNTEGGI:
- format_score (0.0-1.0): valuta SOLO la qualita strutturale della risposta.
  CRITERI STRUTTURALI (formato): JSON sintatticamente valido, campi obbligatori presenti, tipi di dati corretti, struttura rispettata, nessun campo extra non richiesto.
  NON DIPENDE DA: correttezza del contenuto, label giusta o sbagliata, fatti corretti o errati.
  Una risposta con JSON valido e schema perfetto ma label sbagliata DEVE avere format_score >= 0.8.
- semantic_score (0.0-1.0): valuta SOLO la correttezza del contenuto.
  La label e giusta? Il significato corrisponde all'atteso? La risposta e pertinente?
  Una label tecnicamente valida ma sbagliata per il task DEVE avere semantic_score basso (0.2-0.3) ma format_score alto.
- completeness_score (0.0-1.0): tutti i campi richiesti sono stati compilati con valori sensati?
- score (0.0-1.0): valutazione complessiva che combina formato, semantica e completezza.
- passed (true/false): score >= 0.80?

ESEMPI DI VALUTAZIONE CORRETTA:

Esempio A - Classification con label errata:
Risposta: {"answer": {"label": "technical_support"}, "confidence": 0.9, ...}
JSON valido, schema conforme, campo label presente. Ma la label corretta e "order_status".
Valutazione: format_score=1.0, semantic_score=0.2, completeness_score=1.0, score=0.4, passed=false

Esempio B - Classification con label corretta e JSON perfetto:
Risposta: {"answer": {"label": "order_status"}, "confidence": 0.95, ...}
Valutazione: format_score=1.0, semantic_score=1.0, completeness_score=1.0, score=1.0, passed=true

Esempio C - JSON malformato (mancano parentesi):
Risposta: {"answer": {"label": "order_status", "confidence": 0.9
Valutazione: format_score=0.0, semantic_score=0.0, completeness_score=0.0, score=0.0, passed=false

Esempio D - JSON valido ma campi obbligatori mancanti:
Risposta: {"answer": {}, "confidence": 0.5}
Valutazione: format_score=0.4, semantic_score=0.0, completeness_score=0.0, score=0.15, passed=false

Tipo test:
{{ test_type }}

Input originale:
{{ input_payload }}

Risultato atteso:
{{ expected_output }}

Risposta modello:
{{ model_output }}

Rubrica:
{{ rubric }}

IMPORTANTE: Restituisci SOLO ed ESCLUSIVAMENTE un oggetto JSON puro, senza markdown, senza backtick, senza testo prima o dopo. Il JSON deve avere questa struttura:

{
  "score": 0.0,
  "passed": false,
  "format_score": 0.0,
  "semantic_score": 0.0,
  "completeness_score": 0.0,
  "safety_score": 1.0,
  "hallucination_detected": false,
  "refusal_detected": false,
  "reasoning": "breve motivazione tecnica in italiano"
}

Non omettere nessuno di questi campi. Non aggiungere campi extra. Non racchiudere il JSON in backtick o blocchi di codice. Restituisci SOLO il JSON."""


ALTERNATIVE_KEY_MAP = {
    "score": ["score", "overall_score", "final_score", "total_score"],
    "passed": ["passed", "pass", "is_passed", "success"],
    "format_score": ["format_score", "format"],
    "semantic_score": ["semantic_score", "semantic"],
    "completeness_score": ["completeness_score", "completeness", "completeness"],
    "safety_score": ["safety_score", "safety"],
    "hallucination_detected": ["hallucination_detected", "hallucination", "hallucinated", "has_hallucination"],
    "refusal_detected": ["refusal_detected", "refusal", "refused", "has_refusal"],
    "reasoning": ["reasoning", "reason", "explanation", "notes"],
    "finding_accuracy": ["finding_accuracy", "finding_correctness"],
    "finding_groundedness": ["finding_groundedness", "finding_grounded"],
    "invented_bug_count": ["invented_bug_count", "hallucinated_bug_count"],
    "missed_bug_count": ["missed_bug_count", "false_negative_count"],
    "severity_correctness": ["severity_correctness", "severity_accuracy"],
    "location_specificity": ["location_specificity", "location_accuracy"],
    "recommendation_relevance": ["recommendation_relevance", "recommendation_quality"],
    "overall_assessment_quality": ["overall_assessment_quality"],
}

CODE_ANALYSIS_EXTRA_FIELDS = """

Per i task code_analysis, includi ANCHE questi campi (con i valori indicati per default):
  "finding_accuracy": 0.0,
  "finding_groundedness": 0.0,
  "invented_bug_count": 0,
  "missed_bug_count": 0,
  "severity_correctness": 0.0,
  "location_specificity": 0.0,
  "recommendation_relevance": 0.0,
  "overall_assessment_quality": 0.0

- finding_accuracy: quanti findings attesi sono stati identificati correttamente (0.0-1.0)
- finding_groundedness: i findings sono realmente supportati dal codice (0.0-1.0)
- invented_bug_count: numero di bug/vulnerabilita inventati non presenti nel codice
- missed_bug_count: numero di bug/vulnerabilita attesi non identificati
- severity_correctness: accuratezza della severity assegnata (0.0-1.0)
- location_specificity: precisione della localizzazione del finding (0.0-1.0)
- recommendation_relevance: qualita e pertinenza delle raccomandazioni (0.0-1.0)
- overall_assessment_quality: qualita complessiva della valutazione (0.0-1.0)"""

STT_EXTRA_FIELDS = """

Per i task speech_to_text_postprocess, segui queste linee guida INDEROGABILI:
- Se clean_transcript e presente e strutturato correttamente, semantic_score DEVE essere >= 0.7.
- Se action_items ha schema valido (owner/task/deadline corretti), completeness_score DEVE essere >= 0.75.
- NON azzerare score, semantic_score o completeness_score quando il formato e lo schema sono corretti.
- Penalita moderate (0.1-0.3) per assumptions/warnings non richiesti, MAI score 0 se il task e eseguito.
- Se filler_terms_remaining_count = 0 (nessun riempitivo), premia la qualita della pulizia trascrizione.
- Se non c'e prompt echo, non penalizzare.
- Se non c'e refusal, non penalizzare.
- Non penalizzare se mancano alcuni dettagli minori negli entities_mentioned.
- Una risposta con formato perfetto ma qualche dettaglio mancante NON deve essere scored 0.0."""

RAG_EXTRA_FIELDS = """

Per i task RAG / Q&A documentale, segui queste linee guida INDEROGABILI:
- completeness_score misura quanti fatti RICHIESTI dalla domanda sono presenti nella risposta.
- Se la domanda chiede N elementi e la risposta li contiene TUTTI, completeness DEVE essere 1.0.
- Se la risposta contiene 1 elemento su 3 richiesti, completeness deve essere circa 0.33.
- NON azzerare completeness se la risposta contiene almeno un fatto corretto.
- Le citazioni servono a supportare i fatti, ma completeness dipende dai FATTI nella answer_text.
- Se tutti i fatti richiesti sono presenti e supportati dal contesto, completeness=1.0 e semantic_score alto."""


def _map_alternative_keys(parsed: dict) -> dict:
    mapped = {}
    for canonical, alternatives in ALTERNATIVE_KEY_MAP.items():
        for alt in alternatives:
            if alt in parsed:
                val = parsed[alt]
                mapped[canonical] = val
                break
    mapped["_extra_keys"] = [k for k in parsed if k not in sum(ALTERNATIVE_KEY_MAP.values(), [])]
    mapped["_used_alt_keys"] = {
        canonical: next(alt for alt in alternatives if alt in parsed)
        for canonical, alternatives in ALTERNATIVE_KEY_MAP.items()
        if any(alt in parsed for alt in alternatives[1:])
    }
    return mapped


def _normalize_value(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "yes", "si", "1"):
            return True
        if v in ("false", "no", "0"):
            return False
        try:
            return float(v)
        except (ValueError, TypeError):
            pass
    return value


def _validate_score(parsed: dict) -> list[str]:
    warnings = []
    for key in ["score", "format_score", "semantic_score", "completeness_score", "safety_score"]:
        val = parsed.get(key)
        if val is None:
            continue
        if isinstance(val, bool):
            parsed[key] = 1.0 if val else 0.0
            warnings.append(f"{key} was boolean {val}, converted to {parsed[key]}")
            continue
        try:
            fv = float(val)
            parsed[key] = fv
            if fv < 0.0 or fv > 1.0:
                parsed[key] = max(0.0, min(1.0, fv))
                warnings.append(f"{key}={fv} clamped to [0,1]")
        except (ValueError, TypeError):
            warnings.append(f"{key}={val} not numeric, defaulting to None")
            parsed[key] = None
    return warnings


def _bool_convert(parsed: dict):
    for key in ["hallucination_detected", "refusal_detected"]:
        val = parsed.get(key)
        if val is not None and not isinstance(val, bool):
            if isinstance(val, str):
                parsed[key] = val.strip().lower() in ("true", "yes", "1")
            else:
                parsed[key] = bool(val)
    if "passed" in parsed and parsed["passed"] is not None and not isinstance(parsed["passed"], bool):
        if isinstance(parsed["passed"], str):
            parsed["passed"] = parsed["passed"].strip().lower() in ("true", "yes", "1")
        else:
            parsed["passed"] = bool(parsed["passed"])


def _parse_validator_response(text: str) -> tuple[dict, str, str]:
    if not text or not text.strip():
        return {
            "score": None, "passed": None, "format_score": None,
            "semantic_score": None, "completeness_score": None,
            "safety_score": None, "hallucination_detected": False,
            "refusal_detected": False, "reasoning": "",
        }, "empty_response", "Validator returned empty response"

    clean = text.strip()
    candidates = []
    parse_notes = []

    if clean.startswith("{"):
        candidates.append(("direct", clean))

    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", clean)
    if fence_match:
        candidates.append(("fence", fence_match.group(1)))

    for brace_match in re.finditer(r"\{", clean):
        depth = 0
        start = brace_match.start()
        for i, ch in enumerate(clean[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    extracted = clean[start:i + 1]
                    if not any(extracted == c[1] for c in candidates):
                        candidates.append(("balanced", extracted))
                    break

    parsed = None
    last_error = ""
    for source, candidate in candidates:
        try:
            parsed = json.loads(candidate.strip())
            if isinstance(parsed, dict):
                parse_notes.append(f"parsed from {source}")
                break
            parsed = None
        except json.JSONDecodeError as e:
            last_error = str(e)
            continue

    if parsed is None:
        return {
            "score": None, "passed": None, "format_score": None,
            "semantic_score": None, "completeness_score": None,
            "safety_score": None, "hallucination_detected": False,
            "refusal_detected": False, "reasoning": "",
        }, "invalid_json", f"JSON parse failed: {last_error or 'no candidates'}, raw: {text[:500]}"

    mapped = _map_alternative_keys(parsed)
    _normalize_scores(mapped, text)
    _bool_convert(mapped)
    warnings = _validate_score(mapped)
    if mapped.get("_used_alt_keys"):
        parse_notes.append(f"alt keys: {mapped['_used_alt_keys']}")
    if warnings:
        parse_notes.append(f"warnings: {warnings}")

    critical_missing = []
    for key in ["score", "passed", "format_score", "semantic_score", "completeness_score", "safety_score"]:
        if mapped.get(key) is None:
            critical_missing.append(key)

    status = "ok"
    error_msg = ""
    if critical_missing:
        if "score" in critical_missing and "passed" in critical_missing:
            status = "mapping_error"
            error_msg = f"Critical keys missing after parsing: {critical_missing}: {text[:500]}"
        else:
            status = "ok"
            error_msg = f"Partial keys missing: {critical_missing}"

    mapped["reasoning"] = mapped.get("reasoning", "")
    return mapped, status, error_msg


def _normalize_scores(mapped, raw_text):
    pass


VALIDATOR_RETRY_COUNT = 2


def _get_validator_settings() -> dict:
    try:
        from ..database import SessionLocal
        from ..models import ValidatorConfig
        db = SessionLocal()
        vc = db.query(ValidatorConfig).first()
        db.close()
        if vc:
            return {
                "enabled": vc.enabled,
                "provider": vc.provider,
                "model": vc.model,
                "fallback_provider": vc.fallback_provider,
                "fallback_model": vc.fallback_model,
                "validation_mode": vc.validation_mode,
                "temperature": vc.temperature,
                "max_tokens": vc.max_tokens,
            }
    except Exception:
        pass
    return _get_cfg()


async def _call_validator_provider(provider: str, model: str, prompt: str, temperature: float, max_tokens: int) -> dict:
    try:
        client = get_provider_client(provider)
        response = await client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            top_p=0.9,
            max_tokens=max_tokens,
            response_format="json",
        )
        return response
    except Exception as e:
        return {"error": str(e), "text": "", "raw": {}}


async def validate_response(
    test_type: str,
    input_payload: str,
    expected_output: str,
    model_output: str,
    rubric: str = "",
    json_validity: bool = True,
    schema_compliance: bool = True,
) -> dict:
    validator_cfg = _get_validator_settings()

    if not validator_cfg.get("enabled", False):
        result = _empty_validation_result()
        result["validator_status"] = "disabled"
        result["validator_error_message"] = "Validator is disabled"
        result["validator_attempts"] = 0
        result["validator_raw_response"] = ""
        return result

    provider = validator_cfg.get("provider", "ollama")
    model = validator_cfg.get("model", "")
    temperature = validator_cfg.get("temperature", 0.0)
    max_tokens = validator_cfg.get("max_tokens", 2048)
    fallback_provider = validator_cfg.get("fallback_provider")
    fallback_model = validator_cfg.get("fallback_model")

    prompt = VALIDATOR_PROMPT_TEMPLATE.replace("{{ test_type }}", test_type)
    prompt = prompt.replace("{{ input_payload }}", str(input_payload)[:4000])
    prompt = prompt.replace("{{ expected_output }}", str(expected_output)[:4000])
    prompt = prompt.replace("{{ model_output }}", str(model_output)[:4000])
    prompt = prompt.replace("{{ rubric }}", str(rubric)[:2000])

    deterministic_hint = f"\n\nVINCOLI DETERMINISTICI PRE-CALCOLATI (non modificabili):\n- JSON valido: {'SI' if json_validity else 'NO (HARD FAIL)'}\n- Schema conforme: {'SI' if schema_compliance else 'NO (HARD FAIL)'}\n\nREGOLE INDEROGABILI basate su questi vincoli:\n- Se JSON NON valido: format_score DEVE essere <= 0.2, il test NON puo passare.\n- Se schema NON conforme: format_score DEVE essere <= 0.5, il test NON puo passare.\n- Il tuo semantic_score puo comunque valutare la qualita parziale del contenuto, ma passed DEVE essere false se uno dei due vincoli e NO.\n"

    if "code_analysis" in test_type.lower():
        deterministic_hint += CODE_ANALYSIS_EXTRA_FIELDS
    if "speech_to_text" in test_type.lower() or "stt" in test_type.lower():
        deterministic_hint += STT_EXTRA_FIELDS
    if "rag" in test_type.lower() or "qa" in test_type.lower():
        deterministic_hint += RAG_EXTRA_FIELDS

    prompt += deterministic_hint

    final_status = "unknown"
    final_error = ""
    final_raw = ""
    final_attempts = 0
    final_parsed = {}

    for attempt in range(VALIDATOR_RETRY_COUNT):
        final_attempts = attempt + 1

        response = await _call_validator_provider(provider, model, prompt, temperature, max_tokens)

        error = response.get("error")
        text = response.get("text", "")
        final_raw = text

        if error:
            final_status, final_error = _classify_provider_error(error)
            if fallback_provider and fallback_model:
                fb_response = await _call_validator_provider(fallback_provider, fallback_model, prompt, temperature, max_tokens)
                fb_error = fb_response.get("error")
                fb_text = fb_response.get("text", "")
                if fb_error:
                    final_status, final_error = _classify_provider_error(f"fallback: {fb_error}")
                    final_raw = f"primary({final_error}); fallback({fb_error})"
                elif not fb_text or not fb_text.strip():
                    final_status = "empty_response"
                    final_error = "Fallback validator returned empty response"
                    final_raw = f"primary error; fallback empty"
                else:
                    parsed, status, parse_err = _parse_validator_response(fb_text)
                    final_raw = f"[fallback] {fb_text}"
                    if status == "ok":
                        final_status = "ok"
                        final_error = ""
                        final_parsed = parsed
                        break
                    else:
                        final_status = status
                        final_error = f"Fallback parse error: {parse_err}"
            continue

        if not text or not text.strip():
            final_status = "empty_response"
            final_error = "Validator returned empty response"
            if attempt < VALIDATOR_RETRY_COUNT - 1:
                await asyncio.sleep(1)
                continue
            break

        parsed, status, parse_err = _parse_validator_response(text)
        if status == "ok" or status == "mapping_error":
            final_status = status
            final_error = parse_err if parse_err else ""
            final_parsed = parsed
            break

        final_status = status
        final_error = parse_err
        if attempt < VALIDATOR_RETRY_COUNT - 1:
            await asyncio.sleep(1)
            continue
        final_parsed = parsed

    if not final_parsed:
        final_parsed = {
            "score": None, "passed": None, "format_score": None,
            "semantic_score": None, "completeness_score": None,
            "safety_score": None, "hallucination_detected": False,
            "refusal_detected": False, "reasoning": "",
        }

    result = final_parsed.copy()
    result["validator_status"] = final_status
    result["validator_error_message"] = final_error
    result["validator_raw_response"] = final_raw[:5000] if final_raw else ""
    result["validator_attempts"] = final_attempts
    result["validator_provider"] = provider
    result["validator_model"] = model
    result["validation_text"] = final_raw[:5000] if final_raw else ""
    result["validation_raw"] = ""
    return result


def _classify_provider_error(error: str) -> tuple[str, str]:
    error_lower = error.lower() if error else ""
    if "timeout" in error_lower:
        return "timeout", error
    if "connect" in error_lower or "refused" in error_lower or "unreachable" in error_lower:
        return "provider_error", error
    if "401" in error or "403" in error or "auth" in error_lower:
        return "provider_error", error
    if "429" in error or "rate limit" in error_lower:
        return "provider_error", error
    return "provider_error", error


def _empty_validation_result() -> dict:
    return {
        "score": None, "passed": None, "format_score": None,
        "semantic_score": None, "completeness_score": None,
        "safety_score": None, "hallucination_detected": False,
        "refusal_detected": False, "reasoning": "",
        "validator_provider": "", "validator_model": "",
        "validation_text": "", "validation_raw": "",
    }
