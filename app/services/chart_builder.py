import json
from ..models import TestRun, TestResult, ConfiguredModel
from sqlalchemy.orm import Session


def build_dashboard_charts(db: Session) -> dict:
    runs = db.query(TestRun).order_by(TestRun.created_at.desc()).limit(10).all()

    results = []
    for run in runs:
        results.extend(db.query(TestResult).filter(TestResult.test_run_id == run.id).all())

    model_scores = {}
    model_pass = {}
    model_total = {}
    model_latencies = {}
    model_json_validity = {}
    provider_errors = {}

    for r in results:
        key = r.model_id
        if key not in model_scores:
            model_scores[key] = []
            model_pass[key] = 0
            model_total[key] = 0
            model_latencies[key] = []
            model_json_validity[key] = {"valid": 0, "total": 0}

        model_total[key] += 1

        if r.latency_ms:
            model_latencies[key].append(r.latency_ms)

        if r.response_json:
            model_json_validity[key]["valid"] += 1
        model_json_validity[key]["total"] += 1

        has_score = False
        for m in (r.metrics or []):
            if m.metric_name == "final_score":
                model_scores[key].append(m.metric_value)
                if m.metric_value >= 0.80:
                    model_pass[key] += 1
                has_score = True

        if r.error_type:
            if r.provider not in provider_errors:
                provider_errors[r.provider] = {}
            provider_errors[r.provider][r.error_type] = provider_errors[r.provider].get(r.error_type, 0) + 1

    models = db.query(ConfiguredModel).all()
    model_labels = {m.id: m.label for m in models}

    return {
        "model_scores": {
            "labels": [model_labels.get(k, k) for k in model_scores],
            "data": [round(sum(v) / len(v), 4) if v else 0 for v in model_scores.values()],
        },
        "model_pass_rate": {
            "labels": [model_labels.get(k, k) for k in model_pass],
            "data": [round(model_pass[k] / model_total[k] * 100, 1) if model_total[k] else 0 for k in model_pass],
        },
        "model_latency": {
            "labels": [model_labels.get(k, k) for k in model_latencies],
            "data": [round(sum(v) / len(v), 2) if v else 0 for v in model_latencies.values()],
        },
        "model_json_rate": {
            "labels": [model_labels.get(k, k) for k in model_json_validity],
            "data": [
                round(model_json_validity[k]["valid"] / model_json_validity[k]["total"] * 100, 1)
                if model_json_validity[k]["total"] else 0
                for k in model_json_validity
            ],
        },
        "provider_errors": provider_errors,
    }


