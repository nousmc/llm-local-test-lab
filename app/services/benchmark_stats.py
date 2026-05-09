from collections import defaultdict
from sqlalchemy.orm import Session

from ..models import TestResult, ConfiguredModel


def _safe_round(value, ndigits=4):
    return round(value, ndigits)


def compute_benchmark_stats(db: Session, test_run_id: int) -> dict:
    results = db.query(TestResult).filter(
        TestResult.test_run_id == test_run_id,
        TestResult.temperature_used.isnot(None),
        TestResult.repetition_index.isnot(None),
    ).all()

    if not results:
        return {"model_stats": {}, "ranking": [], "has_benchmark_data": False}

    # model_type_temp_scores[mid][ttype][temp] = [scores...]
    model_type_temp = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    model_temp_all = defaultdict(lambda: defaultdict(list))

    for r in results:
        mid = r.model_id
        temp = r.temperature_used
        ttype = r.test_case.test_type_id if r.test_case else "unknown"

        score = 0.0
        for m in (r.metrics or []):
            if m.metric_name == "final_score":
                score = m.metric_value
                break

        model_type_temp[mid][ttype][temp].append(score)
        model_temp_all[mid][temp].append(score)

    models = db.query(ConfiguredModel).all()
    model_labels = {m.id: m.label for m in models}

    # Compute per-type optimal temperature for each model
    # model_per_type_opt[mid][ttype] = {temperature, mean, std_dev}
    model_per_type_opt = defaultdict(dict)
    for mid, types in model_type_temp.items():
        for ttype, temps in types.items():
            best_temp = None
            best_mean = -1
            for temp, scores in temps.items():
                m = sum(scores) / len(scores)
                if m > best_mean or (m == best_mean and (best_temp is None or temp < best_temp)):
                    best_mean = m
                    best_temp = temp
            if best_temp is not None:
                n = len(temps[best_temp])
                variance = sum((s - best_mean) ** 2 for s in temps[best_temp]) / n if n > 1 else 0
                model_per_type_opt[mid][ttype] = {
                    "temperature": best_temp,
                    "mean_score": _safe_round(best_mean),
                    "std_dev": _safe_round(variance ** 0.5),
                    "count": n,
                }

    # Compute ranking: model score = mean of its per-type optimal means
    model_scores = {}
    for mid, type_opts in model_per_type_opt.items():
        means = [opt["mean_score"] for opt in type_opts.values()]
        if means:
            model_scores[mid] = sum(means) / len(means)
        else:
            model_scores[mid] = 0.0

    ranking = sorted(model_scores.items(), key=lambda x: -x[1])
    ranking_list = []
    for rank_idx, (mid, score) in enumerate(ranking, 1):
        type_opts = model_per_type_opt.get(mid, {})
        ranking_list.append({
            "rank": rank_idx,
            "model_id": mid,
            "model_label": model_labels.get(mid, mid),
            "mean_score": _safe_round(score),
            "per_type_optimal": type_opts,
        })

    best_model = ranking_list[0] if ranking_list else None

    # Build best model per-category chart data (each category uses its own optimal temp)
    best_category_scores = {}
    if best_model:
        bmid = best_model["model_id"]
        for ttype, opt in model_per_type_opt.get(bmid, {}).items():
            best_category_scores[ttype] = {
                "mean_score": opt["mean_score"],
                "std_dev": opt["std_dev"],
                "temperature": opt["temperature"],
                "count": opt["count"],
            }

    # Global per-temp stats for detail view (informational)
    model_global_stats = {}
    for mid, temps in model_temp_all.items():
        model_global_stats[mid] = {}
        for temp, scores in temps.items():
            n = len(scores)
            mean = sum(scores) / n if n else 0
            variance = sum((s - mean) ** 2 for s in scores) / n if n > 1 else 0
            model_global_stats[mid][temp] = {
                "mean_score": _safe_round(mean),
                "min_score": _safe_round(min(scores)),
                "max_score": _safe_round(max(scores)),
                "std_dev": _safe_round(variance ** 0.5),
                "count": n,
            }

    return {
        "model_global_stats": model_global_stats,
        "model_per_type_optimal": {mid: dict(opts) for mid, opts in model_per_type_opt.items()},
        "ranking": ranking_list,
        "best_model": best_model,
        "best_category_scores": best_category_scores,
        "model_labels": model_labels,
        "has_benchmark_data": True,
    }


def build_benchmark_chart_data(stats: dict) -> dict:
    if not stats.get("has_benchmark_data"):
        return {}

    best = stats.get("best_model")
    if not best:
        return {}

    bmid = best["model_id"]
    type_opts = stats.get("model_per_type_optimal", {}).get(bmid, {})
    categories = sorted(type_opts.keys())
    means = [type_opts[c]["mean_score"] for c in categories]
    std_devs = [type_opts[c]["std_dev"] for c in categories]
    temps = [type_opts[c]["temperature"] for c in categories]

    return {
        "best_model_label": best["model_label"],
        "categories": categories,
        "category_scores": means,
        "category_std_dev": std_devs,
        "category_temps": temps,
    }
