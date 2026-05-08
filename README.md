# LLM Local Test Lab

Piattaforma di benchmark per modelli LLM locali (Ollama) e remoti (OpenRouter). Permette di creare, eseguire e analizzare test strutturati su 10 tipologie tecniche, organizzati in 15 domini applicativi, con validazione automatica tramite modello giudice e reportistica completa.

---

## Indice

1. [Installazione](#installazione)
2. [Avvio](#avvio)
3. [Architettura](#architettura)
4. [Provider e modelli](#provider-e-modelli)
5. [Tipologie tecniche di test](#tipologie-tecniche-di-test)
6. [Domini applicativi (Librerie)](#domini-applicativi-librerie)
7. [Workflow](#workflow)
8. [Scoring e validazione](#scoring-e-validazione)
9. [Report e grafici](#report-e-grafici)
10. [Security](#security)
11. [Struttura progetto](#struttura-progetto)
12. [API JSON](#api-json)
13. [Troubleshooting](#troubleshooting)

---

## Installazione

```bash
cd llm-test-lab
pip install -r requirements.txt
```

**Dipendenze principali**: FastAPI, Uvicorn, SQLAlchemy, Jinja2, Pydantic, PyYAML, httpx, pandas, python-multipart, Chart.js.

---

## Avvio

```bash
uvicorn app.main:app --host 0.0.0.0 --port 7357
```

Apri: **http://localhost:7357**

Al primo avvio il database SQLite viene creato automaticamente. Modelli, provider, validatore, tipologie test e librerie demo vengono seedati dal file `config/config.yaml`.

Per resettare lo stato: cancella `data/app.db` e riavvia.

---

## Architettura

### Gerarchia logica

```
Libreria (dominio applicativo)
  └── Test Case (singolo scenario)
        └── Tipologia tecnica (capacita testata)
              └── Prompt (template + input)
              └── Risultato atteso (invisibile al modello)
              └── Metriche deterministiche + euristiche + validatore LLM
```

- **Libreria** = dominio (es. legal, medical, ecommerce)
- **Tipo test** = capacita tecnica (es. classification, data_extraction, rag_qa)
- **Test case** = scenario concreto
- **Run** = esecuzione batch su modelli selezionati
- **Report** = analisi aggregata dei risultati

### Flusso di esecuzione

1. Seleziona modelli, scegli librerie/test case
2. Crea la run
3. Avvia: per ogni coppia (modello, test_case) viene generato un prompt
4. Il prompt viene validato (no contaminazione da valori attesi)
5. Il modello produce una risposta
6. Metriche deterministiche calcolate per tipo test
7. Il validatore (modello giudice) valuta la risposta con vincoli deterministici
8. Scoring finale con tre campi pass: deterministic_passed, validator_passed, final_passed
9. Se deterministico perfetto ma validatore in disaccordo → needs_review, floor per classe task
10. Report aggregato generato

---

## Provider e modelli

### Provider configurati

| Provider | Endpoint | Timeout |
|---|---|---|
| **Ollama** | `http://172.23.144.1:11434/v1` | 300s |
| **OpenRouter** | `https://openrouter.ai/api/v1` | 300s |

### Validatore

| Parametro | Valore |
|---|---|
| Provider | OpenRouter |
| Modello primario | `deepseek/deepseek-v4-pro` |
| Modello fallback | `deepseek/deepseek-v4-flash` |
| Temperature | 0.0 |
| Max tokens | 4096 |
| Retry | 2 tentativi con fallback model e parsing robusto |
| Diagnostica | validator_status, error_message, raw_response, attempts |

---

## Tipologie tecniche di test

### 1. Classification
Classifica un testo in una categoria tra un elenco predefinito.
- **Metriche deterministiche**: json_validity, schema_compliance, field_accuracy, extra_fields_count
- **LLM**: semantic_score, format_score, hallucination_detected

### 2. Data Extraction
Estrae campi strutturati da testo non strutturato.
- **Metriche deterministiche**: json_validity, schema_compliance, field_accuracy, missing/extra/incorrect fields
- **Normalizzazione**: date, numeri, case-insensitive, spazi

### 3. RAG / Q&A documentale
Risponde a domande basandosi ESCLUSIVAMENTE su un contesto fornito.
- **Metriche deterministiche**: answer_absent_flag_match (decisiva), answer_absent_textual_absence_detected (diagnostica), citation_exact_substring_match (normalizzata, no fuzzy), citation_presence, top_level_citations_present
- **LLM**: semantic_score, completeness_score (N fatti richiesti e tutti presenti → completeness=1.0), unsupported_claim_rate
- **Regola**: "non contiene/non riporta" e' risposta negativa, NON answer_absent

### 4. Summarization
Riassume un testo rispettando formato, lunghezza e punti richiesti.
- **Metriche deterministiche**: max_words_respected, summary_word_count, summary_is_bulleted, key_points_is_list, task_format_compliance_deterministic
- **LLM**: semantic_score, completeness_score, factual_consistency

### 5. Code Analysis
Analizza codice identificando bug, vulnerabilita e anti-pattern.
- **Metriche deterministiche**: findings_schema_valid, allowed_type_valid (bug|security|best_practice|performance), allowed_severity_valid, finding_required_keys_present
- **LLM**: finding_accuracy, finding_groundedness, invented_bug_count, missed_bug_count, severity_correctness, recommendation_relevance
- **NOTA**: field_accuracy NON e' usata per code_analysis

### 6. Code Documentation
Genera documentazione tecnica in stile Google docstring.
- **Metriche deterministiche**: documentation_structure, hallucinated_parameters_count, examples_schema_violation, hallucinated_exception_count
- **LLM**: returns_correctness, raises_correctness, documentation_completeness_semantic

### 7. Refactoring
Riscrive codice preservando il comportamento e rispettando vincoli.
- **LLM**: behavior_preservation, refactoring_quality, introduced_bug_detected

### 8. Image Description
Descrive oggettivamente una scena visiva.
- **Metriche deterministiche**: required_fields_present, description_word_count, max_words_respected, objects_detected_is_list
- **LLM**: visual_object_accuracy, hallucinated_object_count, scene_type_correctness

### 9. OCR Extraction
Estrae dati strutturati da output OCR di documenti.
- **Metriche deterministiche**: field_accuracy, normalized field comparison

### 10. Speech-to-Text Postprocess
Pulisce trascrizioni grezze ed estrae action items.
- **Metriche deterministiche**: clean_transcript_present, action_items_schema_valid, entities_schema_valid, filler_terms_remaining_count (word-boundary regex), prompt_echo_exact_indicator_found
- **LLM**: action_item_accuracy, entity_extraction_accuracy_semantic
- **NOTA**: "Se formato e schema corretti, semantic_score >= 0.7. MAI score 0 se task eseguito."

---

## Domini applicativi (Librerie)

| ID | Libreria | Dominio | Tipologie coperte |
|---|---|---|---|
| `general` | Libreria Generale | benchmark | class, extract, summ, rag |
| `legal` | Documenti Legali | legal | class, extract, summ, rag |
| `academy` | Academy STEM | stem | class, extract, summ, rag |
| `network_security` | Network Security | cybersecurity | class, extract, summ, rag, code_analysis |
| `network_monitoring` | Network Monitoring | network | class, extract, summ, rag, code_analysis |
| `medical` | Ambito Medico | medical | class, extract, summ, rag, code_analysis |
| `claims_management` | Gestione Reclami | insurance | class, extract, summ, rag |
| `customer_support` | Assistenza Clienti | support | class, extract, summ, rag |
| `online_booking` | Prenotazioni | booking | class, extract, summ, rag |
| `system_administration` | System Admin | sysadmin | class, extract, summ, rag, code_analysis |
| `ecommerce` | E-commerce | ecommerce | class, extract, summ, rag |
| `software_development` | Software Dev | development | class, extract, summ, code_analysis, code_doc, refactoring |
| `document_processing` | Documenti | documents | class, extract, summ, ocr |
| `compliance` | Compliance | compliance | class, extract, summ, rag |
| `agent_development` | Agent Development | ai_agents | class, code_analysis, code_doc, summ, rag, data_extraction, refactoring |

---

## Workflow

### Creare un test case
1. Vai su **Librerie Test** → scegli la libreria
2. Clicca **Nuovo Test Case**
3. Compila: titolo, tipo test, descrizione, input, contesto, expected JSON, prompt template, tag, difficolta, rischio
4. Salva

### Eseguire una run
1. Vai su **Esecuzioni** → **Nuova Run**
2. Dai un nome, seleziona modelli (checkbox)
3. Espandi le librerie e seleziona i test case desiderati
4. Clicca **Crea Run**, poi **Avvia Run**
5. La run esegue i test in parallelo (configurabile, default 4)

### Analizzare i risultati
- **Dashboard**: score medio globale, miglior modello, error rate, latenza
- **Dettaglio run**: grafici per modello/dominio/tipologia; executive report; validator status
- **Dettaglio risultato**: validatore (stato, error message, tentativi, final_score_mode), metriche con evaluation_mode
- **Report**: score medio e pass rate per libreria, confronto modelli per dominio
- **Export**: CSV, JSON dalla pagina run e dalla pagina report

---

## Scoring e validazione

### Tre livelli di valutazione

| Livello | Modalita | Decisivo? | Esempi |
|---|---|---|---|
| Deterministico | Calcolato da codice | Si (guardrail) | json_validity, field_accuracy, max_words_respected |
| Euristico | Calcolato da codice | No (diagnostico) | lexical_similarity, token_overlap |
| LLM | Validatore | Si (task semantici/ibridi) | semantic_score, completeness, finding_accuracy |

### Score per tipologia

Ogni tipologia ha una formula deterministica specifica. Il final_score pesa deterministico + validatore + formato + latenza/stabilita/costo:

- **Task strutturati puri** (classification, data_extraction, ocr): det=50%, val=25%, fmt=10%
- **Task ibridi** (code_analysis, code_documentation, refactoring, STT): det=35%, val=40%, fmt=10%
- **Task semantici** (rag_qa, summarization, image_description): det=30%, val=45%, fmt=10%

### Tre campi pass

- `deterministic_passed`: deterministic_score >= soglia (0.80)
- `validator_passed`: dal validatore (forzato false se JSON/schema invalido)
- `final_passed`: final_score >= soglia (0.80) — il campo principale

### Regole di protezione

- Perfetto deterministico (1.0) + validatore >= 0.90 → final = 1.0
- Perfetto deterministico ma validatore in disaccordo → floor: 0.90 (strutturati), 0.85 (ibridi), 0.75 (semantici)
- JSON invalido cap 0.30, schema violato cap 0.50, refusal cap 0.10
- `final_score_mode`: "normal", "validator_conflict_adjusted", "validator_fallback"
- `needs_review`: true per task semantici/ibridi con validator_conflict o validator_fallback

---

## Report e grafici

### Dashboard
- Score medio per modello, Pass rate, Latenza media, Valid JSON rate

### Dettaglio run
- Score medio per modello / tipologia / dominio
- Confronto tra modelli per tipologia e per dominio
- Tabella risultati
- Executive report generato dal validatore
- Per ogni risultato: validator_status, error_message, final_score_mode

### Dettaglio risultato
- Prompt inviato, risposta modello, JSON estratto
- Validazione: stato validatore, errori, tentativi, modalita scoring
- Metriche con evaluation_mode (deterministic/heuristic/llm)

### Export
- CSV, JSON

---

## Sicurezza

- **API key**: mai salvate nel DB, mai esposte nella UI (mascherate)
- **Prompt**: mai contaminati da valori attesi; controllo pre-invio
- **Upload**: max 50 MB, solo estensioni consentite
- **Output**: escaping HTML in tutti i template
- **Chiavi**: cifrate (XOR + base64) nel DB; `secrets/secret.key` in `.gitignore`

---

## API JSON

| Endpoint | Descrizione |
|---|---|
| `GET /api/models` | Lista modelli configurati |
| `GET /api/test-cases` | Lista test case |
| `POST /api/test-cases` | Crea test case |
| `POST /api/test-runs` | Crea run |
| `POST /api/test-runs/{id}/start` | Avvia run |
| `GET /api/test-runs/{id}` | Stato run |
| `GET /api/test-runs/{id}/results` | Risultati run |
| `GET /api/reports/{id}` | Dettaglio report |

---

## Troubleshooting

| Problema | Soluzione |
|---|---|
| Ollama non raggiungibile | `ollama serve`, verifica URL in `config.yaml` |
| OpenRouter 401 | API key in `secrets/secret.key` non valida |
| Porta 7357 occupata | `lsof -i :7357` e kill |
| DB corrotto | Elimina `data/app.db`, riavvia |
| Prompt non validi | Controlla `user_prompt_template` nel test case |
| Score basso su risposta corretta | Verifica expected_output_json, rifai re-run |
| Validatore sempre 0 | Controlla validator_status e validator_error_message nel dettaglio risultato |
| Metriche None senza spiegazione | Ora il validatore mostra sempre validator_status e error_message |
| field_accuracy=0 su code_analysis | Normale: code_analysis non usa field_accuracy. Usa finding_accuracy dal validatore |
