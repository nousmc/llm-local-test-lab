import json
import csv
import io
import re
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session

from ..models import TestRun, TestResult, ValidationResult, MetricResult, Report, ConfiguredModel


def generate_report(db: Session, test_run_id: int) -> Report | None:
    run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not run:
        return None

    results = db.query(TestResult).filter(TestResult.test_run_id == test_run_id).all()

    existing = db.query(Report).filter(Report.test_run_id == test_run_id).first()
    if existing:
        db.delete(existing)
        db.commit()

    model_ids_raw = json.loads(run.selected_model_ids_json or "[]")
    test_case_ids_raw = json.loads(run.selected_test_case_ids_json or "[]")

    models_tested = db.query(ConfiguredModel).filter(ConfiguredModel.id.in_(model_ids_raw)).all()

    total = len(results)
    completed = sum(1 for r in results if r.status == "completed")
    failed = sum(1 for r in results if r.status in ("failed", "timeout"))
    passed_count = 0
    scores = []
    latencies = []
    errors_by_type = {}
    model_scores = {}
    model_passed = {}
    test_type_scores = {}

    for r in results:
        if r.error_type:
            errors_by_type[r.error_type] = errors_by_type.get(r.error_type, 0) + 1

        for m in (r.metrics or []):
            if m.metric_name == "final_score":
                scores.append(m.metric_value)
                pass_threshold = 0.80
                if m.metric_value >= pass_threshold:
                    passed_count += 1

                key = r.model_id
                if key not in model_scores:
                    model_scores[key] = []
                    model_passed[key] = 0
                model_scores[key].append(m.metric_value)
                if m.metric_value >= pass_threshold:
                    model_passed[key] += 1

                tc = r.test_case
                if tc:
                    tk = tc.test_type_id
                    if tk not in test_type_scores:
                        test_type_scores[tk] = []
                    test_type_scores[tk].append(m.metric_value)

        if r.latency_ms:
            latencies.append(r.latency_ms)

    avg_score = round(sum(scores) / len(scores), 4) if scores else 0
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0
    pass_rate = round(passed_count / total * 100, 1) if total else 0
    error_rate = round(failed / total * 100, 1) if total else 0

    model_stats = {}
    for mid, sc_list in model_scores.items():
        m = next((x for x in models_tested if x.id == mid), None)
        model_stats[mid] = {
            "label": m.label if m else mid,
            "avg_score": round(sum(sc_list) / len(sc_list), 4),
            "pass_count": model_passed.get(mid, 0),
            "total": len(sc_list),
            "pass_rate": round(model_passed.get(mid, 0) / len(sc_list) * 100, 1) if sc_list else 0,
        }

    best_model_id = max(model_stats, key=lambda k: model_stats[k]["avg_score"]) if model_stats else None
    best_model = model_stats[best_model_id]["label"] if best_model_id else None

    summary = f"Test Run: {run.name}\n"
    summary += f"Total tests: {total} | Passed: {passed_count} | Failed: {failed}\n"
    summary += f"Avg Score: {avg_score} | Pass Rate: {pass_rate}% | Avg Latency: {avg_latency}ms\n"

    failures = []
    for r in results:
        if r.status in ("failed", "timeout"):
            failures.append({
                "test_case_id": r.test_case_id,
                "model_id": r.model_id,
                "error": r.error_message,
                "error_type": r.error_type,
            })

    chart_data = _build_chart_data(model_stats, test_type_scores, errors_by_type, latencies, scores)

    report = Report(
        test_run_id=test_run_id,
        title=f"Report: {run.name}",
        summary_text=summary,
        findings_json=json.dumps({
            "total": total,
            "completed": completed,
            "failed": failed,
            "passed_count": passed_count,
            "avg_score": avg_score,
            "pass_rate": pass_rate,
            "error_rate": error_rate,
            "avg_latency": avg_latency,
            "best_model": best_model,
            "model_stats": model_stats,
            "errors_by_type": errors_by_type,
            "failures": failures,
        }),
        chart_payload_json=json.dumps(chart_data),
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return report


def _build_chart_data(model_stats, test_type_scores, errors_by_type, latencies, scores):
    return {
        "model_scores": {
            "labels": list(model_stats.keys()),
            "data": [model_stats[k]["avg_score"] for k in model_stats],
            "pass_rates": [model_stats[k]["pass_rate"] for k in model_stats],
        },
        "test_type_scores": {
            "labels": list(test_type_scores.keys()),
            "data": [round(sum(v) / len(v), 4) for v in test_type_scores.values()],
        },
        "errors": {
            "labels": list(errors_by_type.keys()),
            "data": list(errors_by_type.values()),
        },
        "latency_distribution": latencies,
        "score_distribution": scores,
    }


def generate_csv(results: list) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "run_id", "test_case_id", "test_type", "model_id", "provider",
        "score", "passed", "latency_ms", "tokens_per_second",
        "prompt_tokens", "completion_tokens", "total_tokens", "error_message"
    ])
    for r in results:
        score = 0
        passed = False
        for m in (r.metrics or []):
            if m.metric_name == "final_score":
                score = m.metric_value
                passed = score >= 0.80
                break
        tc = r.test_case
        writer.writerow([
            r.test_run_id,
            r.test_case_id,
            tc.test_type_id if tc else "",
            r.model_id,
            r.provider,
            score,
            passed,
            r.latency_ms or 0,
            r.tokens_per_second or 0,
            r.prompt_tokens or 0,
            r.completion_tokens or 0,
            r.total_tokens or 0,
            r.error_message or "",
        ])
    return output.getvalue()


