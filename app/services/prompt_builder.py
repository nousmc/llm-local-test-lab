import json
import re
import yaml
from pathlib import Path

from .config_loader import get_validator_config as _get_cfg
from .provider_router import get_provider_client
from .metrics import check_prompt_contamination

MESSAGE_CONTAINER_TEMPLATE = """
Rispondi ESCLUSIVAMENTE con un JSON valido nel seguente formato:
{
  "answer": {answer_format},
  "confidence": 0.0,
  "missing_information": [],
  "assumptions": [],
  "citations": [],
  "warnings": []
}

Il campo "answer" deve contenere SOLO i dati del task, rispettando la struttura indicata.
Non aggiungere testo prima o dopo il JSON.
"""

ANSWER_FORMAT_DEFAULTS: dict = {}

ST_HEADER = "Sei un modello in fase di benchmark.\n\nTipo test: {test_type}\n\nIstruzioni: {instructions}\n"


def _load_yaml_templates() -> dict:
    yaml_path = Path(__file__).resolve().parent.parent.parent / "config" / "prompt_templates.yaml"
    try:
        with open(yaml_path) as f:
            raw = yaml.safe_load(f)
        templates = {}
        for tid, entry in raw.items():
            if isinstance(entry, dict):
                body = str(entry.get("body", ""))
                fmt = str(entry.get("answer_format", "{}"))
                ANSWER_FORMAT_DEFAULTS[tid] = fmt
                templates[tid] = ST_HEADER + body + "\n" + MESSAGE_CONTAINER_TEMPLATE
        if templates:
            return templates
    except Exception:
        pass
    return _get_hardcoded_templates()


