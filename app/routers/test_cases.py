import json
import os
import re
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, File, Form, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import TestCase, TestType, UploadedFile
from ..schemas import TestCaseCreate, TestCaseUpdate
from ..services.file_parser import validate_upload, read_uploaded_file

ALLOWED_LABELS_JSON_PATTERN = re.compile(r'\"allowed_labels\"\s*:\s*(\[[^\]]*\])', re.IGNORECASE)

def _assemble_prompt(fields: dict) -> str:
    """Assembla un prompt dai campi forniti, preservando i placeholder per i campi dinamici.

    Args:
        fields: Dizionario con i campi da inserire nel template.

    Returns:
        Il prompt assemblato come stringa.
    """
    from ..services.prompt_builder import PROMPT_TEMPLATES, ST_HEADER, MESSAGE_CONTAINER_TEMPLATE
    test_type_id = fields.get("test_type_id", "classification")
    template = PROMPT_TEMPLATES.get(test_type_id, PROMPT_TEMPLATES.get("classification"))
    if not template:
        template = PROMPT_TEMPLATES.get("classification")

    prompt = template

    field_keys = {
        "test_type", "instructions", "input_text", "context", "field_list",
        "field_placeholders", "allowed_labels", "target", "constraints",
        "format_constraint", "length_constraint", "style", "language",
        "doc_style", "answer_absent_rule",
    }

    for key in field_keys:
        val = fields.get(key, "")
        if val:
            prompt = prompt.replace("{" + key + "}", str(val))
            prompt = prompt.replace("{{ " + key + " }}", str(val))
            prompt = prompt.replace("{{" + key + "}}", str(val))

    return prompt


def _get_type_formats() -> dict:
    from ..services.prompt_builder import PROMPT_TEMPLATES
    formats = {}
    marker = "Rispondi ESCLUSIVAMENTE con un JSON valido"
    for tid, template in PROMPT_TEMPLATES.items():
        idx = template.find(marker)
        if idx >= 0:
            formats[tid] = template[idx:].strip()
    return formats


def _get_default_expected_json(db: Session) -> dict:
    defaults = {}
    for tt in db.query(TestType).all():
        if tt.expected_json_template:
            defaults[tt.id] = tt.expected_json_template
    return defaults


def _get_template_parts() -> dict:
    """Restituisce le parti del template per ogni tipo test, per l'anteprima frontend.

    Estrae body e format constraint dal template assemblato, rimuovendo lo ST_HEADER.
    Identifica anche i placeholder usati nel template.

    Returns:
        Dizionario type_id -> {"body": str, "format": str, "placeholders": [str]}
    """
    from ..services.prompt_builder import PROMPT_TEMPLATES, ST_HEADER
    parts = {}
    placeholder_re = re.compile(r'\{(\{?\s*\w+\s*\}?)\}')
    for tid, template in PROMPT_TEMPLATES.items():
        body = template[len(ST_HEADER):]
        idx = body.rfind("Rispondi ESCLUSIVAMENTE con un JSON valido")
        if idx >= 0:
            format_section = body[idx:]
            body = body[:idx].rstrip("\n")
        else:
            format_section = ""

        placeholders = set()
        for match in placeholder_re.finditer(body):
            ph = match.group(1).strip().strip("{}").strip()
            if ph and ph.isidentifier():
                placeholders.add(ph)

        parts[tid] = {
            "body": body.strip(),
            "format": format_section.strip(),
            "placeholders": sorted(placeholders),
        }
    return parts


