import json

SEED_TEST_CASES = [
    # ============================
    # CLASSIFICATION (3 test cases)
    # ============================
    {
        "test_type_id": "classification",
        "title": "Classificazione ticket IT - Reset password",
        "description": "Classifica il ticket helpdesk nella categoria corretta",
        "input_text": "Ticket #4521 - Utente: marco.rossi@azienda.it. Problema: Dopo aver cambiato la password aziendale ieri, oggi non riesco piu ad accedere alla VPN. Il sistema dice 'credenziali non valide' ma sono certo di averle inserite correttamente. Ho gia provato 3 volte.",
        "expected_output_json": json.dumps({
            "schema": {"label": "string"},
            "expected": {"label": "helpdesk_password_reset"},
            "required_fields": ["label"],
            "allowed_labels": ["helpdesk_password_reset", "network_issue", "billing", "other"]
        }),
        "expected_text": "helpdesk_password_reset",
        "expected_labels_json": json.dumps({"correct_label": "helpdesk_password_reset"}),
        "rubric_json": json.dumps({
            "score_if_correct": 1.0,
            "score_if_wrong": 0.0,
            "invalid_penalty": -1.0
        }),
        "tags_json": json.dumps(["classification", "helpdesk", "IT"]),
        "difficulty": "easy",
        "risk_level": "low",
    },
    {
        "test_type_id": "classification",
        "title": "Classificazione ticket IT - Problema rete",
        "description": "Classifica un ticket relativo alla connettivita di rete",
        "input_text": "Ticket #5821 - Da stamattina il mio PC non si connette alla rete WiFi aziendale. Ho provato a riavviare e a dimenticare la rete ma non funziona. I colleghi nello stesso ufficio non hanno problemi.",
        "expected_output_json": json.dumps({
            "schema": {"label": "string"},
            "expected": {"label": "network_issue"},
            "required_fields": ["label"],
            "allowed_labels": ["helpdesk_password_reset", "network_issue", "billing", "other"]
        }),
        "expected_text": "network_issue",
        "expected_labels_json": json.dumps({"correct_label": "network_issue"}),
        "rubric_json": json.dumps({
            "score_if_correct": 1.0,
            "score_if_wrong": 0.0,
            "invalid_penalty": -1.0
        }),
        "tags_json": json.dumps(["classification", "helpdesk", "network"]),
        "difficulty": "easy",
        "risk_level": "low",
    },
    {
        "test_type_id": "classification",
        "title": "Classificazione fattura - Contestazione costo",
        "description": "Classifica un ticket sulla fatturazione",
        "input_text": "Ticket #7812 - Ho ricevuto la fattura di marzo con un addebito di 450 euro per 'servizi cloud premium' che non ho mai attivato. Chiedo il rimborso immediato e la disattivazione del servizio.",
        "expected_output_json": json.dumps({
            "schema": {"label": "string"},
            "expected": {"label": "billing"},
            "required_fields": ["label"],
            "allowed_labels": ["helpdesk_password_reset", "network_issue", "billing", "other"]
        }),
        "expected_text": "billing",
        "expected_labels_json": json.dumps({"correct_label": "billing"}),
        "rubric_json": json.dumps({
            "score_if_correct": 1.0,
            "score_if_wrong": 0.0,
            "invalid_penalty": -1.0
        }),
        "tags_json": json.dumps(["classification", "billing", "finance"]),
        "difficulty": "easy",
        "risk_level": "medium",
    },

    # ============================
    # DATA EXTRACTION (3 test cases)
    # ============================
    {
        "test_type_id": "data_extraction",
        "title": "Estrazione dati fattura - ACME SRL",
        "description": "Estrai i campi strutturati dal testo di una fattura",
        "input_text": "FATTURA N. 42 del 15/04/2026. Fornitore: ACME SRL, Via Roma 100, Milano. Totale: 1.280,40 EUR. Scadenza: 30/05/2026. Note: pagamento bonifico.",
        "expected_output_json": json.dumps({
            "schema": {
                "invoice_number": "string",
                "date": "date",
                "supplier": "string",
                "total": "number",
                "currency": "string"
            },
            "expected": {
                "invoice_number": "42",
                "date": "2026-04-15",
                "supplier": "ACME SRL",
                "total": 1280.40,
                "currency": "EUR"
            },
            "required_fields": ["invoice_number", "date", "supplier", "total", "currency"]
        }),
        "expected_text": "invoice_number: 42, date: 2026-04-15, supplier: ACME SRL, total: 1280.40, currency: EUR",
        "rubric_json": json.dumps({
            "field_match_weight": 0.6,
            "schema_compliance_weight": 0.4
        }),
        "tags_json": json.dumps(["extraction", "invoice", "finance"]),
        "difficulty": "easy",
        "risk_level": "low",
    },
    {
        "test_type_id": "data_extraction",
        "title": "Estrazione dati ordine - Multi-riga",
        "description": "Estrai i dati da un ordine con piu voci",
        "input_text": "Ordine #ORD-2026-0891 del 20/04/2026. Cliente: TechSolutions SpA, Torino. Articoli: [1] Monitor Dell 27\\\" Qty 2 Prezzo 249.90 cad. [2] Tastiera Logitech Qty 5 Prezzo 59.90 cad. [3] Mouse wireless Qty 5 Prezzo 29.90 cad. Totale ordine: 948.80 EUR. Spedizione: espresso 24h.",
        "expected_output_json": json.dumps({
            "schema": {
                "order_number": "string",
                "date": "date",
                "customer": "string",
                "total": "number",
                "currency": "string",
                "item_count": "integer"
            },
            "expected": {
                "order_number": "ORD-2026-0891",
                "date": "2026-04-20",
                "customer": "TechSolutions SpA",
                "total": 948.80,
                "currency": "EUR",
                "item_count": 3
            },
            "required_fields": ["order_number", "date", "customer", "total", "currency", "item_count"]
        }),
        "rubric_json": json.dumps({
            "field_match_weight": 0.5,
            "schema_compliance_weight": 0.3,
            "item_count_accuracy": 0.2
        }),
        "tags_json": json.dumps(["extraction", "order", "ecommerce"]),
        "difficulty": "medium",
        "risk_level": "low",
    },
    {
        "test_type_id": "data_extraction",
        "title": "Estrazione dati contatto - Business card",
        "description": "Estrai i dati di contatto da un testo informale",
        "input_text": "Ciao, mi chiamo Dott.ssa Laura Bianchi e sono la direttrice marketing di GreenEnergy Srl. Mi trovi al numero +39 02 4567 8901 oppure via email a l.bianchi@greenenergy.it. La sede e in Via Garibaldi 25, 20121 Milano. Il nostro sito e www.greenenergy.it",
        "expected_output_json": json.dumps({
            "schema": {
                "full_name": "string",
                "company": "string",
                "phone": "string",
                "email": "string",
                "address": "string",
                "website": "string"
            },
            "expected": {
                "full_name": "Laura Bianchi",
                "company": "GreenEnergy Srl",
                "phone": "+39 02 4567 8901",
                "email": "l.bianchi@greenenergy.it",
                "address": "Via Garibaldi 25, 20121 Milano",
                "website": "www.greenenergy.it"
            },
            "required_fields": ["full_name", "company", "email", "phone"]
        }),
        "rubric_json": json.dumps({
            "field_match_weight": 0.6,
            "schema_compliance_weight": 0.4
        }),
        "tags_json": json.dumps(["extraction", "contact", "business"]),
        "difficulty": "medium",
        "risk_level": "low",
    },

    # ============================
    # RAG / Q&A DOCUMENTALE (3 test cases)
    # ============================
    {
        "test_type_id": "rag_qa",
        "title": "RAG - Procedura incident management",
        "description": "Rispondi a una domanda basandoti solo sul contesto fornito",
        "input_text": "Quali sono i primi tre passi da seguire in caso di incidente critico di produzione?",
        "context_text": "PROCEDURA GESTIONE INCIDENTI CRITICI v3.1\n\nIn caso di incidente critico di produzione:\n1. Aprire il bridge entro 15 minuti dalla rilevazione\n2. Notificare l'incident manager di turno via telefono\n3. Aggiornare gli stakeholder ogni 30 minuti fino a risoluzione\n4. Documentare tutte le azioni intraprese nel ticket JIRA\n5. Se l'incidente dura oltre 2 ore, escalare al management\n6. A risoluzione, compilare il post-mortem entro 48 ore",
        "expected_output_json": json.dumps({
            "answer_facts": [
                "Aprire bridge entro 15 minuti",
                "Notificare incident manager",
                "Aggiornare stakeholder ogni 30 minuti"
            ],
            "must_cite_context": True,
            "answer_absent": False
        }),
        "expected_text": "1. Aprire il bridge entro 15 minuti. 2. Notificare l'incident manager. 3. Aggiornare gli stakeholder ogni 30 minuti.",
        "rubric_json": json.dumps({
            "fact_coverage_weight": 0.7,
            "context_citation_weight": 0.3,
            "hallucination_penalty": -0.5
        }),
        "tags_json": json.dumps(["rag", "incident", "procedure", "IT"]),
        "difficulty": "easy",
        "risk_level": "low",
    },
    {
        "test_type_id": "rag_qa",
        "title": "RAG - Policy ferie aziendali",
        "description": "QA su documento policy HR: le risposte devono usare solo il contesto",
        "input_text": "Quanti giorni di ferie spettano a un dipendente con 3 anni di anzianita e qual e la procedura per richiederle?",
        "context_text": "POLICY FERIE E PERMESSI - Aggiornata Gennaio 2026\n\nFerie: 26 giorni/anno per tutti i dipendenti. Dopo 5 anni: +2 giorni (totale 28). Dopo 10 anni: +4 giorni (totale 30).\n\nRichiesta: Inserire la richiesta sul portale HR almeno 10 giorni prima. Il manager ha 3 giorni per approvare. Le ferie non godute si accumulano fino a un massimo di 40 giorni; oltre tale soglia vengono perse.\n\nPermessi: 32 ore/anno di permessi retribuiti (ROL). 3 giorni/anno per eventi personali documentabili.",
        "expected_output_json": json.dumps({
            "answer_facts": [
                "26 giorni di ferie all'anno",
                "Richiedere sul portale HR almeno 10 giorni prima",
                "Il manager approva entro 3 giorni"
            ],
            "must_cite_context": True,
            "answer_absent": False
        }),
        "expected_text": "Il dipendente ha diritto a 26 giorni di ferie all'anno. Per richiederle deve inserire la richiesta sul portale HR almeno 10 giorni prima; il manager ha 3 giorni per approvare.",
        "rubric_json": json.dumps({
            "fact_coverage_weight": 0.6,
            "context_citation_weight": 0.4
        }),
        "tags_json": json.dumps(["rag", "HR", "policy"]),
        "difficulty": "medium",
        "risk_level": "low",
    },
    {
        "test_type_id": "rag_qa",
        "title": "RAG - Informazione non presente nel contesto",
        "description": "QA dove la risposta NON e nel contesto: il modello deve dirlo",
        "input_text": "Qual e il budget annuale allocato per la formazione del personale?",
        "context_text": "REPORT ATTIVITA FORMATIVE 2026\n\nCorsi erogati nel Q1: Python base (24 partecipanti), Leadership (18), Sicurezza IT (30).\nTotale ore formazione Q1: 72 ore erogate, 1.440 ore/uomo totali.\nSoddisfazione media: 4.3/5. Docenti: interni (60%), esterni (40%).\nProssime sessioni Q2: Python avanzato, Project Management base.\nIl programma di mentorship ha coinvolto 12 junior e 8 senior mentor.",
        "expected_output_json": json.dumps({
            "answer_facts": [],
            "must_cite_context": True,
            "answer_absent": True
        }),
        "rubric_json": json.dumps({
            "answer_absent_detection_weight": 1.0,
            "hallucination_penalty": -1.0
        }),
        "tags_json": json.dumps(["rag", "hallucination_test", "HR"]),
        "difficulty": "hard",
        "risk_level": "medium",
    },

    # ============================
    # SUMMARIZATION (2 test cases)
    # ============================
    {
        "test_type_id": "summarization",
        "title": "Sintesi verbale riunione - Decisione progetto",
        "description": "Riassumi il verbale in max 180 parole, formato elenco puntato",
        "input_text": "VERBALE RIUNIONE PROGETTO FENICE - 12/04/2026\n\nPresenti: Anna (PM), Marco (Dev), Giulia (UX), Stefano (Ops).\nOrdine del giorno: stato avanzamento Fase 2.\n\nAnna apre la riunione alle 10:00. La Fase 2 e completa al 85%. Marco segnala un bug critico nel modulo di autenticazione che richiede refactoring. Si stima 3 giorni aggiuntivi. Giulia ha completato i mockup delle nuove schermate; il cliente ha approvato il design ieri. Stefano conferma che l'ambiente di staging e pronto per il deploy. La decisione presa: approvata estensione di 3 giorni sulla milestone Fase 2. Owner della risoluzione bug: Marco. Nuova scadenza Fase 2: 28/04/2026. Prossima riunione: 15/04/2026.\n\nRiunione chiusa alle 10:45.",
        "expected_output_json": json.dumps({
            "required_points": [
                "Decisione approvata",
                "Owner assegnato",
                "Scadenza 28/04/2026"
            ],
            "forbidden_points": ["Budget approvato"],
            "max_words": 180,
            "format": "bullet_list"
        }),
        "rubric_json": json.dumps({
            "required_points_coverage": 0.6,
            "conciseness": 0.2,
            "format_compliance": 0.2,
            "forbidden_penalty": -0.3
        }),
        "tags_json": json.dumps(["summarization", "meeting", "project"]),
        "difficulty": "medium",
        "risk_level": "low",
    },
    {
        "test_type_id": "summarization",
        "title": "Sintesi articolo tecnico - IA e medicina",
        "description": "Riassumi un articolo con punti chiave, max 150 parole",
        "input_text": "L'intelligenza artificiale sta rivoluzionando la diagnostica medica. Un recente studio pubblicato su Nature Medicine (marzo 2026) ha dimostrato che un modello di deep learning addestrato su 1.2 milioni di radiografie toraciche e in grado di rilevare 14 patologie con un'accuratezza del 94.5%, superando radiologi esperti (91.2%). Il sistema, chiamato ChestAI-v3, utilizza un'architettura transformer modificata e processa ogni immagine in meno di 2 secondi. I falsi positivi sono stati ridotti del 37% rispetto alla versione precedente. L'FDA ha concesso l'autorizzazione 510(k) a gennaio 2026. Gli ospedali che hanno adottato il sistema riportano una riduzione del 28% nei tempi di refertazione. Criticita evidenziate: necessita di validazione su popolazioni piu diverse e potenziale overfitting su dati di training provenienti principalmente da ospedali USA.",
        "expected_output_json": json.dumps({
            "required_points": [
                "Sistema ChestAI-v3",
                "Accuratezza 94.5%",
                "Supera radiologi esperti",
                "Approvato FDA",
                "Riduzione 28% tempi refertazione"
            ],
            "forbidden_points": [],
            "max_words": 150,
            "format": "bullet_list"
        }),
        "rubric_json": json.dumps({
            "required_points_coverage": 0.6,
            "conciseness": 0.2,
            "format_compliance": 0.2
        }),
        "tags_json": json.dumps(["summarization", "AI", "medicine", "tech"]),
        "difficulty": "medium",
        "risk_level": "low",
    },

    # ============================
    # CODE ANALYSIS (2 test cases)
    # ============================
    {
        "test_type_id": "code_analysis",
        "title": "Analisi codice Python - Divisione per zero",
        "description": "Trova i bug in questa funzione Python",
        "input_text": "def calcola_media(numeri, dividi_per):\n    somma = 0\n    for n in numeri:\n        somma += n\n    media = somma / dividi_per\n    return media\n\n# Esempio d'uso:\nvalori = [10, 20, 30, 40]\ntry:\n    risultato = calcola_media(valori, 0)\n    print(f\\\"Media: {risultato}\\\")\nexcept:\n    print(\\\"Errore nel calcolo\\\")",
        "expected_output_json": json.dumps({
            "code_language": "Python",
            "expected_findings": [
                {
                    "type": "runtime_error",
                    "severity": "medium",
                    "description_contains": "divisione per zero"
                },
                {
                    "type": "best_practice",
                    "severity": "low",
                    "description_contains": "except nudo"
                }
            ],
            "expected_recommendations": [
                "gestire b == 0",
                "specificare il tipo di eccezione nel blocco except"
            ]
        }),
        "rubric_json": json.dumps({
            "finding_recall_weight": 0.6,
            "false_positive_penalty": -0.3,
            "recommendation_quality": 0.4
        }),
        "tags_json": json.dumps(["code_analysis", "python", "bug"]),
        "difficulty": "easy",
        "risk_level": "low",
    },
    {
        "test_type_id": "code_analysis",
        "title": "Analisi codice SQL - SQL injection",
        "description": "Identifica la vulnerabilita di sicurezza nel codice",
        "input_text": "def get_user(username):\n    import sqlite3\n    conn = sqlite3.connect('users.db')\n    cursor = conn.cursor()\n    query = f\\\"SELECT * FROM users WHERE username = '{username}'\\\"\n    cursor.execute(query)\n    return cursor.fetchone()\n\n@app.route('/user/<username>')\ndef user_profile(username):\n    user = get_user(username)\n    if user:\n        return jsonify({\\\"name\\\": user[1], \\\"email\\\": user[2]})\n    return jsonify({\\\"error\\\": \\\"not found\\\"}), 404",
        "expected_output_json": json.dumps({
            "code_language": "SQL",
            "expected_findings": [
                {
                    "type": "security",
                    "severity": "high",
                    "description_contains": "SQL injection"
                },
                {
                    "type": "best_practice",
                    "severity": "medium",
                    "description_contains": "query parametrizzata"
                }
            ],
            "expected_recommendations": [
                "Usare query parametrizzate con placeholder ?",
                "Validare e sanitizzare l'input username"
            ]
        }),
        "rubric_json": json.dumps({
            "finding_recall_weight": 0.6,
            "false_positive_penalty": -0.3,
            "severity_accuracy": 0.2,
            "recommendation_quality": 0.2
        }),
        "tags_json": json.dumps(["code_analysis", "security", "SQL"]),
        "difficulty": "medium",
        "risk_level": "high",
    },

    # ============================
    # CODE DOCUMENTATION (2 test cases)
    # ============================
    {
        "test_type_id": "code_documentation",
        "title": "Docstring funzione - Validazione email",
        "description": "Scrivi docstring in stile Google per questa funzione",
        "input_text": "import re\n\ndef validate_email(email):\n    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n    if not isinstance(email, str):\n        raise TypeError(\\\"L'email deve essere una stringa\\\")\n    if not email.strip():\n        raise ValueError(\\\"L'email non puo essere vuota\\\")\n    match = re.match(pattern, email)\n    if not match:\n        return False, \\\"Formato email non valido\\\"\n    local, domain = email.split('@')\n    if len(local) > 64:\n        return False, \\\"La parte locale supera i 64 caratteri consentiti\\\"\n    return True, \\\"Email valida\\\"",
        "expected_output_json": json.dumps({
            "must_include": ["parametri", "valore restituito", "eccezioni"],
            "style": "docstring_google",
            "language": "it"
        }),
        "rubric_json": json.dumps({
            "completeness_weight": 0.4,
            "technical_accuracy": 0.4,
            "style_compliance": 0.2
        }),
        "tags_json": json.dumps(["documentation", "docstring", "python"]),
        "difficulty": "easy",
        "risk_level": "low",
    },
    {
        "test_type_id": "code_documentation",
        "title": "Documentazione API REST endpoint",
        "description": "Genera documentazione per un endpoint REST",
        "input_text": "@app.get(\\\"/orders/\\\")\nasync def list_orders(\n    page: int = Query(1, ge=1),\n    limit: int = Query(20, ge=1, le=100),\n    status: str = Query(None, regex=\\\"^(pending|shipped|delivered|cancelled)$\\\"),\n    sort_by: str = Query(\\\"created_at\\\", regex=\\\"^(created_at|total|status)$\\\"),\n    order: str = Query(\\\"desc\\\", regex=\\\"^(asc|desc)$\\\")\n):\n    \\\"\\\"\\\"API per elencare gli ordini con paginazione e filtri\\\"\\\"\\\"\n    query = db.query(Order)\n    if status:\n        query = query.filter(Order.status == status)\n    total = query.count()\n    if order == \\\"asc\\\":\n        query = query.order_by(getattr(Order, sort_by).asc())\n    else:\n        query = query.order_by(getattr(Order, sort_by).desc())\n    orders = query.offset((page - 1) * limit).limit(limit).all()\n    return {\n        \\\"data\\\": [o.to_dict() for o in orders],\n        \\\"page\\\": page,\n        \\\"limit\\\": limit,\n        \\\"total\\\": total\n    }",
        "expected_output_json": json.dumps({
            "must_include": ["parametri", "valore restituito", "eccezioni", "esempio"],
            "style": "docstring_google",
            "language": "it"
        }),
        "rubric_json": json.dumps({
            "completeness_weight": 0.4,
            "technical_accuracy": 0.3,
            "style_compliance": 0.3
        }),
        "tags_json": json.dumps(["documentation", "API", "REST", "python"]),
        "difficulty": "medium",
        "risk_level": "low",
    },

    # ============================
    # REFACTORING (2 test cases)
    # ============================
    {
        "test_type_id": "refactoring",
        "title": "Refactoring - Eliminare duplicazione codice",
        "description": "Riscrivi il codice eliminando la duplicazione senza cambiare comportamento",
        "input_text": "def calcola_sconto_cliente(tipo_cliente, importo):\n    if tipo_cliente == \\\"standard\\\":\n        if importo > 1000:\n            sconto = importo * 0.05\n        elif importo > 500:\n            sconto = importo * 0.03\n        else:\n            sconto = importo * 0.01\n        return importo - sconto\n    elif tipo_cliente == \\\"premium\\\":\n        if importo > 1000:\n            sconto = importo * 0.10\n        elif importo > 500:\n            sconto = importo * 0.07\n        else:\n            sconto = importo * 0.05\n        return importo - sconto\n    elif tipo_cliente == \\\"vip\\\":\n        if importo > 1000:\n            sconto = importo * 0.15\n        elif importo > 500:\n            sconto = importo * 0.12\n        else:\n            sconto = importo * 0.10\n        return importo - sconto\n    else:\n        return importo",
        "expected_output_json": json.dumps({
            "must_preserve_behavior": True,
            "target": "ridurre duplicazione",
            "constraints": [
                "non cambiare signature pubbliche",
                "non introdurre dipendenze esterne"
            ],
            "tests_should_pass": True
        }),
        "rubric_json": json.dumps({
            "behavior_preservation": 0.5,
            "duplication_reduction": 0.3,
            "constraints_respected": 0.2
        }),
        "tags_json": json.dumps(["refactoring", "clean_code", "python"]),
        "difficulty": "hard",
        "risk_level": "medium",
    },
    {
        "test_type_id": "refactoring",
        "title": "Refactoring performance - Uso inefficiente liste",
        "description": "Ottimizza il codice per migliorare le performance",
        "input_text": "def trova_comuni(lista_a, lista_b):\n    comuni = []\n    for elemento in lista_a:\n        if elemento in lista_b and elemento not in comuni:\n            comuni.append(elemento)\n    return comuni\n\ndef filtra_per_categoria(prodotti):\n    risultato = []\n    for p in prodotti:\n        if p[\\\"categoria\\\"] == \\\"elettronica\\\" and p[\\\"prezzo\\\"] < 100:\n            risultato.append(p)\n    return sorted(risultato, key=lambda x: x[\\\"prezzo\\\"])",
        "expected_output_json": json.dumps({
            "must_preserve_behavior": True,
            "target": "migliorare performance",
            "constraints": [
                "non cambiare i nomi delle funzioni",
                "non introdurre dipendenze esterne"
            ],
            "tests_should_pass": True
        }),
        "rubric_json": json.dumps({
            "behavior_preservation": 0.4,
            "performance_improvement": 0.4,
            "constraints_respected": 0.2
        }),
        "tags_json": json.dumps(["refactoring", "performance", "python"]),
        "difficulty": "medium",
        "risk_level": "low",
    },

    # ============================
    # IMAGE DESCRIPTION (2 test cases)
    # ============================
    {
        "test_type_id": "image_description",
        "title": "Descrizione immagine - Scenario urbano",
        "description": "Descrivi la scena stradale in max 120 parole, italiano",
        "input_text": "[Immagine: scena di una strada cittadina con una bicicletta appoggiata a un palo, un casco sul sellino, persone che camminano sul marciapiede, alberi sullo sfondo e un semaforo verde]",
        "expected_output_json": json.dumps({
            "required_objects": ["bicicletta", "casco", "strada"],
            "forbidden_objects": ["automobile"],
            "style": "descrizione_neutra",
            "max_words": 120
        }),
        "rubric_json": json.dumps({
            "object_recall": 0.5,
            "object_hallucination_penalty": -0.3,
            "word_limit_compliance": 0.2,
            "style_compliance": 0.3
        }),
        "tags_json": json.dumps(["vision", "description", "scene"]),
        "difficulty": "easy",
        "risk_level": "low",
    },
    {
        "test_type_id": "image_description",
        "title": "Descrizione immagine - Ufficio moderno",
        "description": "Descrivi la scena d'ufficio in italiano, max 100 parole",
        "input_text": "[Immagine: ufficio open-space moderno con scrivanie bianche, un monitor curvo, una pianta verde in vaso, una libreria con libri tecnici, una lavagna a muro con post-it colorati, una finestra che da su un cortile alberato. Alle scrivanie ci sono due laptop chiusi e un tablet acceso con un grafico]",
        "expected_output_json": json.dumps({
            "required_objects": ["scrivan", "monitor", "pianta", "libreria"],
            "forbidden_objects": ["telefono fisso"],
            "style": "descrizione_neutra",
            "max_words": 100
        }),
        "rubric_json": json.dumps({
            "object_recall": 0.5,
            "object_hallucination_penalty": -0.3,
            "word_limit_compliance": 0.2,
            "style_compliance": 0.3
        }),
        "tags_json": json.dumps(["vision", "description", "office"]),
        "difficulty": "medium",
        "risk_level": "low",
    },

    # ============================
    # OCR EXTRACTION (2 test cases)
    # ============================
    {
        "test_type_id": "ocr_extraction",
        "title": "OCR - Carta d'identita",
        "description": "Estrai i dati anagrafici dal testo OCR di un documento",
        "input_text": "CARTA D'IDENTITA REPUBBLICA ITALIANA\n\nCognome: Rossi\nNome: Mario\nNato il: 15/03/1985\nLuogo: Milano (MI)\nResidenza: Via Dante 12, 20121 Milano\nStatura: 178 cm\nOcchi: Marroni\nCapelli: Castani\n\nValida fino al: 15/03/2035",
        "expected_output_json": json.dumps({
            "expected_text": "Mario Rossi, nato 15/03/1985 a Milano",
            "normalization": {
                "ignore_case": True,
                "ignore_extra_spaces": True
            },
            "expected_fields": {
                "name": "Mario Rossi",
                "date": "1985-03-15",
                "birth_place": "Milano"
            }
        }),
        "rubric_json": json.dumps({
            "field_accuracy": 0.6,
            "cer_weight": 0.2,
            "wer_weight": 0.2
        }),
        "tags_json": json.dumps(["ocr", "document", "identity"]),
        "difficulty": "easy",
        "risk_level": "low",
    },
    {
        "test_type_id": "ocr_extraction",
        "title": "OCR - Scontrino fiscale",
        "description": "Estrai dati da uno scontrino fiscale",
        "input_text": "SUPERMERCATO FRESCHISSIMO - Via Verdi 45, Roma\n\nData: 24/04/2026 Ora: 18:32\n\nPane integrale x1        2.40\nLatte fresco 1L x2       3.80\nUova biologiche x1       4.50\nPasta 500g x3           3.90\nPomodori pelati x2       2.60\nOlio EVO 750ml x1        7.90\n\nTOTALE: EUR 25.10\nPAGATO: Contanti EUR 30.00\nRESTO: EUR 4.90\n\nGrazie e arrivederci!",
        "expected_output_json": json.dumps({
            "expected_text": "Supermercato Freschissimo - Totale EUR 25.10 - 6 articoli",
            "normalization": {
                "ignore_case": True,
                "ignore_extra_spaces": True
            },
            "expected_fields": {
                "store": "Supermercato Freschissimo",
                "date": "2026-04-24",
                "total": "25.10",
                "items_count": 6
            }
        }),
        "rubric_json": json.dumps({
            "field_accuracy": 0.5,
            "cer_weight": 0.25,
            "wer_weight": 0.25
        }),
        "tags_json": json.dumps(["ocr", "receipt", "retail"]),
        "difficulty": "medium",
        "risk_level": "low",
    },

    # ============================
    # SPEECH-TO-TEXT POSTPROCESS (2 test cases)
    # ============================
    {
        "test_type_id": "speech_to_text_postprocess",
        "title": "STT Postprocess - Standup meeting",
        "description": "Pulisci la trascrizione e estrai action items",
        "input_text": "ok allora buongiorno a tutti emh... standup del venerdi... emh allora io ho finito il deploy della feature X ieri sera quindi oggi... emh marco si occupa del rollback se ci sono problemi... emh deploy venerdi si... e poi ... emh serve aggiornare la documentazione API entro lunedi, lo fa luca... ah dimenticavo il monitoring va controllato ma non lo fa nessuno per ora... basta io ho finito",
        "expected_output_json": json.dumps({
            "clean_transcript_contains": [
                "deploy venerdi",
                "Marco si occupa del rollback"
            ],
            "action_items": [
                {"owner": "Marco", "task": "rollback", "deadline": None},
                {"owner": "Luca", "task": "aggiornare documentazione API", "deadline": "lunedi"},
                {"owner": None, "task": "controllare monitoring", "deadline": None}
            ]
        }),
        "rubric_json": json.dumps({
            "transcript_cleanup_quality": 0.3,
            "entity_preservation": 0.3,
            "action_item_accuracy": 0.4
        }),
        "tags_json": json.dumps(["stt", "meeting", "standup"]),
        "difficulty": "medium",
        "risk_level": "low",
    },
    {
        "test_type_id": "speech_to_text_postprocess",
        "title": "STT Postprocess - Call center reclamo",
        "description": "Pulisci la trascrizione di una chiamata e estrai i dati rilevanti",
        "input_text": "cliente: si buongiorno emh... chiamo perche il mio ordine... aspetta... ordine numero 78901 del... emh del 10 aprile non mi e mai arrivato... ho pagato con carta... emh 45 euro e novanta... il tracking dice consegnato ma a me non e arrivato niente...\n\noperatore: ok mi scusi per il disguido signor... emh mi puo dare il suo nome e codice cliente?\n\ncliente: si certo, Paolo Verdi, codice VLN4821... emh voglio il rimborso o la spedizione di nuovo",
        "expected_output_json": json.dumps({
            "clean_transcript_contains": [
                "ordine 78901 del 10 aprile non consegnato",
                "Paolo Verdi codice VLN4821"
            ],
            "action_items": [
                {"owner": "operatore", "task": "verificare tracking ordine 78901", "deadline": None},
                {"owner": "operatore", "task": "avviare rimborso o rispedizione", "deadline": None}
            ]
        }),
        "rubric_json": json.dumps({
            "transcript_cleanup_quality": 0.3,
            "entity_preservation": 0.3,
            "action_item_accuracy": 0.4
        }),
        "tags_json": json.dumps(["stt", "call_center", "customer_service"]),
        "difficulty": "hard",
        "risk_level": "medium",
    },
]