def _get_hardcoded_templates() -> dict:
    _fmts = {
        "classification":              '{ "label": "classe_scelta" }',
        "data_extraction":             '{ {field_placeholders} }',
        "rag_qa":                      '{ "answer_text": "risposta basata sul contesto", "citations_used": ["parte del contesto citata..."], "answer_absent": false }',
        "summarization":               '{ "summary": "testo del riassunto", "key_points": ["punto 1", "punto 2"] }',
        "code_analysis":               '{ "findings": [{ "type": "bug|security|best_practice|performance", "severity": "low|medium|high|critical", "location": "linea o funzione", "description": "descrizione del problema", "recommendation": "come risolvere" }], "overall_assessment": "valutazione complessiva" }',
        "code_documentation":          '{ "docstring": "documentazione completa", "parameters": [{ "name": "nome", "type": "tipo", "description": "descrizione" }], "returns": { "type": "tipo", "description": "descrizione" }, "raises": [{ "exception": "NomeEccezione", "condition": "quando viene sollevata" }], "examples": ["esempio duso"] }',
        "refactoring":                 '{ "refactored_code": "codice rifattorizzato", "changes_summary": ["cambio 1", "cambio 2"], "preserved_behavior": true }',
        "image_description":           '{ "description": "descrizione oggettiva dellimmagine", "objects_detected": ["oggetto 1", "oggetto 2"], "scene_type": "tipo di scena", "dominant_colors": ["colore 1"] }',
        "ocr_extraction":              '{ {field_placeholders} }',
        "speech_to_text_postprocess":  '{ "clean_transcript": "trascrizione pulita", "action_items": [{ "owner": "nome o null", "task": "task da fare", "deadline": "data o null" }], "entities_mentioned": [{ "name": "nome entita", "type": "person|date|project|other" }] }',
        "contextual_insight":          '{ "insights": ["idea concreta 1", "idea concreta 2"], "references_to_context": ["riferimento al turno X"], "follow_up_questions": ["domanda di approfondimento"], "depth": "dominio_scelto" }',
    }
    ANSWER_FORMAT_DEFAULTS.update(_fmts)
    return {
        "classification": ST_HEADER + """Devi classificare il testo nella categoria corretta.

Classi ammesse (scegline UNA SOLA): {allowed_labels}

Non usare categorie diverse da quelle elencate.
Non aggiungere spiegazioni, restituisci solo la label scelta.

Input da classificare:
{input_text}
""" + MESSAGE_CONTAINER_TEMPLATE,

        "data_extraction": ST_HEADER + """Devi estrarre dati strutturati dal testo.

Campi da estrarre (con tipo):
{field_list}

Regole:
- Se un dato non e presente o non e leggibile, usa null per quel campo.
- Le date vanno nel formato YYYY-MM-DD.
- I numeri vanno senza simboli di valuta o separatori delle migliaia.
- I campi testo vanno normalizzati (senza spazi inutili).

Input da analizzare:
{input_text}
""" + MESSAGE_CONTAINER_TEMPLATE,

        "rag_qa": ST_HEADER + """Rispondi alla domanda basandoti ESCLUSIVAMENTE sul contesto fornito.

{answer_absent_rule}

Regole:
- Cita parti del contesto per giustificare la risposta (campo "citations").
- Non usare conoscenze esterne al contesto.
- Se il contesto non contiene la risposta, imposta "answer_absent": true.

Domanda:
{input_text}

Contesto:
{context}
""" + MESSAGE_CONTAINER_TEMPLATE,

        "summarization": ST_HEADER + """Devi riassumere il testo fornito.

{format_constraint}
{length_constraint}

Regole:
- Non aggiungere informazioni assenti nel testo originale.
- Rispetta il formato e la lunghezza richiesti.
- Sii conciso e obiettivo.

Testo da sintetizzare:
{input_text}
""" + MESSAGE_CONTAINER_TEMPLATE,

        "code_analysis": ST_HEADER + """Analizza il codice fornito e identifica problemi, bug o vulnerabilita.

Linguaggio: {language}

{ca_instructions}

{custom_rules}
Codice da analizzare:
{input_text}
""" + MESSAGE_CONTAINER_TEMPLATE,

        "code_documentation": ST_HEADER + """Scrivi la documentazione per il codice fornito.

Stile: {doc_style}
Lingua: {language}

Regole:
- Documenta solo comportamenti effettivamente presenti nel codice.
- Non aggiungere funzionalita non implementate.
- Includi parametri, valori restituiti, eccezioni sollevate.

Codice da documentare:
{input_text}
""" + MESSAGE_CONTAINER_TEMPLATE,

        "refactoring": ST_HEADER + """Riscrivi il codice applicando refactoring.

Obiettivo: {target}

Vincoli:
{constraints}

Regole:
- NON cambiare il comportamento esterno del codice.
- NON modificare le signature pubbliche.
- NON introdurre dipendenze esterne.

Codice da rifattorizzare:
{input_text}
""" + MESSAGE_CONTAINER_TEMPLATE,

        "image_description": ST_HEADER + """Descrivi l'immagine in modo neutro e oggettivo.

Stile: {style}
{length_constraint}

Regole:
- Descrivi solo oggetti visibili nell'immagine.
- Non indicare oggetti assenti o solo probabili.
- Non interpretare emozioni o intenzioni di persone.

{input_text}
""" + MESSAGE_CONTAINER_TEMPLATE,

        "ocr_extraction": ST_HEADER + """Estrai i dati dal documento OCR.

Campi da estrarre:
{field_list}

Regole:
- Se un campo non e leggibile o assente, usa null.
- Testo: normalizza spazi e maiuscole/minuscole.
- Date: formato YYYY-MM-DD.
- Numeri: senza simboli, punto decimale.

Documento da analizzare:
{input_text}
""" + MESSAGE_CONTAINER_TEMPLATE,

        "speech_to_text_postprocess": ST_HEADER + """Pulisci e struttura la trascrizione grezza.

{stt_instructions}

{custom_rules}
Trascrizione grezza:
{input_text}
""" + MESSAGE_CONTAINER_TEMPLATE,

        "contextual_insight": ST_HEADER + """Analizza la conversazione multi-turno e produci un'analisi strutturata che dimostri comprensione del contesto, capacita di approfondimento e creativita pertinente al dominio.

Scenario:
{input_text}

Contesto aggiuntivo:
{context}

Istruzioni: {instructions}

{ci_instructions}

{custom_rules}
""" + MESSAGE_CONTAINER_TEMPLATE,
    }


PROMPT_TEMPLATES = _load_yaml_templates()