def _get_type_examples() -> dict:
    """Restituisce esempi predefiniti per ogni tipo di test.

    Returns:
        Dizionario mappato type_id -> {title, description, input_text, rules, expected_json, ...}
    """
    return {
        "classification": {
            "title": "Sentiment analysis",
            "description": "Classificare il sentiment di una recensione",
            "input_text": "Il prodotto e arrivato rotto, non lo ricomprerei mai.",
            "rules": '{"allowed_labels": ["positivo", "negativo", "neutro"]}',
            "expected_output_json": '{"expected": {"label": "negativo"}, "allowed_labels": ["positivo", "negativo", "neutro"]}',
        },
        "data_extraction": {
            "title": "Estrazione dati da fattura",
            "description": "Estrarre dati strutturati da una fattura",
            "input_text": "Fattura N. 00123 del 15/03/2024. Totale: 450.00 EUR.",
            "rules": "Campi: numero_fattura (string), data (date), totale (number)",
            "expected_output_json": '{"expected": {"numero_fattura": "00123", "data": "2024-03-15", "totale": 450.0}, "schema": {"numero_fattura": "string", "data": "date", "totale": "number"}}',
        },
        "rag_qa": {
            "title": "Domanda su contesto tecnico",
            "description": "Rispondere a una domanda usando il contesto fornito",
            "input_text": "Quali sono i requisiti di sistema?",
            "context_text": "Il software richiede Python 3.10+, 8GB RAM, e sistema operativo Linux.",
            "rules": "Citare parti del contesto. Se assente, impostare answer_absent=true.",
            "expected_output_json": '{"expected": {"answer_text": "Python 3.10+, 8GB RAM, Linux", "citations_used": ["Python 3.10+"], "answer_absent": false}, "answer_absent": false}',
        },
        "summarization": {
            "title": "Riassunto di articolo",
            "description": "Sintetizzare un articolo in massimo 100 parole",
            "input_text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit... (articolo lungo)",
            "rules": "Massimo 100 parole. Formato elenco puntato. Solo informazioni dal testo.",
            "expected_output_json": '{"max_words": 100, "format": "bullet_list"}',
        },
        "code_analysis": {
            "title": "Code review sicurezza",
            "description": "Analizzare un frammento Python per vulnerabilit\u00e0",
            "input_text": "import os\nuser_input = input()\nos.system('ls ' + user_input)",
            "rules": 'Linguaggio: Python. Identificare bug, security, best practice.',
            "expected_output_json": '{"expected_findings": [{"type": "security", "severity": "high"}], "language": "Python"}',
        },
        "code_documentation": {
            "title": "Documentazione funzione",
            "description": "Scrivere docstring in stile Google per una funzione",
            "input_text": "def calcola_sconto(prezzo, percentuale, codice_cliente=None):\n    return prezzo * (1 - percentuale / 100)",
            "rules": 'Stile: Google. Lingua: it. Includere parametri, return, eccezioni.',
            "expected_output_json": '{"style": "google", "language": "it", "expected_parameters": [{"name": "prezzo", "type": "float"}, {"name": "percentuale", "type": "float"}, {"name": "codice_cliente", "type": "str"}]}',
        },
        "refactoring": {
            "title": "Refactoring funzione",
            "description": "Rifattorizzare codice per migliorare leggibilita",
            "input_text": "def f(x, y):\\n    return x+y if x>0 else x-y",
            "rules": "Migliorare i nomi. Preservare il comportamento.",
            "expected_output_json": '{"target": "leggibilita", "constraints": ["preservare comportamento", "non cambiare signature"]}',
        },
        "image_description": {
            "title": "Descrizione immagine",
            "description": "Descrivere oggettivamente un'immagine",
            "input_text": "[Rappresentazione testuale dell'immagine]",
            "rules": "Descrivere solo oggetti visibili. Max 50 parole.",
            "expected_output_json": '{"max_words": 50, "style": "oggettiva"}',
        },
        "ocr_extraction": {
            "title": "Estrazione dati OCR",
            "description": "Estrarre dati da documento OCR",
            "input_text": "Nome: Mario Rossi\\nData: 01/01/2024\\nImporto: 150,00",
            "rules": "Campi: nome, data, importo. Normalizzare date e numeri.",
            "expected_output_json": '{"expected": {"nome": "Mario Rossi", "data": "2024-01-01", "importo": 150.0}, "schema": {"nome": "string", "data": "date", "importo": "number"}}',
        },
        "speech_to_text_postprocess": {
            "title": "Post-processing trascrizione",
            "description": "Pulire una trascrizione grezza da riempitivi",
            "input_text": "Ehm allora... dobbiamo fixare il bug nella login, mhm e poi fare il deploy.",
            "rules": "Rimuovere riempitivi (ehm, mhm). Estrarre action items.",
            "expected_output_json": '{"clean_transcript_contains": ["fixare bug login", "fare deploy"]}',
        },
        "contextual_insight": {
            "title": "Analisi conversazione multi-turno",
            "description": "Analizzare conversazione per estrarre insight strategici",
            "input_text": "Turno 1: Dobbiamo migliorare la retention. Turno 2: Forse un programma fedelt\u00e0? Turno 3: Budget limitato a 50K.",
            "context_text": "Conversazione tra CTO e Product Manager di una startup SaaS.",
            "rules": "Min 3 insight, max 8. Riferimenti a turni specifici. Dominio: strategico.",
            "expected_output_json": '{"must_include_themes": ["retention", "fedelt\u00e0", "budget"], "depth": "strategico", "expected_insight_count": {"min": 3, "max": 8}}',
        },
    }


