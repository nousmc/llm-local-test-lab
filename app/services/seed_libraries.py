import json

LIBRARIES = [('general', 'Libreria Generale', 'Test per general', 'general', ['general']),
 ('legal', 'Documenti Legali', 'Test per legal', 'legal', ['legal']),
 ('academy',
  'Academy STEM',
  'Benchmark scientifici su matematica, fisica, chimica, biologia e metodo sperimentale',
  'stem',
  ['academy', 'stem', 'science', 'math', 'physics']),
 ('network_security', 'Network Security', 'Test per network_security', 'network_security', ['network_security']),
 ('network_monitoring', 'Network Monitoring', 'Test per network_monitoring', 'network_monitoring', ['network_monitoring']),
 ('medical', 'Ambito Medico', 'Test per medical', 'medical', ['medical']),
 ('claims_management', 'Gestione Reclami', 'Test per claims_management', 'claims_management', ['claims_management']),
 ('customer_support', 'Assistenza Clienti', 'Test per customer_support', 'customer_support', ['customer_support']),
 ('online_booking', 'Prenotazioni', 'Test per online_booking', 'online_booking', ['online_booking']),
 ('system_administration', 'System Admin', 'Test per system_administration', 'system_administration', ['system_administration']),
 ('ecommerce', 'E-commerce', 'Test per ecommerce', 'ecommerce', ['ecommerce']),
 ('software_development', 'Software Dev', 'Test per software_development', 'software_development', ['software_development']),
 ('document_processing', 'Documenti', 'Test per document_processing', 'document_processing', ['document_processing']),
 ('compliance', 'Compliance', 'Test per compliance', 'compliance', ['compliance']),
 ('agent_development',
  'Agent Development',
  'Test su sviluppo, reasoning, tool-calling e orchestrazione di agenti AI complessi',
  'ai_agents',
  ['agents', 'ai', 'reasoning', 'tool_calling', 'orchestration'])]