def build_run_charts(db: Session, test_run_id: int) -> dict:
    results = db.query(TestResult).filter(TestResult.test_run_id == test_run_id).all()
    run = db.query(TestRun).filter(TestRun.id == test_run_id).first()

    if not run or not results:
        return {}

    model_scores = {}
    model_pass = {}
    model_total = {}
    model_latencies = {}
    type_scores = {}
    type_total = {}
    type_model_scores = {}

    for r in results:
        key = r.model_id
        if key not in model_scores:
            model_scores[key] = []
            model_pass[key] = 0
            model_total[key] = 0
            model_latencies[key] = []

        model_total[key] += 1

        if r.latency_ms:
            model_latencies[key].append(r.latency_ms)

        has_score = False
        for m in (r.metrics or []):
            if m.metric_name == "final_score":
                model_scores[key].append(m.metric_value)
                if m.metric_value >= 0.80:
                    model_pass[key] += 1
                has_score = True

        tc = r.test_case
        if tc:
            tk = tc.test_type_id
            if tk not in type_scores:
                type_scores[tk] = []
                type_total[tk] = 0
            if has_score and model_scores[key]:
                type_scores[tk].append(model_scores[key][-1])
            type_total[tk] += 1

            # Per-model per test-type
            if tk not in type_model_scores:
                type_model_scores[tk] = {}
            if key not in type_model_scores[tk]:
                type_model_scores[tk][key] = []
            if has_score and model_scores[key]:
                type_model_scores[tk][key].append(model_scores[key][-1])

    models = db.query(ConfiguredModel).all()
    model_labels = {m.id: m.label for m in models}

    # --- Per-library aggregations ---
    lib_scores = {}
    lib_pass = {}
    lib_total = {}
    lib_model_scores = {}
    for r in results:
        tc = r.test_case
        lid = tc.library_id if tc and tc.library_id else "general"
        if lid not in lib_scores:
            lib_scores[lid] = []
            lib_pass[lid] = 0
            lib_total[lid] = 0
            lib_model_scores[lid] = {}
        lib_total[lid] += 1
        for m in (r.metrics or []):
            if m.metric_name == "final_score":
                lib_scores[lid].append(m.metric_value)
                if m.metric_value >= 0.80:
                    lib_pass[lid] += 1
                mid = r.model_id
                if mid not in lib_model_scores[lid]:
                    lib_model_scores[lid][mid] = []
                lib_model_scores[lid][mid].append(m.metric_value)

    from ..models import TestLibrary
    lib_labels_map = {lib.id: lib.label for lib in db.query(TestLibrary).all()}

    lib_labels = sorted(lib_scores.keys())
    lib_avg = [round(sum(lib_scores[l]) / len(lib_scores[l]), 4) if lib_scores[l] else 0 for l in lib_labels]
    lib_pass_rates = [round(lib_pass[l] / lib_total[l] * 100, 1) if lib_total[l] else 0 for l in lib_labels]
    lib_display_labels = [lib_labels_map.get(l, l) for l in lib_labels]

    colors = [
        'rgba(34,139,34,0.7)', 'rgba(54,162,235,0.7)', 'rgba(255,159,64,0.7)',
        'rgba(153,102,255,0.7)', 'rgba(255,99,132,0.7)', 'rgba(75,192,192,0.7)',
    ]

    lib_model_datasets = []
    all_model_ids = sorted(model_scores.keys())
    for mi, mid in enumerate(all_model_ids):
        data = []
        for l in lib_labels:
            vals = lib_model_scores.get(l, {}).get(mid, [])
            data.append(round(sum(vals) / len(vals), 4) if vals else 0)
        lib_model_datasets.append({
            "label": model_labels.get(mid, mid),
            "data": data,
            "backgroundColor": colors[mi % len(colors)],
        })

    # Build per-model per-type dataset for grouped bar chart
    test_type_list = sorted(type_model_scores.keys())
    model_ids_in_run = sorted(model_scores.keys())
    type_model_datasets = []
    for i, mid in enumerate(model_ids_in_run):
        data = []
        for tt in test_type_list:
            vals = type_model_scores.get(tt, {}).get(mid, [])
            data.append(round(sum(vals) / len(vals), 4) if vals else 0)
        type_model_datasets.append({
            "label": model_labels.get(mid, mid),
            "data": data,
            "backgroundColor": colors[i % len(colors)],
        })

    model_weighted_scores = {}
    for k in model_scores:
        avg = round(sum(model_scores[k]) / len(model_scores[k]), 4) if model_scores[k] else 0
        pr = round(model_pass.get(k, 0) / model_total.get(k, 1) * 100, 1) if model_total.get(k, 0) else 0
        model_weighted_scores[k] = round(avg * (pr / 100.0), 4)

    return {
        "model_scores": {
            "labels": [model_labels.get(k, k) for k in model_scores],
            "data": [round(sum(v) / len(v), 4) if v else 0 for v in model_scores.values()],
        },
        "model_pass_rate": {
            "labels": [model_labels.get(k, k) for k in model_pass],
            "data": [round(model_pass[k] / model_total[k] * 100, 1) if model_total[k] else 0 for k in model_pass],
        },
        "model_latency": {
            "labels": [model_labels.get(k, k) for k in model_latencies],
            "data": [round(sum(v) / len(v), 2) if v else 0 for v in model_latencies.values()],
        },
        "test_type_scores": {
            "labels": list(type_scores.keys()),
            "data": [round(sum(v) / len(v), 4) if v else 0 for v in type_scores.values()],
        },
        "test_type_model_labels": test_type_list,
        "test_type_model_datasets": type_model_datasets,
        "model_ids": model_ids_in_run,
        "library_scores": {
            "labels": lib_display_labels,
            "data": lib_avg,
        },
        "library_pass_rate": {
            "labels": lib_display_labels,
            "data": lib_pass_rates,
        },
        "library_model_labels": lib_display_labels,
        "library_model_datasets": lib_model_datasets,
        "model_weighted_scores": {
            "labels": [model_labels.get(k, k) for k in model_weighted_scores],
            "data": [model_weighted_scores[k] for k in model_weighted_scores],
        },
    }
