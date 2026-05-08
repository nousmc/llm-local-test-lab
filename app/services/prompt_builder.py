import json
import re

from .config_loader import get_validator_config as _get_cfg
from .provider_router import get_provider_client
from .metrics import check_prompt_contamination

MESSAGE_CONTAINER_TEMPLATE = """
Rispondi ESCLUSIVAMENTE con un JSON valido nel seguente formato:
{
  "answer": %s,
  "confidence": 0.0,
  "missing_information": [],
  "assumptions": [],
  "citations": [],
  "warnings": []
}

Il campo "answer" deve contenere SOLO i dati del task, rispettando la struttura indicata.
Non aggiungere testo prima o dopo il JSON.
"""

ST_HEADER = "Sei un modello in fase di benchmark.\n\nTipo test: {test_type}\n\nIstruzioni: {instructions}\n"

PROMPT_TEMPLATES = {
    "classification": ST_HEADER + """Devi classificare il testo nella categoria corretta.

Classi ammesse (scegline UNA SOLA): {allowed_labels}

Non usare categorie diverse da quelle elencate.
Non aggiungere spiegazioni, restituisci solo la label scelta.

Input da classificare:
{input_text}
""" + MESSAGE_CONTAINER_TEMPLATE % '{ "label": "classe_scelta" }',

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
""" + MESSAGE_CONTAINER_TEMPLATE % '{ {field_placeholders} }',

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
""" + MESSAGE_CONTAINER_TEMPLATE % '{ "answer_text": "risposta basata sul contesto", "citations_used": ["parte del contesto citata..."], "answer_absent": false }',

    "summarization": ST_HEADER + """Devi riassumere il testo fornito.

{format_constraint}
{length_constraint}

Regole:
- Non aggiungere informazioni assenti nel testo originale.
- Rispetta il formato e la lunghezza richiesti.
- Sii conciso e obiettivo.

Testo da sintetizzare:
{input_text}
""" + MESSAGE_CONTAINER_TEMPLATE % '{ "summary": "testo del riassunto", "key_points": ["punto 1", "punto 2"] }',

    "code_analysis": ST_HEADER + """Analizza il codice fornito e identifica problemi, bug o vulnerabilita.

Linguaggio: {language}

Tipo analisi: sicurezza, correttezza, best practice.

Regole:
- Non inventare vulnerabilita o bug non presenti.
- Indica la severita solo se motivata dal codice.
- Ogni finding deve riferirsi a una riga o costrutto specifico.
- Severita ammesse: low, medium, high, critical.

Codice da analizzare:
{input_text}
""" + MESSAGE_CONTAINER_TEMPLATE % '{ "findings": [{ "type": "bug|security|best_practice|performance", "severity": "low|medium|high|critical", "location": "linea o funzione", "description": "descrizione del problema", "recommendation": "come risolvere" }], "overall_assessment": "valutazione complessiva" }',

    "code_documentation": ST_HEADER + """Scrivi la documentazione per il codice fornito.

Stile: {doc_style}
Lingua: {language}

Regole:
- Documenta solo comportamenti effettivamente presenti nel codice.
- Non aggiungere funzionalita non implementate.
- Includi parametri, valori restituiti, eccezioni sollevate.

Codice da documentare:
{input_text}
""" + MESSAGE_CONTAINER_TEMPLATE % '{ "docstring": "documentazione completa", "parameters": [{ "name": "nome", "type": "tipo", "description": "descrizione" }], "returns": { "type": "tipo", "description": "descrizione" }, "raises": [{ "exception": "NomeEccezione", "condition": "quando viene sollevata" }], "examples": ["esempio duso"] }',

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
""" + MESSAGE_CONTAINER_TEMPLATE % '{ "refactored_code": "codice rifattorizzato", "changes_summary": ["cambio 1", "cambio 2"], "preserved_behavior": true }',

    "image_description": ST_HEADER + """Descrivi l'immagine in modo neutro e oggettivo.

Stile: {style}
{length_constraint}

Regole:
- Descrivi solo oggetti visibili nell'immagine.
- Non indicare oggetti assenti o solo probabili.
- Non interpretare emozioni o intenzioni di persone.

{input_text}
""" + MESSAGE_CONTAINER_TEMPLATE % '{ "description": "descrizione oggettiva dellimmagine", "objects_detected": ["oggetto 1", "oggetto 2"], "scene_type": "tipo di scena", "dominant_colors": ["colore 1"] }',

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
""" + MESSAGE_CONTAINER_TEMPLATE % '{ {field_placeholders} }',

    "speech_to_text_postprocess": ST_HEADER + """Pulisci e struttura la trascrizione grezza.

Trasformazione richiesta:
- Rimuovi riempitivi (emh, ehm, ecc).
- Correggi errori di trascrizione evidenti.
- Estrai action items, owner e task espliciti.
- Estrai date e deadline menzionate.

Regole:
- Non aggiungere decisioni o task non menzionati.
- Se un owner non e specificato, usa null.
- Se una deadline non e specificata, usa null.

Trascrizione grezza:
{input_text}
""" + MESSAGE_CONTAINER_TEMPLATE % '{ "clean_transcript": "trascrizione pulita", "action_items": [{ "owner": "nome o null", "task": "task da fare", "deadline": "data o null" }], "entities_mentioned": [{ "name": "nome entita", "type": "person|date|project|other" }] }',
}