SEED_LIBRARY_TEST_CASES = [{'library_id': 'general',
  'test_type_id': 'classification',
  'title': 'Gen-Richiesta',
  'description': 'Classifica',
  'input_text': 'Ticket: info stato ordine #12345 del 01/04/2026.',
  'context_text': None,
  'expected_output_json': '{"schema": {"label": "string"}, "expected": {"label": "order_status"}, "required_fields": ["label"], "allowed_labels": '
                          '["order_status", "return_request", "technical_support", "other"]}',
  'tags_json': '["general"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'general',
  'test_type_id': 'data_extraction',
  'title': 'Gen-Estrazione',
  'description': 'Estrai',
  'input_text': 'Mario Bianchi, 333-1234567, m.bianchi@email.it, Roma, VLN-8821.',
  'context_text': None,
  'expected_output_json': '{"schema": {"nome": "string", "email": "string", "telefono": "string", "citta": "string"}, "expected": {"nome": "Mario Bianchi", '
                          '"email": "m.bianchi@email.it", "telefono": "333-1234567", "citta": "Roma"}, "required_fields": ["nome", "email"]}',
  'tags_json': '["general"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'general',
  'test_type_id': 'summarization',
  'title': 'Gen-Sintesi',
  'description': 'Riassumi',
  'input_text': 'Deploy release 3.2 previsto venerdi 12 maggio ore 22. Fermo 2 ore. Test entro giovedi.',
  'context_text': None,
  'expected_output_json': '{"format": "bullet_list", "max_words": 80, "required_points": ["deploy venerdi 12 maggio", "fermo 2 ore", "completare test entro '
                          'giovedi"]}',
  'tags_json': '["general"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'general',
  'test_type_id': 'rag_qa',
  'title': 'Gen-RAG',
  'description': 'Rispondi',
  'input_text': 'Quale metodo di pagamento per i rimborsi?',
  'context_text': 'POLICY: Rimborsi entro 14 giorni su stesso metodo di pagamento usato per acquisto. No rimborsi in contanti.',
  'expected_output_json': '{"answer_facts": ["stesso metodo di pagamento usato per acquisto", "no rimborsi in contanti"], "must_cite_context": true, '
                          '"answer_absent": false}',
  'tags_json': '["general"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'general',
  'test_type_id': 'data_extraction',
  'title': 'Gen-Normalizza',
  'description': 'Normalizza',
  'input_text': 'Riunione 15/03/2026 14:30-16:00. Partecipanti: Anna Rossi, Marco Verdi, Giulia Neri.',
  'context_text': None,
  'expected_output_json': '{"schema": {"data": "date", "ora_inizio": "string", "ora_fine": "string", "partecipanti": "integer"}, "expected": {"data": '
                          '"2026-03-15", "ora_inizio": "14:30", "ora_fine": "16:00", "partecipanti": 3}, "required_fields": ["data", "partecipanti"]}',
  'tags_json': '["general"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'legal',
  'test_type_id': 'classification',
  'title': 'Legal-Clausola',
  'description': 'Classifica',
  'input_text': 'Il Fornitore garantisce riservatezza dati Cliente per durata contratto e 24 mesi successivi.',
  'context_text': None,
  'expected_output_json': '{"schema": {"label": "string"}, "expected": {"label": "confidenzialita"}, "required_fields": ["label"], "allowed_labels": '
                          '["confidenzialita", "terminazione", "pagamento", "garanzia", "other"]}',
  'tags_json': '["legal"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'legal',
  'test_type_id': 'data_extraction',
  'title': 'Legal-Contratto',
  'description': 'Estrai',
  'input_text': 'Alfa Srl e Beta SpA. Data 01/02/2026. Durata 36 mesi. Alfa: servizio cloud. Beta: 5000 EUR/mese.',
  'context_text': None,
  'expected_output_json': '{"schema": {"parte_a": "string", "parte_b": "string", "data": "date", "durata": "integer", "importo": "number"}, "expected": '
                          '{"parte_a": "Alfa Srl", "parte_b": "Beta SpA", "data": "2026-02-01", "durata": 36, "importo": 5000}, "required_fields": ["parte_a", '
                          '"parte_b", "data"]}',
  'tags_json': '["legal"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'legal',
  'test_type_id': 'summarization',
  'title': 'Legal-Clausola',
  'description': 'Riassumi',
  'input_text': 'Preavviso scritto 90 giorni. Inadempimento grave: risoluzione immediata. Diritti maturati preservati.',
  'context_text': None,
  'expected_output_json': '{"format": "bullet_list", "max_words": 80, "required_points": ["preavviso 90 giorni", "risoluzione immediata per inadempimento '
                          'grave", "diritti maturati preservati"]}',
  'tags_json': '["legal"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'legal',
  'test_type_id': 'rag_qa',
  'title': 'Legal-RAG',
  'description': 'Rispondi',
  'input_text': 'Obblighi titolare trattamento GDPR?',
  'context_text': 'GDPR Art.24: misure tecniche e organizzative adeguate per garantire e dimostrare conformita trattamento. Misure riesaminate e aggiornate '
                  'periodicamente.',
  'expected_output_json': '{"answer_facts": ["misure tecniche e organizzative adeguate", "dimostrare conformita", "riesame periodico"], "must_cite_context": '
                          'true, "answer_absent": false}',
  'tags_json': '["legal"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'legal',
  'test_type_id': 'data_extraction',
  'title': 'Legal-Rischi',
  'description': 'Estrai',
  'input_text': 'No danni indiretti. Cap 50% contratto. Nessuna penale sotto 30 giorni.',
  'context_text': None,
  'expected_output_json': '{"schema": {"limitazione": "string", "cap": "number", "penale": "string"}, "expected": {"limitazione": "no danni indiretti", "cap": '
                          '50, "penale": "nessuna penale sotto 30 giorni"}, "required_fields": ["limitazione", "cap"]}',
  'tags_json': '["legal"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'network_security',
  'test_type_id': 'classification',
  'title': 'Sec-Alert',
  'description': 'Classifica',
  'input_text': 'SSH brute force da 203.0.113.42 su root@prod-01. 150 tentativi in 5 min. IP malevolo noto.',
  'context_text': None,
  'expected_output_json': '{"schema": {"label": "string"}, "expected": {"label": "brute_force"}, "required_fields": ["label"], "allowed_labels": '
                          '["brute_force", "port_scan", "malware", "data_exfiltration", "other"]}',
  'tags_json': '["security"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'network_security',
  'test_type_id': 'data_extraction',
  'title': 'Sec-Estrazione',
  'description': 'Estrai',
  'input_text': 'SEC-2026-0421. 192.0.2.55 -> 10.0.1.12:22. 21/04/2026. HIGH. IP bloccato 3600s.',
  'context_text': None,
  'expected_output_json': '{"schema": {"alert_id": "string", "src": "string", "dst": "string", "severity": "string", "action": "string"}, "expected": '
                          '{"alert_id": "SEC-2026-0421", "src": "192.0.2.55", "dst": "10.0.1.12", "severity": "HIGH", "action": "IP bloccato 3600s"}, '
                          '"required_fields": ["src", "severity", "action"]}',
  'tags_json': '["security"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'network_security',
  'test_type_id': 'summarization',
  'title': 'Sec-Incidente',
  'description': 'Riassumi',
  'input_text': '10/05/2026 03:15 WKSTN-045 traffico verso C2. SOC isola host 03:22. Esfiltrazione elenco dipendenti. No password.',
  'context_text': None,
  'expected_output_json': '{"format": "bullet_list", "max_words": 80, "required_points": ["traffico verso C2", "host isolato entro 7 minuti", "esfiltrazione '
                          'elenco dipendenti", "nessuna password compromessa"]}',
  'tags_json': '["security"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'network_security',
  'test_type_id': 'rag_qa',
  'title': 'Sec-RAG',
  'description': 'Rispondi',
  'input_text': 'Primo passo dopo incidente sicurezza?',
  'context_text': 'IRP v2: 1. Isolare sistemi compromessi dalla rete. 2. Acquisire log e snapshot. 3. Notificare CISO e DPO entro 60 minuti.',
  'expected_output_json': '{"answer_facts": ["isolare sistemi compromessi dalla rete", "containment immediato"], "must_cite_context": true, "answer_absent": '
                          'false}',
  'tags_json': '["security"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'network_security',
  'test_type_id': 'code_analysis',
  'title': 'Sec-Analisi',
  'description': 'Analizza',
  'input_text': 'GET /admin/login.php?user=admin OR 1=1 403 | GET /admin/login.php?user=admin; DROP TABLE users;-- 403',
  'context_text': None,
  'expected_output_json': '{"expected_findings": [{"type": "security", "severity": "high", "description_contains": "SQL injection"}], '
                          '"expected_recommendations": ["Bloccare IP sorgente", "Verificare WAF", "Audit endpoint admin"]}',
  'tags_json': '["security"]',
  'difficulty': 'medium',
  'risk_level': 'high',
  'enabled': True},
 {'library_id': 'network_monitoring',
  'test_type_id': 'summarization',
  'title': 'NM-Disservizio',
  'description': 'Riassumi',
  'input_text': 'VPN Napoli interrotta 14:22 18/05/2026 per guasto HW concentratore. 47 utenti disconnessi. Failover fallito per bug firmware. Ripristino '
                'manuale 15:10 (48 min). Upgrade firmware programmato 20/05.',
  'context_text': None,
  'expected_output_json': '{"format": "bullet_list", "max_words": 80, "required_points": ["VPN Napoli interrotta", "guasto hardware", "47 utenti coinvolti", '
                          '"ripristino 48 minuti"]}',
  'tags_json': '["network"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'network_monitoring',
  'test_type_id': 'rag_qa',
  'title': 'NM-Runbook',
  'description': 'Rispondi',
  'input_text': 'Sonda SNMP non risponde da 5 minuti: procedura?',
  'context_text': 'RUNBOOK: 1) Ping host. 2) Ping OK riavvia snmpd. 3) Ping KO contatta team sede. 4) No risposta ticket P1. 5) Ticket non preso in 10min '
                  'scala manager.',
  'expected_output_json': '{"answer_facts": ["verificare ping ICMP", "riavviare snmpd se ping OK", "contattare team se ping KO", "aprire ticket P1 se nessuno '
                          'risponde"], "must_cite_context": true, "answer_absent": false}',
  'tags_json': '["network"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'network_monitoring',
  'test_type_id': 'code_analysis',
  'title': 'NM-Flapping',
  'description': 'Analizza',
  'input_text': 'Gi0/12 down 10:15:22 loop guard block VLAN10 up 10:15:25 down 10:15:28 up 10:15:35. Flapping 13 secondi.',
  'context_text': None,
  'expected_output_json': '{"expected_findings": [{"type": "network", "severity": "medium", "description_contains": "flapping su porta"}], '
                          '"expected_recommendations": ["Controllare cavo e SFP", "Verificare contatori errore", "Disabilitare se persiste"]}',
  'tags_json': '["network"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'medical',
  'test_type_id': 'summarization',
  'title': 'MD-Anamnesi',
  'description': 'Riassumi',
  'input_text': 'Uomo 45a cefalea frontale 2 settimane 6/10. Peggiora rumore migliora buio. No trauma cranico. PA 135/85. Familiarita emicrania materna. RM '
                'encefalo 2024 nella norma.',
  'context_text': None,
  'expected_output_json': '{"format": "bullet_list", "max_words": 80, "required_points": ["cefalea frontale 2 settimane", "peggiora con rumore", "pressione '
                          '135 su 85", "familiarita emicrania"]}',
  'tags_json': '["medical"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'medical',
  'test_type_id': 'rag_qa',
  'title': 'MD-Protocollo',
  'description': 'Rispondi',
  'input_text': 'Febbre: quando rivolgersi al medico?',
  'context_text': 'PROTOCOLLO: Febbre oltre 38C per 72h richiede valutazione. Oltre 40C pronto soccorso. Con difficolta respiratoria chiamare 112. Con '
                  'rigidita nucale urgenza.',
  'expected_output_json': '{"answer_facts": ["febbre oltre 38C per 72 ore", "oltre 40C pronto soccorso", "difficolta respiratoria 112", "rigidita nucale '
                          'urgenza"], "must_cite_context": true, "answer_absent": false}',
  'tags_json': '["medical"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'claims_management',
  'test_type_id': 'summarization',
  'title': 'CL-Auto',
  'description': 'Riassumi',
  'input_text': 'Noleggio auto 22/04: graffi preesistenti portiera destra. Addetto disse li segno dopo ma non registro. Addebito 400 EUR a riconsegna. '
                'Documentazione fotografica con timestamp presente.',
  'context_text': None,
  'expected_output_json': '{"format": "bullet_list", "max_words": 80, "required_points": ["graffi preesistenti non segnalati", "addetto non ha registrato", '
                          '"addebito 400 EUR", "documentazione fotografica"]}',
  'tags_json': '["claims"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'claims_management',
  'test_type_id': 'rag_qa',
  'title': 'CL-RAG',
  'description': 'Rispondi',
  'input_text': 'Tempi risposta assicurazione a reclamo?',
  'context_text': 'PROCEDURA: 30 giorni primo riscontro. 60 giorni per danni a terzi. Sospensione per richiesta documenti. Penale 50 EUR giorno ritardo.',
  'expected_output_json': '{"answer_facts": ["30 giorni primo riscontro", "60 giorni danni a terzi", "sospensione per documentazione", "penale 50 EUR '
                          'giorno"], "must_cite_context": true, "answer_absent": false}',
  'tags_json': '["claims"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'customer_support',
  'test_type_id': 'summarization',
  'title': 'CS-Conversazione',
  'description': 'Riassumi',
  'input_text': 'Notebook si spegne dopo 10 minuti. Stesso problema a batteria e con alimentatore. Ventola rumorosa e scocca calda. Nessun aggiornamento '
                'recente. Probabile surriscaldamento. Ticket assistenza tecnica aperto.',
  'context_text': None,
  'expected_output_json': '{"format": "bullet_list", "max_words": 80, "required_points": ["spegnimento dopo 10 minuti", "ventola rumorosa scocca calda", '
                          '"stesso problema con alimentatore", "ticket assistenza tecnica"]}',
  'tags_json': '["support"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'customer_support',
  'test_type_id': 'rag_qa',
  'title': 'CS-KB',
  'description': 'Rispondi',
  'input_text': 'Come resettare SmartHub v2 a impostazioni fabbrica?',
  'context_text': 'KB: Tenere premuto reset 15 secondi. LED rosso 3 lampeggi. Rilasciare dopo terzo lampeggio. Riavvio impostazioni fabbrica. Dati locali '
                  'persi permanentemente.',
  'expected_output_json': '{"answer_facts": ["tenere premuto reset 15 secondi", "LED rosso 3 lampeggi", "rilasciare dopo terzo", "dati locali persi"], '
                          '"must_cite_context": true, "answer_absent": false}',
  'tags_json': '["support"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'online_booking',
  'test_type_id': 'summarization',
  'title': 'BK-Hotel',
  'description': 'Riassumi',
  'input_text': 'Camera doppia vista lago 20-21 giugno anniversario matrimonio. Preferenza vasca idromassaggio e balcone. Arrivo venerdi ore 15 partenza '
                'domenica dopo colazione.',
  'context_text': None,
  'expected_output_json': '{"format": "bullet_list", "max_words": 80, "required_points": ["doppia vista lago 20-21 giugno", "anniversario matrimonio", "vasca '
                          'idromassaggio e balcone", "arrivo ven 15 check-out dom"]}',
  'tags_json': '["booking"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'online_booking',
  'test_type_id': 'rag_qa',
  'title': 'BK-Policy',
  'description': 'Rispondi',
  'input_text': 'Cancellazione 3 giorni prima check-in: quanto pago?',
  'context_text': 'POLICY: Cancellazione gratuita oltre 7gg prima. 30% tra 7 e 3gg. 70% tra 3gg e 24h. 100% meno 24h o no-show. Tariffe non rimborsabili mai.',
  'expected_output_json': '{"answer_facts": ["30% tra 7 e 3 giorni", "70% tra 3 giorni e 24 ore", "cancellazione gratuita oltre 7 giorni"], '
                          '"must_cite_context": true, "answer_absent": false}',
  'tags_json': '["booking"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'system_administration',
  'test_type_id': 'summarization',
  'title': 'SA-FS',
  'description': 'Riassumi',
  'input_text': '03:45 monitoring /var/log 98% su log-server-01. rsyslog smette di scrivere. 03:52 rotazione manuale log vecchi 30gg. 45GB recuperati su '
                '450GB. 04:10 servizio ripreso. Root cause: lock orfano logrotate dopo riavvio.',
  'context_text': None,
  'expected_output_json': '{"format": "bullet_list", "max_words": 80, "required_points": ["filesystem /var/log al 98%", "rsyslog interrotto", "45GB '
                          'recuperati", "lock orfano logrotate"]}',
  'tags_json': '["sysadmin"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'system_administration',
  'test_type_id': 'rag_qa',
  'title': 'SA-Nginx',
  'description': 'Rispondi',
  'input_text': 'Procedura riavvio sicuro nginx in produzione?',
  'context_text': 'RUNBOOK: 1) nginx -t per test. 2) systemctl reload per riavvio a caldo. 3) Se reload fallisce systemctl restart. 4) Verificare con '
                  'systemctl status. 5) Se inconsistente: stop attesa 5s start. 6) Monitorare error.log.',
  'expected_output_json': '{"answer_facts": ["nginx -t test configurazione", "systemctl reload caldo", "restart se reload fallisce", "stop attesa 5s start se '
                          'inconsistente"], "must_cite_context": true, "answer_absent": false}',
  'tags_json': '["sysadmin"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'system_administration',
  'test_type_id': 'code_analysis',
  'title': 'SA-Apache',
  'description': 'Analizza',
  'input_text': 'Apache error: MaxRequestWorkers reached consider raising. Child pid 1234 exit signal Segmentation fault 11. Client 192.168.1.100 invalid HTTP '
                'syntax.',
  'context_text': None,
  'expected_output_json': '{"expected_findings": [{"type": "configuration", "severity": "high", "description_contains": "MaxRequestWorkers raggiunto"}, '
                          '{"type": "bug", "severity": "high", "description_contains": "Segmentation fault child"}], "expected_recommendations": ["Aumentare '
                          'MaxRequestWorkers", "Indagare causa segfault", "Bloccare client malevolo"]}',
  'tags_json': '["sysadmin"]',
  'difficulty': 'medium',
  'risk_level': 'high',
  'enabled': True},
 {'library_id': 'ecommerce',
  'test_type_id': 'summarization',
  'title': 'EC-Taglia',
  'description': 'Riassumi',
  'input_text': 'ORD-8901 felpa taglia M ricevuta taglia L. Reso gratuito con etichetta email. Taglia M disponibile e spedita oggi stesso. Ritiro contestuale '
                'taglia errata.',
  'context_text': None,
  'expected_output_json': '{"format": "bullet_list", "max_words": 80, "required_points": ["felpa M ricevuta L", "reso gratuito", "M disponibile spedita", '
                          '"ritiro contestuale"]}',
  'tags_json': '["ecommerce"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'ecommerce',
  'test_type_id': 'rag_qa',
  'title': 'EC-Resi',
  'description': 'Rispondi',
  'input_text': 'Posso restituire prodotto acquistato 20 giorni fa?',
  'context_text': 'POLICY: Resi entro 30 giorni dalla consegna senza motivazione. Prodotto integro in confezione originale con accessori. Prodotti igiene solo '
                  'con sigillo intatto. Oltre 30gg solo difetti di conformita entro 60gg dalla scoperta.',
  'expected_output_json': '{"answer_facts": ["30 giorni dalla consegna", "integro in confezione originale", "igiene solo sigillo intatto", "difetti conformita '
                          'entro 60 giorni"], "must_cite_context": true, "answer_absent": false}',
  'tags_json': '["ecommerce"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'software_development',
  'test_type_id': 'code_documentation',
  'title': 'SD-Doc',
  'description': 'Documenta',
  'input_text': 'def find_duplicates(items):\n'
                '    seen = set()\n'
                '    dups = []\n'
                '    for i in items:\n'
                '        if i in seen: dups.append(i)\n'
                '        else: seen.add(i)\n'
                '    return dups',
  'context_text': None,
  'expected_output_json': '{"must_include": ["parametri", "valore restituito", "esempio utilizzo"], "style": "docstring_google", "language": "it"}',
  'tags_json': '["development"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'software_development',
  'test_type_id': 'refactoring',
  'title': 'SD-Refactor',
  'description': 'Rifattorizza',
  'input_text': 'def get_name(u): return u.first + " " + u.last if u.first and u.last else u.first or "Unknown"\n'
                'def get_display(u): return u.first + " " + u.last if u.first and u.last else u.first or "Unknown"',
  'context_text': None,
  'expected_output_json': '{"must_preserve_behavior": true, "target": "ridurre duplicazione codice", "constraints": ["non cambiare firma funzioni", "non '
                          'introdurre dipendenze"]}',
  'tags_json': '["development"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'software_development',
  'test_type_id': 'summarization',
  'title': 'SD-Changelog',
  'description': 'Riassumi',
  'input_text': 'v2.4.1: OAuth2 Google+Microsoft. API bulk-import utenti. Fix race condition database. N+1 query ottimizzazione -60%. Cache Redis sessioni. '
                'Deprecato API v1 products.',
  'context_text': None,
  'expected_output_json': '{"format": "bullet_list", "max_words": 80, "required_points": ["OAuth2 Google e Microsoft", "fix race condition database", "N+1 '
                          'optimization 60%", "cache Redis", "deprecazione API v1"]}',
  'tags_json': '["development"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'document_processing',
  'test_type_id': 'ocr_extraction',
  'title': 'DP-CI',
  'description': 'Estrai',
  'input_text': 'Carta Identita: Rossi Mario nato 15/03/1985 Milano. Residente Via Dante 12 20121 Milano. Documento CA1234567 valido fino 15/03/2035.',
  'context_text': None,
  'expected_output_json': '{"expected_fields": {"nome": "Mario Rossi", "data_nascita": "1985-03-15", "luogo": "Milano", "residenza": "Via Dante 12 20121 '
                          'Milano", "documento": "CA1234567", "scadenza": "2035-03-15"}}',
  'tags_json': '["documents"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'document_processing',
  'test_type_id': 'summarization',
  'title': 'DP-Collaudo',
  'description': 'Riassumi',
  'input_text': 'Collaudo 05/05/2026 impianto elettrico Via Garibaldi 12 Milano. OK: terra 0.8 Ohm, isolamento 2-5 MOhm, differenziali 30ms, magnetotermiche '
                'coordinate. NC: schema elettrico assente a bordo quadro. Prescrizione 30 giorni. POSITIVO CON PRESCRIZIONE.',
  'context_text': None,
  'expected_output_json': '{"format": "bullet_list", "max_words": 80, "required_points": ["collaudo POSITIVO con prescrizione", "verifiche sicurezza '
                          'superate", "NC schema elettrico assente", "prescrizione 30 giorni"]}',
  'tags_json': '["documents"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'compliance',
  'test_type_id': 'summarization',
  'title': 'CP-Retention',
  'description': 'Riassumi',
  'input_text': 'DATA RETENTION POLICY: Dati clienti 10 anni da fine contratto. Marketing 24 mesi da ultimo consenso. Log accesso 36 mesi. Dati biometrici '
                'massimo 12 mesi. Backup AES-256 massimo 5 anni cancellazione automatica.',
  'context_text': None,
  'expected_output_json': '{"format": "bullet_list", "max_words": 80, "required_points": ["clienti 10 anni", "marketing 24 mesi", "log accesso 36 mesi", '
                          '"biometrici 12 mesi", "backup AES-256 5 anni"]}',
  'tags_json': '["compliance"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'compliance',
  'test_type_id': 'rag_qa',
  'title': 'CP-RAG',
  'description': 'Rispondi',
  'input_text': 'Procedura richiesta accesso dati interessato GDPR Art.15?',
  'context_text': 'PROCEDURA: 1) Ricezione richiesta. 2) Verifica identita 5gg. 3) Raccolta dati da CRM ERP HR. 4) Verifica assenza dati terzi. 5) Risposta '
                  'formato strutturato entro 30gg. 6) Proroga 60gg per richieste complesse con motivazione.',
  'expected_output_json': '{"answer_facts": ["verifica identita entro 5 giorni", "raccolta da tutti i sistemi", "risposta entro 30 giorni", "proroga 60 giorni '
                          'complesse"], "must_cite_context": true, "answer_absent": false}',
  'tags_json': '["compliance"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'compliance',
  'test_type_id': 'rag_qa',
  'title': 'CP-Assente',
  'description': 'Verifica',
  'input_text': 'Sistema videosorveglianza aziendale conforme a tutte le normative vigenti?',
  'context_text': 'Sistema copre ingresso parcheggio corridoio. Cartelli informativi gen 2026. Registrazioni 7 giorni. Nessun DPO nominato per supervisione.',
  'expected_output_json': '{"answer_facts": [], "must_cite_context": true, "answer_absent": true}',
  'tags_json': '["compliance"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'network_monitoring',
  'test_type_id': 'classification',
  'title': 'network_monitoring-Classificazione-evento',
  'description': 'Classifica lo scenario di dominio',
  'input_text': 'Evento: utilizzo link WAN al 95% per 20 minuti con aumento latenza e code su interfaccia uplink.',
  'context_text': None,
  'expected_output_json': '{"schema": {"label": "string"}, "expected": {"label": "congestione"}, "required_fields": ["label"], "allowed_labels": '
                          '["congestione", "degrado_prestazioni", "down_hard", "flapping", "other"]}',
  'tags_json': '["network_monitoring"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'network_monitoring',
  'test_type_id': 'data_extraction',
  'title': 'network_monitoring-Estrazione-uplink',
  'description': 'Estrai dati strutturati di dominio',
  'input_text': 'Alert uplink-fw-01 Gi0/2 throughput 940Mbps loss 1.2% timestamp 2026-06-01 10:12.',
  'context_text': None,
  'expected_output_json': '{"schema": {"host": "string", "interface": "string", "throughput_mbps": "number", "loss_pct": "number", "timestamp": "date"}, '
                          '"expected": {"host": "uplink-fw-01", "interface": "Gi0/2", "throughput_mbps": 940, "loss_pct": 1.2, "timestamp": "2026-06-01"}, '
                          '"required_fields": ["host", "interface", "throughput_mbps"]}',
  'tags_json': '["network_monitoring"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'medical',
  'test_type_id': 'classification',
  'title': 'medical-Classificazione-prenotazione',
  'description': 'Classifica lo scenario di dominio',
  'input_text': 'Richiesta: vorrei prenotare una visita informativa non urgente presso ambulatorio vaccinale.',
  'context_text': None,
  'expected_output_json': '{"schema": {"label": "string"}, "expected": {"label": "prenotazione"}, "required_fields": ["label"], "allowed_labels": '
                          '["info_logistica", "prenotazione", "reclamo", "other"]}',
  'tags_json': '["medical"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'medical',
  'test_type_id': 'data_extraction',
  'title': 'medical-Estrazione-parametri',
  'description': 'Estrai dati strutturati di dominio',
  'input_text': 'Valori dichiarati: pressione 130/82, frequenza 76 bpm, temperatura 36.8C, saturazione 98%.',
  'context_text': None,
  'expected_output_json': '{"schema": {"pressione": "string", "frequenza": "integer", "temperatura": "number", "saturazione": "integer"}, "expected": '
                          '{"pressione": "130/82", "frequenza": 76, "temperatura": 36.8, "saturazione": 98}, "required_fields": ["pressione", "temperatura"]}',
  'tags_json': '["medical"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'medical',
  'test_type_id': 'rag_qa',
  'title': 'medical-RAG-info_assente',
  'description': 'Rispondi usando solo il contesto',
  'input_text': 'Il documento indica una diagnosi?',
  'context_text': 'Contesto informativo: sono presenti solo orari ambulatorio, recapiti e modalita di prenotazione. Non sono riportate diagnosi o terapie.',
  'expected_output_json': '{"answer_facts": [], "must_cite_context": true, "answer_absent": true}',
  'tags_json': '["medical"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'claims_management',
  'test_type_id': 'classification',
  'title': 'claims_management-Classificazione-furto',
  'description': 'Classifica lo scenario di dominio',
  'input_text': 'Reclamo: sottrazione borsa da autovettura parcheggiata, denuncia sporta il giorno successivo.',
  'context_text': None,
  'expected_output_json': '{"schema": {"label": "string"}, "expected": {"label": "furto"}, "required_fields": ["label"], "allowed_labels": ["danno_cose", '
                          '"furto", "smarrimento", "danno_persona", "other"]}',
  'tags_json': '["claims_management"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'claims_management',
  'test_type_id': 'data_extraction',
  'title': 'claims_management-Estrazione-furto',
  'description': 'Estrai dati strutturati di dominio',
  'input_text': 'Sinistro CL-2026-1020 cliente Neri Luca data 03/06/2026 importo stimato 900 EUR motivo furto bagaglio.',
  'context_text': None,
  'expected_output_json': '{"schema": {"sinistro": "string", "cliente": "string", "data": "date", "importo": "number", "motivo": "string"}, "expected": '
                          '{"sinistro": "CL-2026-1020", "cliente": "Neri Luca", "data": "2026-06-03", "importo": 900, "motivo": "furto bagaglio"}, '
                          '"required_fields": ["sinistro", "cliente", "importo"]}',
  'tags_json': '["claims_management"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'claims_management',
  'test_type_id': 'rag_qa',
  'title': 'claims_management-RAG-documenti',
  'description': 'Rispondi usando solo il contesto',
  'input_text': 'Quali documenti servono per aprire un reclamo furto?',
  'context_text': 'Procedura furto: allegare denuncia autorita, ricevuta bene sottratto, modulo reclamo firmato, coordinate rimborso.',
  'expected_output_json': '{"answer_facts": ["denuncia autorita", "ricevuta bene sottratto", "modulo firmato", "coordinate rimborso"], "must_cite_context": '
                          'true, "answer_absent": false}',
  'tags_json': '["claims_management"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'customer_support',
  'test_type_id': 'classification',
  'title': 'customer_support-Classificazione-pagamento',
  'description': 'Classifica lo scenario di dominio',
  'input_text': 'Cliente segnala doppio addebito carta per lo stesso ordine e chiede storno.',
  'context_text': None,
  'expected_output_json': '{"schema": {"label": "string"}, "expected": {"label": "problema_pagamento"}, "required_fields": ["label"], "allowed_labels": '
                          '["problema_spedizione", "reso", "difetto", "problema_pagamento", "other"]}',
  'tags_json': '["customer_support"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'customer_support',
  'test_type_id': 'data_extraction',
  'title': 'customer_support-Estrazione-pagamento',
  'description': 'Estrai dati strutturati di dominio',
  'input_text': 'Ticket PAY-2026-55 cliente demo@example.test ordine ORD-7788 doppio addebito 49.90 EUR data 02/06/2026.',
  'context_text': None,
  'expected_output_json': '{"schema": {"ticket": "string", "email": "string", "ordine": "string", "importo": "number", "data": "date"}, "expected": {"ticket": '
                          '"PAY-2026-55", "email": "demo@example.test", "ordine": "ORD-7788", "importo": 49.9, "data": "2026-06-02"}, "required_fields": '
                          '["ticket", "ordine", "importo"]}',
  'tags_json': '["customer_support"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'customer_support',
  'test_type_id': 'rag_qa',
  'title': 'customer_support-RAG-policy_pagamenti',
  'description': 'Rispondi usando solo il contesto',
  'input_text': 'Quanto tempo serve per storno doppio addebito?',
  'context_text': 'KB pagamenti: gli storni per doppio addebito vengono verificati entro 3 giorni lavorativi e riaccreditati entro 7 giorni lavorativi.',
  'expected_output_json': '{"answer_facts": ["verifica entro 3 giorni lavorativi", "riaccredito entro 7 giorni lavorativi"], "must_cite_context": true, '
                          '"answer_absent": false}',
  'tags_json': '["customer_support"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'online_booking',
  'test_type_id': 'classification',
  'title': 'online_booking-Classificazione-cancellazione',
  'description': 'Classifica lo scenario di dominio',
  'input_text': 'Cliente chiede annullamento prenotazione hotel per domani causa imprevisto.',
  'context_text': None,
  'expected_output_json': '{"schema": {"label": "string"}, "expected": {"label": "cancellazione"}, "required_fields": ["label"], "allowed_labels": '
                          '["prenotazione_ristorante", "prenotazione_hotel", "modifica", "cancellazione", "other"]}',
  'tags_json': '["online_booking"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'online_booking',
  'test_type_id': 'data_extraction',
  'title': 'online_booking-Estrazione-hotel',
  'description': 'Estrai dati strutturati di dominio',
  'input_text': 'Prenotazione BK-2026-90 hotel Aurora check-in 12/07/2026 check-out 14/07/2026 ospiti 2 camera doppia.',
  'context_text': None,
  'expected_output_json': '{"schema": {"booking_id": "string", "hotel": "string", "check_in": "date", "check_out": "date", "ospiti": "integer"}, "expected": '
                          '{"booking_id": "BK-2026-90", "hotel": "Aurora", "check_in": "2026-07-12", "check_out": "2026-07-14", "ospiti": 2}, '
                          '"required_fields": ["booking_id", "check_in", "ospiti"]}',
  'tags_json': '["online_booking"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'online_booking',
  'test_type_id': 'rag_qa',
  'title': 'online_booking-RAG-no_show',
  'description': 'Rispondi usando solo il contesto',
  'input_text': 'Cosa succede in caso di no-show?',
  'context_text': 'Policy no-show: mancata presentazione senza cancellazione comporta addebito 100 percento della prima notte.',
  'expected_output_json': '{"answer_facts": ["addebito 100 percento della prima notte"], "must_cite_context": true, "answer_absent": false}',
  'tags_json': '["online_booking"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'system_administration',
  'test_type_id': 'classification',
  'title': 'system_administration-Classificazione-disk',
  'description': 'Classifica lo scenario di dominio',
  'input_text': 'Server backup-02 segnala filesystem /backup al 99 percento e job backup fallito.',
  'context_text': None,
  'expected_output_json': '{"schema": {"label": "string"}, "expected": {"label": "disk_full"}, "required_fields": ["label"], "allowed_labels": ["memory_leak", '
                          '"disk_full", "network_down", "service_crash", "other"]}',
  'tags_json': '["system_administration"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'system_administration',
  'test_type_id': 'data_extraction',
  'title': 'system_administration-Estrazione-backup',
  'description': 'Estrai dati strutturati di dominio',
  'input_text': 'Host backup-02 servizio backupd errore DISK_FULL timestamp 2026-06-02T03:20 spazio 99 percento.',
  'context_text': None,
  'expected_output_json': '{"schema": {"host": "string", "servizio": "string", "errore": "string", "timestamp": "date", "utilizzo_pct": "number"}, "expected": '
                          '{"host": "backup-02", "servizio": "backupd", "errore": "DISK_FULL", "timestamp": "2026-06-02", "utilizzo_pct": 99}, '
                          '"required_fields": ["host", "errore", "utilizzo_pct"]}',
  'tags_json': '["system_administration"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'ecommerce',
  'test_type_id': 'classification',
  'title': 'ecommerce-Classificazione-spedizione',
  'description': 'Classifica lo scenario di dominio',
  'input_text': 'Ordine risulta consegnato ma cliente dichiara di non aver ricevuto il pacco.',
  'context_text': None,
  'expected_output_json': '{"schema": {"label": "string"}, "expected": {"label": "problema_spedizione"}, "required_fields": ["label"], "allowed_labels": '
                          '["prodotto_danneggiato", "prodotto_errato", "reso", "problema_spedizione", "other"]}',
  'tags_json': '["ecommerce"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'ecommerce',
  'test_type_id': 'data_extraction',
  'title': 'ecommerce-Estrazione-tracking',
  'description': 'Estrai dati strutturati di dominio',
  'input_text': 'Ordine ORD-9901 cliente Demo Cliente tracking TRK123 stato consegnato data 04/06/2026 importo 72.50 EUR.',
  'context_text': None,
  'expected_output_json': '{"schema": {"ordine": "string", "cliente": "string", "tracking": "string", "stato": "string", "data": "date", "importo": "number"}, '
                          '"expected": {"ordine": "ORD-9901", "cliente": "Demo Cliente", "tracking": "TRK123", "stato": "consegnato", "data": "2026-06-04", '
                          '"importo": 72.5}, "required_fields": ["ordine", "tracking", "stato"]}',
  'tags_json': '["ecommerce"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'ecommerce',
  'test_type_id': 'rag_qa',
  'title': 'ecommerce-RAG-policy_consegna',
  'description': 'Rispondi usando solo il contesto',
  'input_text': 'Cosa fare se tracking indica consegnato ma cliente nega ricezione?',
  'context_text': 'Policy consegna: aprire verifica corriere, richiedere conferma indirizzo, attendere esito entro 5 giorni lavorativi.',
  'expected_output_json': '{"answer_facts": ["aprire verifica corriere", "richiedere conferma indirizzo", "esito entro 5 giorni lavorativi"], '
                          '"must_cite_context": true, "answer_absent": false}',
  'tags_json': '["ecommerce"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'software_development',
  'test_type_id': 'data_extraction',
  'title': 'software_development-Estrazione-issue',
  'description': 'Estrai dati strutturati di dominio',
  'input_text': 'Issue DEV-2026-77 componente checkout severity high assegnato a team payments scadenza 2026-06-15.',
  'context_text': None,
  'expected_output_json': '{"schema": {"issue": "string", "component": "string", "severity": "string", "owner": "string", "deadline": "date"}, "expected": '
                          '{"issue": "DEV-2026-77", "component": "checkout", "severity": "high", "owner": "team payments", "deadline": "2026-06-15"}, '
                          '"required_fields": ["issue", "component", "severity"]}',
  'tags_json': '["software_development"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'software_development',
  'test_type_id': 'rag_qa',
  'title': 'software_development-RAG-branching',
  'description': 'Rispondi usando solo il contesto',
  'input_text': 'Quale branch usare per hotfix?',
  'context_text': 'Policy branching: bug critici produzione usano branch hotfix dalla release corrente; feature usano branch feature da develop.',
  'expected_output_json': '{"answer_facts": ["bug critici produzione usano branch hotfix", "hotfix dalla release corrente"], "must_cite_context": true, '
                          '"answer_absent": false}',
  'tags_json': '["software_development"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'document_processing',
  'test_type_id': 'data_extraction',
  'title': 'document_processing-Estrazione-ricevuta',
  'description': 'Estrai dati strutturati di dominio',
  'input_text': 'Ricevuta R-2026-77 data 05/06/2026 fornitore DemoLab totale 125.40 EUR causale analisi campione.',
  'context_text': None,
  'expected_output_json': '{"schema": {"numero": "string", "data": "date", "fornitore": "string", "totale": "number", "causale": "string"}, "expected": '
                          '{"numero": "R-2026-77", "data": "2026-06-05", "fornitore": "DemoLab", "totale": 125.4, "causale": "analisi campione"}, '
                          '"required_fields": ["numero", "data", "totale"]}',
  'tags_json': '["document_processing"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'document_processing',
  'test_type_id': 'classification',
  'title': 'document_processing-Classificazione-modulo',
  'description': 'Classifica lo scenario di dominio',
  'input_text': 'Documento contiene dati anagrafici, contatti, firma e consenso privacy per iscrizione servizio.',
  'context_text': None,
  'expected_output_json': '{"schema": {"label": "string"}, "expected": {"label": "modulo_iscrizione"}, "required_fields": ["label"], "allowed_labels": '
                          '["rimborso_spese", "fattura", "contratto", "certificato", "modulo_iscrizione", "other"]}',
  'tags_json': '["document_processing"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'document_processing',
  'test_type_id': 'rag_qa',
  'title': 'document_processing-RAG-campi_obbligatori',
  'description': 'Rispondi usando solo il contesto',
  'input_text': 'Quali campi sono obbligatori nel modulo?',
  'context_text': 'Guida modulo: nome, cognome, email e consenso privacy sono obbligatori; telefono e note sono opzionali.',
  'expected_output_json': '{"answer_facts": ["nome cognome email obbligatori", "consenso privacy obbligatorio", "telefono opzionale"], "must_cite_context": '
                          'true, "answer_absent": false}',
  'tags_json': '["document_processing"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'compliance',
  'test_type_id': 'data_extraction',
  'title': 'compliance-Estrazione-audit',
  'description': 'Estrai dati strutturati di dominio',
  'input_text': 'Audit AUD-2026-31 norma ISO27001 controllo A.5.15 owner sicurezza scadenza 2026-07-01 severita alta.',
  'context_text': None,
  'expected_output_json': '{"schema": {"audit": "string", "norma": "string", "controllo": "string", "owner": "string", "scadenza": "date", "severity": '
                          '"string"}, "expected": {"audit": "AUD-2026-31", "norma": "ISO27001", "controllo": "A.5.15", "owner": "sicurezza", "scadenza": '
                          '"2026-07-01", "severity": "alta"}, "required_fields": ["audit", "norma", "controllo", "scadenza"]}',
  'tags_json': '["compliance"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'compliance',
  'test_type_id': 'classification',
  'title': 'compliance-Classificazione-data_breach',
  'description': 'Classifica lo scenario di dominio',
  'input_text': 'Segnalazione: invio accidentale elenco clienti a destinatario esterno non autorizzato.',
  'context_text': None,
  'expected_output_json': '{"schema": {"label": "string"}, "expected": {"label": "data_breach"}, "required_fields": ["label"], "allowed_labels": '
                          '["registro_trattamenti", "data_breach", "mancata_notifica", "policy_obsoleta", "other"]}',
  'tags_json': '["compliance"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'academy',
  'test_type_id': 'classification',
  'title': 'Academy STEM - Classificazione problema scientifico',
  'description': 'Classifica il tipo di problema STEM',
  'input_text': 'Problema: Un oggetto cade da fermo da un altezza di 20 metri in assenza di attrito. Si chiede di stimare il tempo di caduta usando g = 9.81 '
                'm/s^2.',
  'context_text': None,
  'expected_output_json': '{"schema": {"label": "string"}, "expected": {"label": "fisica_cinematica"}, "required_fields": ["label"], "allowed_labels": '
                          '["matematica_algebra", "fisica_cinematica", "chimica_stechiometria", "biologia_cellulare", "statistica", "other"]}',
  'tags_json': '["academy", "stem", "classification"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'academy',
  'test_type_id': 'data_extraction',
  'title': 'Academy STEM - Estrazione dati esperimento fisica',
  'description': 'Estrai grandezze fisiche e parametri sperimentali',
  'input_text': 'Esperimento: pendolo semplice. Lunghezza filo L = 0.80 m. Massa bob = 120 g. Periodo medio misurato su 10 oscillazioni: 1.79 s. Incertezza '
                'sul periodo: ±0.03 s. Accelerazione gravitazionale attesa: 9.81 m/s^2.',
  'context_text': None,
  'expected_output_json': '{"schema": {"sistema": "string", "lunghezza_m": "number", "massa_g": "number", "periodo_s": "number", "incertezza_periodo_s": '
                          '"number", "g_atteso": "number"}, "expected": {"sistema": "pendolo semplice", "lunghezza_m": 0.8, "massa_g": 120, "periodo_s": 1.79, '
                          '"incertezza_periodo_s": 0.03, "g_atteso": 9.81}, "required_fields": ["sistema", "lunghezza_m", "periodo_s", '
                          '"incertezza_periodo_s"]}',
  'tags_json': '["academy", "stem", "physics", "extraction"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'academy',
  'test_type_id': 'summarization',
  'title': 'Academy STEM - Sintesi metodo scientifico',
  'description': 'Riassumi il contenuto scientifico mantenendo i concetti chiave',
  'input_text': 'Il metodo scientifico prevede osservazione del fenomeno, formulazione di una domanda, costruzione di un ipotesi verificabile, progettazione '
                'di un esperimento controllato, raccolta dei dati, analisi dei risultati e confronto con l ipotesi iniziale. Se i dati non supportano l '
                'ipotesi, questa deve essere modificata o rifiutata. La riproducibilita degli esperimenti e fondamentale per la validazione dei risultati.',
  'context_text': None,
  'expected_output_json': '{"format": "bullet_list", "max_words": 90, "required_points": ["osservazione del fenomeno", "ipotesi verificabile", "esperimento '
                          'controllato", "analisi dati", "riproducibilita"]}',
  'tags_json': '["academy", "stem", "summarization"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'academy',
  'test_type_id': 'rag_qa',
  'title': 'Academy STEM - RAG legge di Ohm',
  'description': 'Rispondi usando solo il contesto scientifico fornito',
  'input_text': 'Come si calcola la corrente in un circuito resistivo se sono noti tensione e resistenza?',
  'context_text': 'CONTESTO DIDATTICO: La legge di Ohm mette in relazione tensione, corrente e resistenza in un circuito elettrico. La formula e V = R * I. Di '
                  'conseguenza, se sono note tensione V e resistenza R, la corrente si calcola come I = V / R. La tensione si misura in volt, la resistenza in '
                  'ohm e la corrente in ampere.',
  'expected_output_json': '{"answer_facts": ["legge di Ohm I = V / R", "corrente in ampere", "tensione in volt", "resistenza in ohm"], "must_cite_context": '
                          'true, "answer_absent": false}',
  'tags_json': '["academy", "stem", "physics", "rag"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'academy',
  'test_type_id': 'data_extraction',
  'title': 'Academy STEM - Estrazione dati stechiometria',
  'description': 'Estrai dati chimici da un esercizio di stechiometria',
  'input_text': 'Esercizio: Reazione 2 H2 + O2 -> 2 H2O. Sono disponibili 4.0 mol di H2 e 1.5 mol di O2. Massa molare H2O = 18.015 g/mol. Determinare il '
                'reagente limitante e la quantita teorica massima di acqua prodotta.',
  'context_text': None,
  'expected_output_json': '{"schema": {"reazione": "string", "mol_h2": "number", "mol_o2": "number", "massa_molare_h2o": "number", "reagente_limitante": '
                          '"string", "mol_h2o_teoriche": "number"}, "expected": {"reazione": "2 H2 + O2 -> 2 H2O", "mol_h2": 4.0, "mol_o2": 1.5, '
                          '"massa_molare_h2o": 18.015, "reagente_limitante": "O2", "mol_h2o_teoriche": 3.0}, "required_fields": ["reazione", "mol_h2", '
                          '"mol_o2", "reagente_limitante", "mol_h2o_teoriche"]}',
  'tags_json': '["academy", "stem", "chemistry", "extraction"]',
  'difficulty': 'medium',
  'risk_level': 'low',
  'enabled': True},
 {'library_id': 'agent_development',
  'test_type_id': 'classification',
  'title': 'Agent-Dev - Classificazione pattern agente',
  'description': 'Classifica il tipo di architettura agente descritta',
  'input_text': 'Descrizione: Un sistema che riceve una richiesta utente, la scompone in sotto-task, per ogni sotto-task decide se chiamare un tool esterno '
                '(API, database, file system) o ragionare internamente, aggrega i risultati parziali e produce una risposta finale strutturata. Il sistema '
                'mantiene una memoria della conversazione e puo riformulare la richiesta se i tool restituiscono errori.',
  'context_text': None,
  'expected_output_json': '{"schema": {"label": "string"}, "expected": {"label": "react_agent_with_tools"}, "required_fields": ["label"], "allowed_labels": '
                          '["react_agent_with_tools", "chain_of_thought_simple", "router_agent", "multi_agent_orchestrator", "rag_agent", "other"]}',
  'tags_json': '["agents", "classification", "architecture"]',
  'difficulty': 'hard',
  'risk_level': 'medium',
  'enabled': True},
 {'library_id': 'agent_development',
  'test_type_id': 'code_analysis',
  'title': 'Agent-Dev - Analisi implementazione tool-calling',
  'description': 'Analizza il codice di un agente che chiama tool esterni',
  'input_text': 'def execute_agent_task(user_query, available_tools):\n'
                '    plan = llm_plan(user_query)\n'
                '    results = {}\n'
                '    for step in plan["steps"]:\n'
                '        tool_name = step["tool"]\n'
                '        if tool_name not in available_tools:\n'
                '            continue  # skip silently\n'
                '        tool = available_tools[tool_name]\n'
                '        try:\n'
                '            result = tool.run(step["params"])\n'
                '            results[step["id"]] = result\n'
                '        except:\n'
                '            results[step["id"]] = None\n'
                '    return llm_synthesize(user_query, plan, results)',
  'context_text': None,
  'expected_output_json': '{"expected_findings": [{"type": "bug", "severity": "high", "description_contains": "skip silently quando tool non trovato"}, '
                          '{"type": "best_practice", "severity": "medium", "description_contains": "except generico senza logging"}, {"type": "design", '
                          '"severity": "medium", "description_contains": "nessuna validazione parametri prima della chiamata"}], "expected_recommendations": '
                          '["Sollevare eccezione esplicita se tool richiesto non disponibile", "Loggare eccezioni con traceback per debug", "Validare params '
                          'contro tool schema prima di eseguire"]}',
  'tags_json': '["agents", "code_analysis", "tool_calling"]',
  'difficulty': 'hard',
  'risk_level': 'medium',
  'enabled': True},
 {'library_id': 'agent_development',
  'test_type_id': 'code_documentation',
  'title': 'Agent-Dev - Documentazione orchestratore multi-step',
  'description': 'Documenta la funzione di orchestrazione di un agente ReAct',
  'input_text': 'def react_loop(query: str, tools: dict, max_iterations: int = 10) -> dict:\n'
                '    context = {"query": query, "history": [], "observations": []}\n'
                '    for i in range(max_iterations):\n'
                '        thought_action = llm_reason(context)\n'
                '        if thought_action.get("final_answer"):\n'
                '            return thought_action["final_answer"]\n'
                '        action = thought_action.get("action")\n'
                '        if action and action["tool"] in tools:\n'
                '            result = tools[action["tool"]](**action.get("params", {}))\n'
                '            context["observations"].append({"action": action, "result": result})\n'
                '            context["history"].append(thought_action.get("thought", ""))\n'
                '        else:\n'
                '            context["observations"].append({"error": "unknown tool or missing action"})\n'
                '    return {"error": "max_iterations_reached", "partial_context": context}',
  'context_text': None,
  'expected_output_json': '{"must_include": ["parametri", "valore restituito", "eccezioni", "esempio di utilizzo"], "style": "docstring_google", "language": '
                          '"it"}',
  'tags_json': '["agents", "documentation", "react"]',
  'difficulty': 'hard',
  'risk_level': 'medium',
  'enabled': True},
 {'library_id': 'agent_development',
  'test_type_id': 'summarization',
  'title': 'Agent-Dev - Sintesi paper su agenti LLM',
  'description': 'Riassumi il paper tecnico sugli agenti basati su LLM',
  'input_text': 'PAPER: Gli agenti basati su Large Language Models rappresentano un paradigma emergente in cui il modello non si limita a generare testo ma '
                'agisce come nucleo decisionale di un sistema autonomo. L architettura ReAct (Reasoning + Acting) combina catene di pensiero con chiamate a '
                'strumenti esterni, permettendo al modello di raccogliere informazioni, eseguire azioni e adattare il piano in base ai risultati. I componenti '
                'chiave sono: un planner che scompone il task, un executor che gestisce tool calling, un memory module per contesto a lungo termine, e un '
                'evaluator che valida gli output intermedi. Le sfide principali includono: hallucination nei piani generati, errori a cascata da tool falliti, '
                'consumo eccessivo di token nelle iterazioni, e sicurezza delle azioni eseguite automaticamente.',
  'context_text': None,
  'expected_output_json': '{"format": "bullet_list", "max_words": 100, "required_points": ["architettura ReAct", "planner executor memory evaluator", '
                          '"hallucination nei piani", "errori a cascata da tool falliti", "sicurezza azioni automatiche"]}',
  'tags_json': '["agents", "summarization", "paper"]',
  'difficulty': 'hard',
  'risk_level': 'medium',
  'enabled': True},
 {'library_id': 'agent_development',
  'test_type_id': 'rag_qa',
  'title': 'Agent-Dev - RAG selezione tool appropriato',
  'description': 'Rispondi basandoti sulla documentazione dei tool disponibili',
  'input_text': 'Quale tool usare per recuperare il prezzo attuale di un prodotto dato il suo SKU?',
  'context_text': 'DOCUMENTAZIONE TOOL DISPONIBILI:\n'
                  '- search_catalog(keywords, category): cerca prodotti per parole chiave e categoria opzionale\n'
                  '- get_product_price(sku): restituisce prezzo corrente e valuta per lo SKU specificato\n'
                  '- check_inventory(sku, warehouse): verifica disponibilita in magazzino\n'
                  '- create_order(items): crea un ordine con gli articoli specificati\n'
                  '- lookup_customer(email): recupera dati cliente da email',
  'expected_output_json': '{"answer_facts": ["get_product_price", "richiede parametro sku", "restituisce prezzo e valuta"], "must_cite_context": true, '
                          '"answer_absent": false}',
  'tags_json': '["agents", "rag", "tool_selection"]',
  'difficulty': 'hard',
  'risk_level': 'medium',
  'enabled': True},
 {'library_id': 'agent_development',
  'test_type_id': 'data_extraction',
  'title': 'Agent-Dev - Chiamata funzione con parametri complessi',
  'description': 'Estrai il nome della funzione, i parametri e il tipo di ogni parametro dalla descrizione della tool call',
  'input_text': 'Tool call richiesta: get_weather(location="Milano", units="metric", forecast_days=5, include_hourly=true, lang="it")',
  'context_text': None,
  'expected_output_json': '{"schema": {"function_name": "string", "params": "string", "param_count": "integer"}, "expected": {"function_name": "get_weather", '
                          '"params": "location, units, forecast_days, include_hourly, lang", "param_count": 5}, "required_fields": ["function_name", "params", '
                          '"param_count"]}',
  'tags_json': '["agents", "function_calling", "hard"]',
  'difficulty': 'hard',
  'risk_level': 'high',
  'enabled': True},
 {'library_id': 'agent_development',
  'test_type_id': 'code_analysis',
  'title': 'Agent-Dev - Scrittura funzione da specifica formale',
  'description': 'Analizza se il codice implementa correttamente la specifica data',
  'input_text': 'SPECIFICA: La funzione deve calcolare la similarita coseno tra due vettori di uguale lunghezza, gestendo il caso di vettore nullo. Deve '
                'accettare due liste di float e restituire un float tra -1 e 1.\n'
                '\n'
                'CODICE:\n'
                'def cosine_similarity(v1, v2):\n'
                '    dot = sum(a * b for a, b in zip(v1, v2))\n'
                '    norm1 = sum(a * a for a in v1) ** 0.5\n'
                '    norm2 = sum(b * b for b in v2) ** 0.5\n'
                '    if norm1 == 0 or norm2 == 0:\n'
                '        return 0.0\n'
                '    return dot / (norm1 * norm2)',
  'context_text': None,
  'expected_output_json': '{"expected_findings": [{"type": "bug", "severity": "critical", "description_contains": "non verifica lunghezza uguale dei '
                          'vettori"}, {"type": "edge_case", "severity": "medium", "description_contains": "ritorna 0.0 per vettore nullo anziche sollevare '
                          'eccezione o None"}], "expected_recommendations": ["Aggiungere controllo len(v1) == len(v2) con ValueError", "Documentare '
                          'comportamento per vettori nulli"]}',
  'tags_json': '["agents", "spec_to_code", "hard"]',
  'difficulty': 'hard',
  'risk_level': 'high',
  'enabled': True},
 {'library_id': 'agent_development',
  'test_type_id': 'refactoring',
  'title': 'Agent-Dev - Da comando utente a codice funzionante',
  'description': 'Genera il codice che soddisfa il comando utente rispettando i vincoli',
  'input_text': 'COMANDO UTENTE: Voglio una funzione che legga un file CSV di ordini (colonne: order_id, customer, amount, status) e restituisca un dizionario '
                'con: numero ordini per stato, totale amount per stato, cliente con spesa maggiore.\n'
                '\n'
                'VINCOLI: Usare solo standard library Python (csv, collections). Gestire file inesistente con eccezione personalizzata. Gestire righe vuote o '
                'malformate.',
  'context_text': None,
  'expected_output_json': '{"must_preserve_behavior": false, "target": "implementare funzione da specifica utente", "constraints": ["solo standard library", '
                          '"gestire file mancante", "gestire righe malformate"], "tests_should_pass": true}',
  'tags_json': '["agents", "user_command_to_code", "hard"]',
  'difficulty': 'hard',
  'risk_level': 'high',
  'enabled': True},
 {'library_id': 'agent_development',
  'test_type_id': 'code_analysis',
  'title': 'Agent-Dev - Loop scrittura e verifica codice',
  'description': 'Analizza il codice prodotto da un agente dopo 3 iterazioni di fix, trovando i bug residui',
  'input_text': 'ITERAZIONE 1 (bug iniziali):\n'
                'def merge_intervals(intervals):\n'
                '    if not intervals: return []\n'
                '    intervals.sort()\n'
                '    merged = [intervals[0]]\n'
                '    for current in intervals[1:]:\n'
                '        prev = merged[-1]\n'
                '        if current[0] <= prev[1]:\n'
                '            prev[1] = max(prev[1], current[1])\n'
                '        else:\n'
                '            merged.append(current)\n'
                '    return merged\n'
                '\n'
                'ITERAZIONE 2 (fix 1): aggiunto controllo input non liste\n'
                'ITERAZIONE 3 (fix 2): aggiunta validazione tuple (a,b) con a<=b\n'
                '\n'
                'CODICE FINALE:\n'
                'def merge_intervals(intervals):\n'
                '    if not isinstance(intervals, list): raise TypeError("lista richiesta")\n'
                '    if not intervals: return []\n'
                '    valid = []\n'
                '    for iv in intervals:\n'
                '        if not isinstance(iv, (list, tuple)) or len(iv) != 2: continue\n'
                '        a, b = iv\n'
                '        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)): continue\n'
                '        if a > b: a, b = b, a\n'
                '        valid.append([a, b])\n'
                '    if not valid: return []\n'
                '    valid.sort()\n'
                '    merged = [valid[0]]\n'
                '    for current in valid[1:]:\n'
                '        prev = merged[-1]\n'
                '        if current[0] <= prev[1]:\n'
                '            prev[1] = max(prev[1], current[1])\n'
                '        else:\n'
                '            merged.append(current)\n'
                '    return merged',
  'context_text': None,
  'expected_output_json': '{"expected_findings": [{"type": "edge_case", "severity": "medium", "description_contains": "intervalli sovrapposti parzialmente non '
                          'gestiti quando current[1] < prev[1]"}, {"type": "best_practice", "severity": "low", "description_contains": "nessun docstring o '
                          'type hint"}], "expected_recommendations": ["Aggiungere type hints per input e output", "Documentare comportamento con docstring '
                          'Google-style"]}',
  'tags_json': '["agents", "code_verify_loop", "hard"]',
  'difficulty': 'hard',
  'risk_level': 'high',
  'enabled': True},
 {'library_id': 'agent_development',
  'test_type_id': 'data_extraction',
  'title': 'Agent-Dev - Orchestrazione multi-tool con fallback',
  'description': 'Estrai la sequenza di tool call e la logica di fallback dal piano di esecuzione',
  'input_text': 'PIANO AGENTE:\n'
                'Step 1: search_product(sku="SH2-34-BK")\n'
                '  - Se success: passa a Step 3 con product_id dal risultato\n'
                '  - Se errore "not_found": chiama search_catalog(keywords="SmartHub v2", category="elettronica")\n'
                'Step 2: check_inventory(product_id=result.product_id, warehouse="MIL-01")\n'
                '  - Se stock > 0: calcola available = stock - reserved\n'
                '  - Se stock == 0: chiama find_alternative(product_id) e restituisci suggerimenti\n'
                'Step 3: get_price(product_id=result.product_id, currency="EUR")\n'
                'Step 4: format_response(product=result, stock=available, price=result.price)',
  'context_text': None,
  'expected_output_json': '{"schema": {"tool_sequence": "string", "fallback_triggers": "string", "total_steps": "integer", "has_error_handling": "string"}, '
                          '"expected": {"tool_sequence": "search_product -> search_catalog | check_inventory -> find_alternative | get_price -> '
                          'format_response", "fallback_triggers": "not_found su search_product, stock==0 su check_inventory", "total_steps": 4, '
                          '"has_error_handling": "si"}, "required_fields": ["tool_sequence", "fallback_triggers", "total_steps"]}',
  'tags_json': '["agents", "function_calling", "orchestration", "hard"]',
  'difficulty': 'hard',
  'risk_level': 'high',
  'enabled': True}]