def seed_test_cases(db):
    import datetime
    from ..models import TestCase

    existing_count = db.query(TestCase).count()
    if existing_count >= len(SEED_TEST_CASES):
        return 0

    added = 0
    for tc_data in SEED_TEST_CASES:
        existing = db.query(TestCase).filter(
            TestCase.title == tc_data["title"],
            TestCase.test_type_id == tc_data["test_type_id"],
        ).first()
        if existing:
            continue

        tc = TestCase(
            test_type_id=tc_data["test_type_id"],
            title=tc_data["title"],
            description=tc_data.get("description"),
            input_text=tc_data.get("input_text"),
            context_text=tc_data.get("context_text"),
            system_prompt=tc_data.get("system_prompt"),
            user_prompt_template=tc_data.get("user_prompt_template"),
            rules=tc_data.get("rules"),
            expected_output_json=tc_data.get("expected_output_json"),
            expected_text=tc_data.get("expected_text"),
            expected_labels_json=tc_data.get("expected_labels_json"),
            rubric_json=tc_data.get("rubric_json"),
            tags_json=tc_data.get("tags_json"),
            difficulty=tc_data.get("difficulty", "medium"),
            risk_level=tc_data.get("risk_level", "low"),
            enabled=True,
        )
        db.add(tc)
        added += 1

    if added > 0:
        db.commit()

    return added