def _extract_expected_schema(expected_output_json: str | None) -> dict:
    if not expected_output_json:
        return {}
    try:
        return json.loads(expected_output_json)
    except Exception:
        return {}


def _build_field_list(expected: dict) -> str:
    fields = expected.get("schema", {})
    if not fields:
        exp = expected.get("expected", {})
        fields = {k: (type(v).__name__ if v is not None else "string") for k, v in exp.items()} if isinstance(exp, dict) else {}
    if not fields:
        exp_fields = expected.get("expected_fields", {})
        fields = {k: (type(v).__name__ if v is not None else "string") for k, v in exp_fields.items()} if isinstance(exp_fields, dict) else {}

    if expected.get("required_fields"):
        required = set(expected["required_fields"])
    else:
        required = set(fields.keys())

    if not fields:
        return "  (nessun campo specificato)"

    lines = []
    for field, ftype in fields.items():
        marker = " *" if field in required else ""
        lines.append(f"  - {field}: {ftype}{marker}")
    return "\n".join(lines)


def _build_field_placeholders(expected: dict) -> str:
    fields = expected.get("schema", {})
    if not fields:
        exp = expected.get("expected", {})
        fields = {k: (type(v).__name__ if v is not None else "string") for k, v in exp.items()} if isinstance(exp, dict) else {}
    if not fields:
        exp_fields = expected.get("expected_fields", {})
        fields = {k: (type(v).__name__ if v is not None else "string") for k, v in exp_fields.items()} if isinstance(exp_fields, dict) else {}

    if not fields:
        return ""

    placeholders = []
    for field, ftype in fields.items():
        if ftype in ("number", "integer", "float", "int"):
            placeholders.append(f'"{field}": 0')
        elif ftype == "bool":
            placeholders.append(f'"{field}": false')
        elif ftype == "date":
            placeholders.append(f'"{field}": "YYYY-MM-DD"')
        else:
            placeholders.append(f'"{field}": "valore"')
    return ", ".join(placeholders)


def _get_allowed_labels(expected: dict) -> str:
    labels = expected.get("allowed_labels", [])
    if not labels:
        expected_labels = expected.get("expected_labels_json", "")
        if expected_labels:
            try:
                labels_data = json.loads(expected_labels) if isinstance(expected_labels, str) else expected_labels
                labels = labels_data.get("allowed_labels", []) or list(labels_data.values())
            except Exception:
                pass
    if not labels and "expected" in expected:
        exp = expected["expected"]
        labels = list(exp.keys()) if isinstance(exp, dict) else []

    if labels:
        return ", ".join(str(l) for l in labels) + "\nDevi scegliere UNA di queste. Non aggiungere altre etichette."
    return " (NESSUNA CLASSE SPECIFICATA - IL PROMPT POTREBBE ESSERE INVALIDO)"


def _get_constraints_text(expected: dict) -> str:
    constraints = expected.get("constraints", [])
    if not constraints:
        return "- Non cambiare il comportamento esterno."
    return "\n".join(f"- {c}" for c in constraints)


def _get_format_constraint(expected: dict) -> str:
    fmt = expected.get("format", "bullet_list")
    if fmt == "bullet_list":
        return "Formato richiesto: elenco puntato."
    return f"Formato richiesto: {fmt}."


def _get_length_constraint(expected: dict) -> str:
    max_words = expected.get("max_words")
    if max_words:
        return f"Limite massimo: {max_words} parole."
    return ""


def validate_prompt(prompt: str, test_type_id: str, expected_output_json: str | None, allowed_source_text: str = "") -> tuple[bool, str, str]:
    issues = []

    has_container = '{"answer"' in prompt.replace(" ", "") or '"answer":' in prompt
    if not has_container:
        issues.append("missing_response_container")

    if test_type_id == "classification":
        if "Classi ammesse" not in prompt:
            issues.append("missing_allowed_labels")
        else:
            section = prompt.split("Classi ammesse")[1].split("\n\n")[0] if "\n\n" in prompt.split("Classi ammesse")[1] else prompt.split("Classi ammesse")[1]
            if "NESSUNA CLASSE" in section or "(nessuna classe" in section or len(section.strip()) < 5:
                issues.append("missing_allowed_labels")

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
        return False, "; ".join(issues), "invalid_prompt"
    return True, "", "valid"