def seed_libraries(db):
    from ..models import TestLibrary
    added = 0
    for lib_id, label, desc, domain, tags in LIBRARIES:
        existing = db.query(TestLibrary).filter(TestLibrary.id == lib_id).first()
        if not existing:
            db.add(TestLibrary(id=lib_id, label=label, description=desc, domain=domain, tags_json=json.dumps(tags), enabled=True))
            added += 1
        elif lib_id == "academy":
            existing.label = label; existing.description = desc; existing.domain = domain; existing.tags_json = json.dumps(tags)
    if added: db.commit()
    return added

def seed_library_test_cases(db):
    from ..models import TestCase
    added = 0
    for tc_data in SEED_LIBRARY_TEST_CASES:
        dup = db.query(TestCase).filter(TestCase.title == tc_data["title"]).first()
        if dup:
            if not dup.library_id: dup.library_id = tc_data.get("library_id")
            continue
        tc = TestCase(test_type_id=tc_data["test_type_id"], library_id=tc_data.get("library_id"), title=tc_data["title"], description=tc_data.get("description"), input_text=tc_data.get("input_text"), context_text=tc_data.get("context_text"), expected_output_json=tc_data.get("expected_output_json"), expected_text=tc_data.get("expected_text"), tags_json=tc_data.get("tags_json"), difficulty=tc_data.get("difficulty","medium"), risk_level=tc_data.get("risk_level","low"), enabled=True)
        db.add(tc); added += 1
    if added: db.commit()
    return added

def migrate_legacy_tests_to_general_library(db):
    from ..models import TestCase, TestLibrary
    orphans = db.query(TestCase).filter(TestCase.library_id == None).all()
    if not orphans: return 0
    gen = db.query(TestLibrary).filter(TestLibrary.id == "general").first()
    if not gen:
        gen = TestLibrary(id="general", label="Libreria Generale", description="Test migrati senza libreria", domain="general", enabled=True)
        db.add(gen); db.commit()
    count = 0
    for tc in orphans: tc.library_id = "general"; count += 1
    db.commit()
    return count

def migrate_academy_library_to_stem(db):
    from ..models import TestCase
    old = {"Academy-Richiesta","Academy-Corso","Academy-Materiale","Academy-Regolamento","Academy-Feedback"}
    updated = 0
    for tc in db.query(TestCase).filter(TestCase.library_id == "academy", TestCase.title.in_(old)).all():
        tc.enabled = False; tc.tags_json = json.dumps(["academy","deprecated_admin_seed"]); updated += 1
    if updated: db.commit()
    return updated