def _build_type_meta() -> dict:
    import yaml as _yaml
    from pathlib import Path as _Path
    import re as _re
    _ph = _re.compile(r'\{[a-z_]+\}')
    try:
        _tpl_data = _yaml.safe_load((_Path(__file__).resolve().parent.parent.parent / "config" / "prompt_templates.yaml").read_text())
    except Exception:
        _tpl_data = {}

    _hidden_placeholders = {
        "{custom_rules}", "{ci_instructions}", "{ca_instructions}", "{stt_instructions}",
    }

    def _template_body(tid: str) -> str:
        body = _tpl_data.get(tid, {}).get("body", "")
        if not body:
            return ""
        lines = []
        for l in body.strip().split("\n"):
            stripped = l.strip()
            if not stripped or stripped in _hidden_placeholders:
                continue
            lines.append(stripped)
        return "\n".join(lines)

    def _answer_format(tid: str) -> str:
        return str(_tpl_data.get(tid, {}).get("answer_format", ""))

    _default_rules = {
        "classification": [
            "Non usare categorie diverse da quelle elencate.",
            "Non aggiungere spiegazioni, restituisci solo la label scelta.",
        ],
        "data_extraction": [
            "Se un dato non e presente o non e leggibile, usa null per quel campo.",
            "Le date vanno nel formato YYYY-MM-DD.",
            "I numeri vanno senza simboli di valuta o separatori delle migliaia.",
            "I campi testo vanno normalizzati (senza spazi inutili).",
        ],
        "rag_qa": [
            "Cita parti del contesto per giustificare la risposta (campo \"citations\").",
            "Non usare conoscenze esterne al contesto.",
            "Se il contesto non contiene la risposta, imposta \"answer_absent\": true.",
        ],
        "summarization": [
            "Non aggiungere informazioni assenti nel testo originale.",
            "Rispetta il formato e la lunghezza richiesti.",
            "Sii conciso e obiettivo.",
        ],
        "code_analysis": [
            "Non inventare vulnerabilita o bug non presenti.",
            "Indica la severita solo se motivata dal codice.",
            "Ogni finding deve riferirsi a una riga o costrutto specifico.",
            "Severita ammesse: low, medium, high, critical.",
        ],
        "code_documentation": [
            "Documenta solo comportamenti effettivamente presenti nel codice.",
            "Non aggiungere funzionalita non implementate.",
            "Includi parametri, valori restituiti, eccezioni sollevate.",
        ],
        "refactoring": [
            "NON cambiare il comportamento esterno del codice.",
            "NON modificare le signature pubbliche.",
            "NON introdurre dipendenze esterne.",
        ],
        "image_description": [
            "Descrivi solo oggetti visibili nell'immagine.",
            "Non indicare oggetti assenti o solo probabili.",
            "Non interpretare emozioni o intenzioni di persone.",
        ],
        "ocr_extraction": [
            "Se un campo non e leggibile o assente, usa null.",
            "Testo: normalizza spazi e maiuscole/minuscole.",
            "Date: formato YYYY-MM-DD.",
            "Numeri: senza simboli, punto decimale.",
        ],
        "speech_to_text_postprocess": [
            "Non aggiungere decisioni o task non menzionati.",
            "Se un owner non e specificato, usa null.",
            "Se una deadline non e specificata, usa null.",
        ],
        "contextual_insight": [
            "Ogni insight deve essere concreto e pertinente al dominio.",
            "Non proporre idee generiche o ovvie.",
            "Fai riferimento esplicito a turni specifici della conversazione.",
            "Le domande di approfondimento devono essere rilevanti e non scontate.",
        ],
    }

    return {
        "classification": {
            "description": "Il modello classifica un testo in una delle categorie ammesse. Scoring deterministico su label esatta.",
            "input_label": "Testo da classificare",
            "needs_context": False,
            "template_body": _template_body("classification"),
            "default_rules": _default_rules["classification"],
            "answer_format": _answer_format("classification"),
        },
        "data_extraction": {
            "description": "Il modello estrae campi strutturati da un testo. Scoring su field accuracy e schema compliance.",
            "input_label": "Testo da cui estrarre i dati",
            "needs_context": False,
            "template_body": _template_body("data_extraction"),
            "default_rules": _default_rules["data_extraction"],
            "answer_format": _answer_format("data_extraction"),
        },
        "rag_qa": {
            "description": "Il modello risponde a una domanda basandosi SOLO sul contesto fornito. Scoring su answer_absent e citazioni.",
            "input_label": "Domanda",
            "needs_context": True,
            "template_body": _template_body("rag_qa"),
            "default_rules": _default_rules["rag_qa"],
            "answer_format": _answer_format("rag_qa"),
        },
        "summarization": {
            "description": "Il modello sintetizza un testo rispettando limite di parole e formato. Scoring su max_words_respected.",
            "input_label": "Testo da sintetizzare",
            "needs_context": False,
            "template_body": _template_body("summarization"),
            "default_rules": _default_rules["summarization"],
            "answer_format": _answer_format("summarization"),
        },
        "code_analysis": {
            "description": "Il modello analizza codice e identifica bug, security issues, best practice. Scoring su findings_schema.",
            "input_label": "Codice da analizzare",
            "needs_context": False,
            "template_body": _template_body("code_analysis"),
            "default_rules": _default_rules["code_analysis"],
            "answer_format": _answer_format("code_analysis"),
        },
        "code_documentation": {
            "description": "Il modello genera docstring/documentazione per il codice fornito. Scoring su struttura, completezza e stile.",
            "input_label": "Codice da documentare",
            "needs_context": False,
            "template_body": _template_body("code_documentation"),
            "default_rules": _default_rules["code_documentation"],
            "answer_format": _answer_format("code_documentation"),
        },
        "refactoring": {
            "description": "Il modello riscrive il codice applicando refactoring senza cambiare comportamento. Scoring su schema e similarità.",
            "input_label": "Codice da rifattorizzare",
            "needs_context": False,
            "template_body": _template_body("refactoring"),
            "default_rules": _default_rules["refactoring"],
            "answer_format": _answer_format("refactoring"),
        },
        "image_description": {
            "description": "Il modello descrive un'immagine in modo neutro. Scoring su oggetti rilevati e rispetto del limite parole.",
            "input_label": "Descrizione testuale dell'immagine (o istruzioni)",
            "needs_context": False,
            "template_body": _template_body("image_description"),
            "default_rules": _default_rules["image_description"],
            "answer_format": _answer_format("image_description"),
        },
        "ocr_extraction": {
            "description": "Il modello estrae dati da testo OCR di un documento. Scoring su field accuracy.",
            "input_label": "Testo OCR del documento",
            "needs_context": False,
            "template_body": _template_body("ocr_extraction"),
            "default_rules": _default_rules["ocr_extraction"],
            "answer_format": _answer_format("ocr_extraction"),
        },
        "speech_to_text_postprocess": {
            "description": "Il modello pulisce una trascrizione grezza e ne estrae action items. Scoring su clean_transcript e action_items_schema.",
            "input_label": "Trascrizione grezza",
            "needs_context": False,
            "template_body": _template_body("speech_to_text_postprocess"),
            "default_rules": _default_rules["speech_to_text_postprocess"],
            "answer_format": _answer_format("speech_to_text_postprocess"),
        },
        "contextual_insight": {
            "description": "Il modello analizza una conversazione multi-turno e produce insight strategici. Scoring su insight_count e must_include_themes.",
            "input_label": "Scenario / Conversazione multi-turno",
            "needs_context": True,
            "template_body": _template_body("contextual_insight"),
            "default_rules": _default_rules["contextual_insight"],
            "answer_format": _answer_format("contextual_insight"),
        },
    }