def seed_test_cases_from_yaml(db, yaml_path: str = "config/testcase_initializer.yaml") -> int:
    import yaml
    from pathlib import Path
    from ..models import TestCase

    path = Path(yaml_path)
    if not path.exists():
        return -1

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to load {yaml_path}: {e}")
        return -1

    if not isinstance(data, list) or len(data) == 0:
        return -1

    existing_titles = set()
    for (title, tid) in db.query(TestCase.title, TestCase.test_type_id).all():
        existing_titles.add((title, tid))

    added = 0
    for tc_data in data:
        key = (tc_data.get("title"), tc_data.get("test_type_id"))
        if key in existing_titles:
            continue

        tc = TestCase(
            test_type_id=tc_data["test_type_id"],
            title=tc_data["title"],
            description=tc_data.get("description"),
            input_text=tc_data.get("input_text"),
            context_text=tc_data.get("context_text"),
            system_prompt=tc_data.get("system_prompt"),
            user_prompt_template=tc_data.get("user_prompt_template"),
            rules=tc_data.get("rules"),
            expected_output_json=tc_data.get("expected_output_json"),
            expected_text=tc_data.get("expected_text"),
            expected_labels_json=tc_data.get("expected_labels_json"),
            rubric_json=tc_data.get("rubric_json"),
            tags_json=tc_data.get("tags_json"),
            difficulty=tc_data.get("difficulty", "medium"),
            risk_level=tc_data.get("risk_level", "low"),
            enabled=tc_data.get("enabled", True),
        )
        if tc_data.get("library_id"):
            tc.library_id = tc_data["library_id"]
        db.add(tc)
        added += 1

    if added > 0:
        db.commit()

    return added


def seed_test_types_from_yaml(db, yaml_path: str = "config/testtype_initializer.yaml") -> int:
    import yaml
    from pathlib import Path
    from ..models import TestType

    path = Path(yaml_path)
    if not path.exists():
        return -1
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to load {yaml_path}: {e}")
        return -1
    if not isinstance(data, list) or len(data) == 0:
        return -1

    existing_ids = {row[0] for row in db.query(TestType.id).all()}
    added = 0
    for tt_data in data:
        if tt_data.get("id") in existing_ids:
            continue
        tt = TestType(
            id=tt_data["id"],
            label=tt_data.get("label", tt_data["id"]),
            description=tt_data.get("description"),
            expected_schema=tt_data.get("expected_schema"),
            expected_json_template=tt_data.get("expected_json_template"),
            enabled=tt_data.get("enabled", True),
        )
        db.add(tt)
        added += 1

    if added > 0:
        db.commit()
    return added