async def generate_executive_report(db: Session, test_run_id: int) -> str | None:
    run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not run:
        return None

    results = db.query(TestResult).filter(TestResult.test_run_id == test_run_id).all()
    if not results:
        return None

    benchmark_cfg = json.loads(run.benchmark_config_json or "{}")
    is_benchmark = benchmark_cfg.get("enabled", False)

    scores = []
    model_stats = {}
    errors = []
    for r in results:
        model_key = r.model_id
        if model_key not in model_stats:
            model_stats[model_key] = {"total": 0, "scores": [], "failures": 0, "latencies": []}

        model_stats[model_key]["total"] += 1
        if r.latency_ms:
            model_stats[model_key]["latencies"].append(r.latency_ms)

        for m in (r.metrics or []):
            if m.metric_name == "final_score":
                scores.append(m.metric_value)
                model_stats[model_key]["scores"].append(m.metric_value)
                break

        if r.status in ("failed", "timeout"):
            model_stats[model_key]["failures"] += 1
            errors.append(f"{r.model_id} su {r.test_case.test_type_id if r.test_case else '?'}: {r.error_message or 'errore sconosciuto'}")

    model_summary = ""
    for mid, ms in model_stats.items():
        avg = round(sum(ms["scores"]) / len(ms["scores"]), 4) if ms["scores"] else 0
        avg_lat = round(sum(ms["latencies"]) / len(ms["latencies"]), 2) if ms["latencies"] else 0
        model_summary += f"- {mid}: score medio {avg}, {ms['total']} test, {ms['failures']} falliti, latenza media {avg_lat}ms\n"

    benchmark_section = ""
    if is_benchmark:
        try:
            from .benchmark_stats import compute_benchmark_stats
            bstats = compute_benchmark_stats(db, test_run_id)
            if bstats.get("has_benchmark_data"):
                repeat_count = benchmark_cfg.get("repeat_count", 3)
                benchmark_section = f"\nModalità benchmark: {repeat_count} ripetizioni per test a 3 temperature diverse.\n"
                benchmark_section += "Classifica (score medio per tipo con temperatura ottimale):\n"
                for entry in bstats.get("ranking", [])[:10]:
                    benchmark_section += f"  #{entry['rank']} {entry['model_label']} — {entry['mean_score']}\n"
                    for ttype, opt in entry.get("per_type_optimal", {}).items():
                        benchmark_section += f"      {ttype}: T={opt['temperature']} score={opt['mean_score']} std={opt['std_dev']}\n"
        except Exception:
            pass

    prompt = f"""Sei un analista tecnico che deve scrivere un executive report sui risultati di un benchmark LLM.

Dati della run:
Nome: {run.name}
Totale test eseguiti: {len(results)}
Score medio globale: {round(sum(scores)/len(scores), 4) if scores else 'N/D'}

Risultati per modello:
{model_summary}
{benchmark_section}
Errori riscontrati:
{chr(10).join(errors[:10]) if errors else 'Nessun errore significativo'}

Scrivi un executive report in italiano (max 500 parole).

Formato obbligatorio:
- Restituisci SOLO testo semplice.
- Non restituire JSON.
- Non usare blocchi markdown con triple backtick.
- Non usare tabelle markdown.
- Usa esattamente queste sezioni, una per riga:

Sintesi esecutiva
<2-3 frasi sui risultati complessivi>

Confronto tra modelli
<chi ha performato meglio/peggio e perche, includi analisi delle temperature ottimali se presenti>

Analisi errori
<pattern ricorrenti e criticita>

Raccomandazioni operative
<quale modello usare per quale scopo e a quale temperatura>

Sii concreto e basati solo sui dati forniti. Non inventare informazioni."""

    try:
        from .validator import _get_validator_settings
        from .provider_router import get_provider_client

        val_cfg = _get_validator_settings()
        if not val_cfg.get("enabled"):
            return _build_simple_executive_report(results, model_stats, scores, errors, is_benchmark, db, test_run_id)

        client = get_provider_client(val_cfg["provider"])
        resp = await client.chat(
            model=val_cfg["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=val_cfg.get("temperature", 0.0),
            max_tokens=val_cfg.get("max_tokens", 2048),
        )
        text = resp.get("text", "")
        if resp.get("error"):
            fallback = val_cfg.get("fallback_provider")
            fallback_model = val_cfg.get("fallback_model")
            if fallback and fallback_model:
                fb = get_provider_client(fallback)
                resp2 = await fb.chat(
                    model=fallback_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=2048,
                )
                text = resp2.get("text", "")

        return _normalize_executive_report(text) if text else _build_simple_executive_report(results, model_stats, scores, errors, is_benchmark, db, test_run_id)

    except Exception:
        return _build_simple_executive_report(results, model_stats, scores, errors, is_benchmark, db, test_run_id)


def _normalize_executive_report(text: str) -> str:
    if not text:
        return ""

    cleaned = text.strip()

    # Remove markdown code fences if the model wrapped the answer.
    cleaned = re.sub(r"^```(?:json|markdown|md|text)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    # Some models return JSON despite the prompt. Extract the useful text.
    parsed = None
    if cleaned.startswith("{"):
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            parsed = None
    if isinstance(parsed, dict):
        for key in ("executive_report", "report", "summary", "text", "content"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                cleaned = value.strip()
                break
        else:
            sections = []
            for key in ("sintesi_esecutiva", "sintesi", "confronto_modelli", "analisi_errori", "raccomandazioni"):
                value = parsed.get(key)
                if value:
                    title = key.replace("_", " ").title()
                    if isinstance(value, list):
                        body = "\n".join(f"- {item}" for item in value)
                    else:
                        body = str(value)
                    sections.append(f"{title}\n{body}")
            cleaned = "\n\n".join(sections) if sections else json.dumps(parsed, ensure_ascii=False, indent=2)

    # Convert literal escaped newlines/tabs often produced by JSON-ish text.
    cleaned = cleaned.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "  ")

    # Remove markdown emphasis that may create odd rendering/parsing in HTML exports.
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.*?)__", r"\1", cleaned)
    cleaned = re.sub(r"^#+\s*", "", cleaned, flags=re.MULTILINE)

    # Normalize known section headings.
    replacements = {
        "1. Sintesi esecutiva": "Sintesi esecutiva",
        "2. Confronto tra modelli": "Confronto tra modelli",
        "3. Analisi errori": "Analisi errori",
        "4. Raccomandazioni operative": "Raccomandazioni operative",
    }
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)

    # Compact excessive blank lines while preserving paragraph separation.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _build_simple_executive_report(results, model_stats, scores, errors, is_benchmark=False, db=None, test_run_id=None):
    total = len(results)
    avg_score = round(sum(scores) / len(scores), 4) if scores else 0
    passed = sum(1 for s in scores if s >= 0.80)
    failed = total - passed
    best_model = max(model_stats, key=lambda k: (sum(model_stats[k]["scores"]) / max(1, len(model_stats[k]["scores"])))) if model_stats else "N/D"
    error_count = len(errors)

    report = f"""EXECUTIVE REPORT AUTOMATICO

Sintesi esecutiva: Sono stati eseguiti {total} test su {len(model_stats)} modelli. Score medio globale: {avg_score}. {passed} test superati (>=0.80), {failed} falliti."""

    if is_benchmark and db and test_run_id:
        try:
            from .benchmark_stats import compute_benchmark_stats
            bstats = compute_benchmark_stats(db, test_run_id)
            if bstats.get("ranking"):
                best = bstats["ranking"][0]
                report += f"\n\nClassifica benchmark (temperatura ottimale per tipologia):\n"
                for entry in bstats["ranking"][:5]:
                    report += f"- #{entry['rank']} {entry['model_label']}: {entry['mean_score']}\n"
                report += f"\nMiglior modello: {best['model_label']} con score {best['mean_score']}\nTemperature ottimali per tipologia:\n"
                for ttype, opt in best.get("per_type_optimal", {}).items():
                    report += f"  {ttype}: T={opt['temperature']} (score {opt['mean_score']})\n"
        except Exception:
            pass
    else:
        report += f"\n\nMiglior modello: {best_model}."

    report += f"\n\nAnalisi errori: {error_count} errori riscontrati. I problemi piu comuni includono errori di connessione ai provider, timeout, e fallimenti nella validazione del formato JSON atteso."

    report += f"\n\nRaccomandazioni: Selezionare il modello con score medio piu alto per i task critici. Per task che richiedono output JSON strutturato, preferire modelli con supports_json=true. Verificare la raggiungibilita dei provider prima di eseguire le run."
    return report