def _extract_expected_schema(expected_output_json: str | None) -> dict:
    if not expected_output_json:
        return {}
    try:
        data = json.loads(expected_output_json)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _build_field_list(expected: dict) -> str:
    schema = expected.get("schema", {})
    if schema:
        return "\n".join(f"  - {k}: {v}" for k, v in schema.items())
    exp_data = expected.get("expected", expected.get("expected_fields", {}))
    if isinstance(exp_data, dict):
        return "\n".join(f"  - {k}" for k in exp_data.keys())
    return ""


_TYPE_HINTS = {
    "number": "0", "integer": "0", "float": "0.0",
    "boolean": "false",
    "date": '"YYYY-MM-DD"',
    "datetime": '"YYYY-MM-DD HH:MM:SS"',
    "array": "[]",
    "object": "{}",
}

_DEFAULT_CI_INSTRUCTIONS = (
    "Produci un'analisi con:\n"
    "- insights: lista di idee/strategie concrete (minimo 3, massimo 8)\n"
    "- references_to_context: riferimenti specifici ai turni della conversazione\n"
    "- follow_up_questions: domande di approfondimento pertinenti\n"
    "- depth: il dominio di riferimento della tua analisi"
)

_DEFAULT_CA_INSTRUCTIONS = "Tipo analisi: sicurezza, correttezza, best practice."

_DEFAULT_STT_INSTRUCTIONS = (
    "Trasformazione richiesta:\n"
    "- Rimuovi riempitivi (emh, ehm, ecc).\n"
    "- Correggi errori di trascrizione evidenti.\n"
    "- Estrai action items, owner e task espliciti.\n"
    "- Estrai date e deadline menzionate."
)


def _build_field_placeholders(expected: dict) -> str:
    fields = expected.get("expected", expected.get("expected_fields", {}))
    if isinstance(fields, dict) and fields:
        return ', '.join(f'"{k}": "..."' for k in fields.keys())
    schema = expected.get("schema", {})
    if isinstance(schema, dict) and schema:
        parts = []
        for k, t in schema.items():
            hint = _TYPE_HINTS.get(str(t).lower(), '"..."')
            parts.append(f'"{k}": {hint}')
        return ', '.join(parts)
    return ""


def _get_allowed_labels(expected: dict) -> str:
    labels = expected.get("allowed_labels", [])
    if isinstance(labels, str):
        return labels
    if isinstance(labels, list):
        return ", ".join(str(l) for l in labels)
    exp_labels = expected.get("expected_labels", {})
    if isinstance(exp_labels, dict):
        vals = list(exp_labels.values())
        if vals:
            return ", ".join(str(v) for v in vals)
    return ""


def _get_constraints_text(expected: dict) -> str:
    constraints = expected.get("constraints", [])
    if isinstance(constraints, list):
        return "\n".join(f"  - {c}" for c in constraints)
    return ""


def _get_format_constraint(expected: dict) -> str:
    fmt = expected.get("format", "")
    if fmt == "bullet_list":
        return "Formato richiesto: elenco puntato.\n  - Ogni riga del summary deve iniziare con un trattino (-).\n  - I key_points devono essere una lista degli stessi punti."
    return ""


def _get_length_constraint(expected: dict) -> str:
    max_words = expected.get("max_words")
    if max_words:
        return f"Lunghezza massima: {max_words} parole."
    return ""


def _format_custom_rules(rules_text) -> str:
    if not rules_text or not str(rules_text).strip():
        return ""
    lines = [l.strip() for l in str(rules_text).strip().split("\n") if l.strip()]
    items = "\n".join(f"- {l}" if not l.startswith("- ") else l for l in lines)
    return "Regole:\n" + items