router = APIRouter(prefix="/test-cases", tags=["test_cases"])


@router.get("/", response_class=HTMLResponse)
async def test_case_list(request: Request, db: Session = Depends(get_db)):
    test_cases = db.query(TestCase).order_by(TestCase.library_id, TestCase.test_type_id, TestCase.title).all()
    test_types = db.query(TestType).all()
    from ..models import TestLibrary
    libraries = db.query(TestLibrary).all()
    lib_map = {lib.id: lib for lib in libraries}
    lib_groups = {}
    for tc in test_cases:
        lid = tc.library_id or "general"
        if lid not in lib_groups:
            lib_groups[lid] = {"label": lib_map[lid].label if lid in lib_map else "General", "cases": []}
        lib_groups[lid]["cases"].append(tc)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="test_case_form.html",
        context={
            "request": request,
            "lib_groups": lib_groups,
            "test_cases": test_cases,
            "test_types": test_types,
            "mode": "list",
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def test_case_new(request: Request, db: Session = Depends(get_db)):
    test_types = db.query(TestType).all()
    from ..models import TestLibrary
    libraries = db.query(TestLibrary).all()
    default_template = ""
    test_type_id = request.query_params.get("test_type_id", "")
    if test_type_id:
        from ..services.prompt_builder import PROMPT_TEMPLATES, ST_HEADER, MESSAGE_CONTAINER_TEMPLATE
        template = PROMPT_TEMPLATES.get(test_type_id, PROMPT_TEMPLATES.get("classification"))
        if template:
            default_template = template
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="test_case_form.html",
        context={"request": request, "test_types": test_types, "libraries": libraries, "type_formats": _get_type_formats(), "template_parts": _get_template_parts(), "default_expected": _get_default_expected_json(db), "type_examples": _get_type_examples(), "lib_groups": {}, "test_cases": [], "mode": "create", "tc": None, "default_template": default_template},
    )


@router.get("/create", response_class=HTMLResponse)
async def test_case_create_guided_get(request: Request, db: Session = Depends(get_db)):
    from ..models import TestLibrary
    test_types = db.query(TestType).filter(TestType.enabled == True).all()
    libraries = db.query(TestLibrary).filter(TestLibrary.enabled == True).all()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="test_case_create.html",
        context={
            "request": request,
            "test_types": test_types,
            "libraries": libraries,
            "type_meta": _build_type_meta(),
        },
    )


@router.post("/create")
async def test_case_create_guided_post(
    request: Request,
    title: str = Form(...),
    test_type_id: str = Form(...),
    library_id: str = Form(""),
    description: str = Form(""),
    input_text: str = Form(""),
    context_text: str = Form(""),
    system_prompt: str = Form(""),
    custom_rules: str = Form(""),
    expected_output_json: str = Form(""),
    expected_text: str = Form(""),
    difficulty: str = Form("medium"),
    risk_level: str = Form("low"),
    enabled: str = Form("true"),
    tags_json: str = Form(""),
    rubric_json: str = Form(""),
    db: Session = Depends(get_db),
):
    # Validate expected_output_json
    parsed_expected = None
    if expected_output_json.strip():
        try:
            parsed_expected = json.loads(expected_output_json)
        except json.JSONDecodeError as e:
            return HTMLResponse(
                f"<script>alert('Errore: Expected JSON non valido — {str(e)[:120]}');window.history.back();</script>"
            )

    # Validate classification label consistency
    if test_type_id == "classification" and isinstance(parsed_expected, dict):
        allowed = parsed_expected.get("allowed_labels", [])
        expected_label = (parsed_expected.get("expected") or {}).get("label", "")
        if expected_label and allowed and expected_label not in allowed:
            return HTMLResponse(
                f"<script>alert('Errore: la label attesa \"{expected_label}\" non è tra le classi ammesse.');window.history.back();</script>"
            )

    tc = TestCase(
        test_type_id=test_type_id,
        title=title,
        description=description or None,
        input_text=input_text or None,
        context_text=context_text or None,
        system_prompt=system_prompt or None,
        user_prompt_template=None,
        rules=custom_rules or None,
        expected_output_json=expected_output_json or None,
        expected_text=expected_text or None,
        tags_json=tags_json or None,
        rubric_json=rubric_json or None,
        difficulty=difficulty,
        risk_level=risk_level,
        enabled=enabled == "true",
        library_id=library_id or None,
    )
    db.add(tc)
    db.commit()
    return RedirectResponse(url="/test-cases", status_code=303)