def _render_prompt_template(template: str, test_case, test_type, expected: dict) -> str:
    _tid = (test_type.id if test_type else None) or test_case.test_type_id
    replacements = {
        "answer_format": expected.get("answer_format", ANSWER_FORMAT_DEFAULTS.get(_tid, "{}")),
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
        "language": expected.get("code_language", expected.get("language", "it")),
        "doc_style": expected.get("style", "docstring_google"),
        "answer_absent_rule": (
            "IMPORTANTE: se la risposta NON e presente nel contesto, imposta "
            "answer_absent a true e lascia answer_text vuoto."
        ) if expected.get("answer_absent") is not None else "",
        "custom_rules": _format_custom_rules(getattr(test_case, "rules", None)),
        "ci_instructions": expected.get("ci_instructions", _DEFAULT_CI_INSTRUCTIONS),
        "ca_instructions": expected.get("ca_instructions", _DEFAULT_CA_INSTRUCTIONS),
        "stt_instructions": expected.get("stt_instructions", _DEFAULT_STT_INSTRUCTIONS),
    }
    prompt = template
    for key, value in replacements.items():
        prompt = prompt.replace("{" + key + "}", str(value))
        prompt = prompt.replace("{{ " + key + " }}", str(value))
        prompt = prompt.replace("{{" + key + "}}", str(value))
    return prompt


def _build_generated_prompt(test_case, test_type) -> str:
    tid = test_type.id if test_type else test_case.test_type_id
    template = PROMPT_TEMPLATES.get(tid)
    if not template:
        template = PROMPT_TEMPLATES.get("classification")
        tid = "classification"
    expected = _extract_expected_schema(test_case.expected_output_json)
    return _render_prompt_template(template, test_case, test_type, expected)


def _build_prompt(test_case, test_type) -> str:
    expected = _extract_expected_schema(test_case.expected_output_json)
    if test_case.user_prompt_template and test_case.user_prompt_template.strip():
        return _render_prompt_template(test_case.user_prompt_template, test_case, test_type, expected)
    return _build_generated_prompt(test_case, test_type)


def validate_prompt(
    prompt: str,
    test_type_id: str,
    expected_output_json: str | None,
    allowed_source_text: str = "",
) -> tuple[bool, list[str], str]:
    issues = []

    has_container = '{"answer"' in prompt.replace(" ", "") or '"answer":' in prompt
    if not has_container:
        issues.append("missing_response_container")

    if test_type_id == "classification":
        has_classi_ammesse = "Classi ammesse" in prompt
        has_allowed_labels_json = bool(re.search(r'"allowed_labels"\s*:\s*\[', prompt, re.IGNORECASE))

        if not has_classi_ammesse and not has_allowed_labels_json:
            issues.append("missing_allowed_labels")
        elif has_classi_ammesse:
            rest = prompt.split("Classi ammesse", 1)[1]
            section = rest.split("\n\n")[0] if "\n\n" in rest else rest
            label_part = section.split(":", 1)[-1] if ":" in section else section
            label_text = label_part.strip("() :\n\r\t")
            if len(label_text) < 3 or "," not in label_text:
                issues.append("missing_allowed_labels")
        elif has_allowed_labels_json:
            try:
                match = re.search(r'"allowed_labels"\s*:\s*(\[[^\]]*\])', prompt, re.IGNORECASE)
                if match:
                    labels = json.loads(match.group(1))
                    if not isinstance(labels, list) or len(labels) == 0:
                        issues.append("missing_allowed_labels")
                else:
                    issues.append("missing_allowed_labels")
            except (json.JSONDecodeError, TypeError):
                issues.append("missing_allowed_labels")

    if not prompt.strip():
        issues.append("empty_prompt")

    if "rispondi esclusivamente con un json" not in prompt.lower():
        issues.append("missing_json_instruction")

    if "{input_text}" in prompt or "{{input_text}}" in prompt:
        issues.append("unreplaced_placeholders")

    generic_schema_indicators = [
        "Formato atteso: classification_expected",
        "Formato atteso: json_expected",
        "Formato atteso: rag_expected",
        "Formato atteso: summary_expected",
        "Formato atteso: code_expected",
        "Formato atteso: code_doc_expected",
        "Formato atteso: refactoring_expected",
        "Formato atteso: vision_expected",
        "Formato atteso: ocr_expected",
        "Formato atteso: stt_expected",
    ]
    for indicator in generic_schema_indicators:
        if indicator.lower() in prompt.lower():
            issues.append("generic_schema_not_expanded")

    if " ... " in prompt and "answer" in prompt:
        pass

    contaminated, info = check_prompt_contamination(prompt, expected_output_json, allowed_source_text=allowed_source_text)
    if contaminated:
        issues.append(f"contamination:{info}")

    if issues:
        return False, issues, "invalid_prompt"
    return True, [], "valid"