@router.post("/")
async def test_case_create(
    request: Request,
    title: str = Form(...),
    test_type_id: str = Form(...),
    description: str = Form(""),
    input_text: str = Form(""),
    context_text: str = Form(""),
    system_prompt: str = Form(""),
    user_prompt_template: str = Form(""),
    rules: str = Form(""),
    expected_output_json: str = Form(""),
    expected_text: str = Form(""),
    expected_labels_json: str = Form(""),
    rubric_json: str = Form(""),
    tags_json: str = Form(""),
    difficulty: str = Form("medium"),
    risk_level: str = Form("low"),
    enabled: str = Form("true"),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    if rules.strip() and not user_prompt_template.strip():
        try:
            prompt_fields = {
                "test_type_id": test_type_id,
                "test_type": test_type_id,
                "instructions": description or test_type_id,
                "input_text": input_text or "",
                "context": context_text or "",
                "rules": rules,
            }
            if expected_output_json.strip():
                try:
                    exp = json.loads(expected_output_json)
                    if isinstance(exp, dict):
                        from ..services.prompt_builder import (
                            _build_field_list, _build_field_placeholders,
                            _get_allowed_labels, _get_constraints_text,
                            _get_format_constraint, _get_length_constraint,
                        )
                        prompt_fields["field_list"] = _build_field_list(exp)
                        prompt_fields["field_placeholders"] = _build_field_placeholders(exp)
                        prompt_fields["allowed_labels"] = _get_allowed_labels(exp)
                        prompt_fields["constraints"] = _get_constraints_text(exp)
                        prompt_fields["format_constraint"] = _get_format_constraint(exp)
                        prompt_fields["length_constraint"] = _get_length_constraint(exp)
                        prompt_fields["style"] = exp.get("style", "descrizione_neutra")
                        prompt_fields["language"] = exp.get("language", "it")
                        prompt_fields["doc_style"] = exp.get("style", "docstring_google")
                        prompt_fields["target"] = exp.get("target", "migliorare il codice")
                        prompt_fields["answer_absent_rule"] = (
                            "IMPORTANTE: se la risposta NON e presente nel contesto, imposta "
                            "answer_absent a true e lascia answer_text vuoto."
                        ) if exp.get("answer_absent") is not None else ""
                except Exception:
                    pass
            user_prompt_template = _assemble_prompt(prompt_fields)
        except Exception:
            user_prompt_template = user_prompt_template or ""
    uploaded_path = None
    if file and file.filename:
        valid, error = validate_upload(file.filename, file.size or 0)
        if not valid:
            return HTMLResponse(f"<script>alert('{error}');window.history.back();</script>")
        ext = os.path.splitext(file.filename)[1]
        stored_name = f"{uuid.uuid4().hex}{ext}"
        stored_path = f"app/uploads/{stored_name}"
        os.makedirs("app/uploads", exist_ok=True)
        content = await file.read()
        with open(stored_path, "wb") as f:
            f.write(content)
        uploaded_path = stored_path

        uf = UploadedFile(
            original_filename=file.filename,
            stored_path=stored_path,
            mime_type=file.content_type,
            size_bytes=file.size,
        )
        db.add(uf)

    tc = TestCase(
        test_type_id=test_type_id,
        title=title,
        description=description or None,
        input_text=input_text or None,
        input_file_path=uploaded_path,
        context_text=context_text or None,
        system_prompt=system_prompt or None,
        user_prompt_template=user_prompt_template or None,
        expected_output_json=expected_output_json or None,
        expected_text=expected_text or None,
        expected_labels_json=expected_labels_json or None,
        rubric_json=rubric_json or None,
        tags_json=tags_json or None,
        difficulty=difficulty,
        risk_level=risk_level,
        enabled=enabled == "true",
    )
    db.add(tc)
    db.commit()
    return RedirectResponse(url="/test-cases", status_code=303)


@router.get("/{id}/edit-guided", response_class=HTMLResponse)
async def test_case_edit_guided_get(id: int, request: Request, db: Session = Depends(get_db)):
    import json as _json
    from ..models import TestLibrary
    tc = db.query(TestCase).filter(TestCase.id == id).first()
    if not tc:
        return RedirectResponse(url="/test-cases")
    test_types = db.query(TestType).filter(TestType.enabled == True).all()
    libraries = db.query(TestLibrary).filter(TestLibrary.enabled == True).all()
    tc_json = _json.dumps({
        "id": tc.id,
        "test_type_id": tc.test_type_id,
        "library_id": tc.library_id or "",
        "title": tc.title or "",
        "description": tc.description or "",
        "input_text": tc.input_text or "",
        "context_text": tc.context_text or "",
        "system_prompt": tc.system_prompt or "",
        "expected_output_json": tc.expected_output_json or "",
        "expected_text": tc.expected_text or "",
        "difficulty": tc.difficulty or "medium",
        "risk_level": tc.risk_level or "low",
        "enabled": tc.enabled,
        "tags_json": tc.tags_json or "",
        "rubric_json": tc.rubric_json or "",
        "custom_rules": tc.rules or "",
        "has_legacy_prompt": bool(tc.user_prompt_template and tc.user_prompt_template.strip()),
    })
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="test_case_create.html",
        context={
            "request": request,
            "test_types": test_types,
            "libraries": libraries,
            "type_meta": _build_type_meta(),
            "tc": tc,
            "tc_json": tc_json,
            "edit_mode": True,
        },
    )


@router.post("/{id}/edit-guided")
async def test_case_edit_guided_post(
    id: int,
    request: Request,
    title: str = Form(...),
    test_type_id: str = Form(...),
    library_id: str = Form(""),
    description: str = Form(""),
    input_text: str = Form(""),
    context_text: str = Form(""),
    system_prompt: str = Form(""),
    custom_rules: str = Form(""),
    expected_output_json: str = Form(""),
    expected_text: str = Form(""),
    difficulty: str = Form("medium"),
    risk_level: str = Form("low"),
    enabled: str = Form("true"),
    tags_json: str = Form(""),
    rubric_json: str = Form(""),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone
    tc = db.query(TestCase).filter(TestCase.id == id).first()
    if not tc:
        return RedirectResponse(url="/test-cases")

    if expected_output_json.strip():
        try:
            parsed_expected = json.loads(expected_output_json)
        except json.JSONDecodeError as e:
            return HTMLResponse(
                f"<script>alert('Errore: Expected JSON non valido — {str(e)[:120]}');window.history.back();</script>"
            )
        if test_type_id == "classification" and isinstance(parsed_expected, dict):
            allowed = parsed_expected.get("allowed_labels", [])
            expected_label = (parsed_expected.get("expected") or {}).get("label", "")
            if expected_label and allowed and expected_label not in allowed:
                return HTMLResponse(
                    f"<script>alert('Errore: la label attesa \"{expected_label}\" non è tra le classi ammesse.');window.history.back();</script>"
                )

    tc.test_type_id = test_type_id
    tc.title = title
    tc.description = description or None
    tc.input_text = input_text or None
    tc.context_text = context_text or None
    tc.system_prompt = system_prompt or None
    tc.user_prompt_template = None
    tc.rules = custom_rules or None
    tc.expected_output_json = expected_output_json or None
    tc.expected_text = expected_text or None
    tc.tags_json = tags_json or None
    tc.rubric_json = rubric_json or None
    tc.difficulty = difficulty
    tc.risk_level = risk_level
    tc.enabled = enabled == "true"
    tc.library_id = library_id or None
    tc.updated_at = datetime.now(timezone.utc)
    db.commit()
    return RedirectResponse(url="/test-cases", status_code=303)


@router.get("/{id}", response_class=HTMLResponse)
async def test_case_detail(id: int, request: Request, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == id).first()
    if not tc:
        return RedirectResponse(url="/test-cases")
    test_types = db.query(TestType).all()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="test_case_form.html",
        context={"request": request, "tc": tc, "test_types": test_types, "lib_groups": {}, "test_cases": [], "mode": "detail"},
    )


@router.get("/{id}/edit", response_class=HTMLResponse)
async def test_case_edit(id: int, request: Request, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == id).first()
    if not tc:
        return RedirectResponse(url="/test-cases")
    test_types = db.query(TestType).all()
    if not tc.user_prompt_template or not tc.user_prompt_template.strip():
        try:
            prompt_fields = {
                "test_type_id": tc.test_type_id,
                "test_type": tc.test_type_id,
                "instructions": tc.description or tc.test_type_id,
                "input_text": tc.input_text or "",
                "context": tc.context_text or "",
                "rules": tc.rules or "",
                "description": tc.description or "",
            }
            if tc.expected_output_json and tc.expected_output_json.strip():
                try:
                    exp = json.loads(tc.expected_output_json)
                    if isinstance(exp, dict):
                        from ..services.prompt_builder import (
                            _build_field_list, _build_field_placeholders,
                            _get_allowed_labels, _get_constraints_text,
                            _get_format_constraint, _get_length_constraint,
                        )
                        prompt_fields["field_list"] = _build_field_list(exp)
                        prompt_fields["field_placeholders"] = _build_field_placeholders(exp)
                        prompt_fields["allowed_labels"] = _get_allowed_labels(exp)
                        prompt_fields["constraints"] = _get_constraints_text(exp)
                        prompt_fields["format_constraint"] = _get_format_constraint(exp)
                        prompt_fields["length_constraint"] = _get_length_constraint(exp)
                        prompt_fields["style"] = exp.get("style", "descrizione_neutra")
                        prompt_fields["language"] = exp.get("language", "it")
                        prompt_fields["doc_style"] = exp.get("style", "docstring_google")
                        prompt_fields["target"] = exp.get("target", "migliorare il codice")
                        prompt_fields["answer_absent_rule"] = (
                            "IMPORTANTE: se la risposta NON e presente nel contesto, imposta "
                            "answer_absent a true e lascia answer_text vuoto."
                        ) if exp.get("answer_absent") is not None else ""
                except Exception:
                    pass
            tc.user_prompt_template = _assemble_prompt(prompt_fields)
        except Exception:
            try:
                from ..services.test_runner import _build_prompt
                tt = db.query(TestType).filter(TestType.id == tc.test_type_id).first()
                tc.user_prompt_template = _build_prompt(tc, tt)
            except Exception:
                pass
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="test_case_form.html",
        context={"request": request, "tc": tc, "test_types": test_types, "type_formats": _get_type_formats(), "template_parts": _get_template_parts(), "default_expected": _get_default_expected_json(db), "type_examples": _get_type_examples(), "lib_groups": {}, "test_cases": [], "mode": "edit"},
    )


@router.post("/{id}")
async def test_case_update(
    id: int,
    request: Request,
    title: str = Form(...),
    test_type_id: str = Form(...),
    description: str = Form(""),
    input_text: str = Form(""),
    context_text: str = Form(""),
    system_prompt: str = Form(""),
    user_prompt_template: str = Form(""),
    rules: str = Form(""),
    expected_output_json: str = Form(""),
    expected_text: str = Form(""),
    expected_labels_json: str = Form(""),
    rubric_json: str = Form(""),
    tags_json: str = Form(""),
    difficulty: str = Form("medium"),
    risk_level: str = Form("low"),
    enabled: str = Form("true"),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    tc = db.query(TestCase).filter(TestCase.id == id).first()
    if not tc:
        return RedirectResponse(url="/test-cases")

    tc.test_type_id = test_type_id
    tc.title = title
    tc.description = description or None
    tc.input_text = input_text or None
    tc.context_text = context_text or None
    tc.system_prompt = system_prompt or None
    tc.user_prompt_template = user_prompt_template or None
    tc.rules = rules or None
    tc.expected_output_json = expected_output_json or None
    tc.expected_text = expected_text or None
    tc.expected_labels_json = expected_labels_json or None
    tc.rubric_json = rubric_json or None
    tc.tags_json = tags_json or None
    tc.difficulty = difficulty
    tc.risk_level = risk_level
    tc.enabled = enabled == "true"
    tc.updated_at = datetime.now(timezone.utc)

    if file and file.filename:
        valid, error = validate_upload(file.filename, file.size or 0)
        if not valid:
            return HTMLResponse(f"<script>alert('{error}');window.history.back();</script>")
        ext = os.path.splitext(file.filename)[1]
        stored_name = f"{uuid.uuid4().hex}{ext}"
        stored_path = f"app/uploads/{stored_name}"
        os.makedirs("app/uploads", exist_ok=True)
        content = await file.read()
        with open(stored_path, "wb") as f:
            f.write(content)
        tc.input_file_path = stored_path

    db.commit()
    return RedirectResponse(url="/test-cases", status_code=303)


@router.post("/{id}/delete")
async def test_case_delete(id: int, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == id).first()
    if tc:
        db.delete(tc)
        db.commit()
    return RedirectResponse(url="/test-cases", status_code=303)
