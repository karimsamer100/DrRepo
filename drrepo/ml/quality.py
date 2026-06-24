from __future__ import annotations

from typing import List, Dict, Any
from collections import Counter

from drrepo.ml.dataset_builder import validate_dataset
from drrepo.ml.splits import split_dataset
from drrepo.ml.baseline import predict_record_baseline
from drrepo.ml.leakage import detect_dataset_leakage_risks, detect_label_leakage_risks


def summarize_label_counts(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    repo_counts: Counter = Counter()
    port_counts: Counter = Counter()
    for r in records or []:
        labels = r.get("labels") or {}
        repo = labels.get("repository_readiness_label")
        port = labels.get("portfolio_readiness_label")
        if repo:
            repo_counts[repo] += 1
        if port:
            port_counts[port] += 1
    return {"repository_readiness_label": dict(repo_counts), "portfolio_readiness_label": dict(port_counts)}


def summarize_source_counts(records: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Counter = Counter()
    for r in records or []:
        src = r.get("source") or {}
        st = src.get("type") or "unknown"
        counts[st] += 1
    return dict(counts)


def summarize_baseline_predictions(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    repo_counts: Counter = Counter()
    port_counts: Counter = Counter()
    for r in records or []:
        # consider missing features as malformed
        if "features" not in r:
            repo_counts["error"] += 1
            port_counts["error"] += 1
            continue
        try:
            pred = predict_record_baseline(r)
            repo = pred.get("repository_readiness_baseline")
            port = pred.get("portfolio_readiness_baseline")
            if repo:
                repo_counts[repo] += 1
            if port:
                port_counts[port] += 1
        except Exception:
            repo_counts["error"] += 1
            port_counts["error"] += 1
    return {"repository_readiness_baseline": dict(repo_counts), "portfolio_readiness_baseline": dict(port_counts)}


def build_dataset_quality_report(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    report: Dict[str, Any] = {"report_version": "v1"}
    record_count = len(records or [])
    report["record_count"] = record_count

    # validation
    validation_errors = validate_dataset(records)
    report["validation_errors"] = validation_errors

    # leakage warnings
    leakage_warnings = detect_dataset_leakage_risks(records)
    report["leakage_warnings"] = leakage_warnings

    # source counts
    report["source_type_counts"] = summarize_source_counts(records)

    # label counts
    report["label_counts"] = summarize_label_counts(records)

    # baseline predictions
    report["baseline_prediction_counts"] = summarize_baseline_predictions(records)

    # feature schema versions
    versions = sorted({r.get("feature_schema_version") for r in records if r.get("feature_schema_version")})
    report["feature_schema_versions"] = versions

    # splits
    try:
        splits = split_dataset(records)
        report["split_counts"] = {k: len(v) for k, v in splits.items()}
    except Exception as exc:
        report["split_counts"] = {"train": 0, "validation": 0, "test": 0}
        validation_errors = list(validation_errors) + [f"split error: {exc}"]
        report["validation_errors"] = validation_errors

    # dataset ready for training?
    has_labels = any(r.get("labels") for r in records)
    strong_provenance_for_all_labeled = True
    for r in records:
        if r.get("labels"):
            rec_risks = detect_label_leakage_risks(r)
            if rec_risks:
                strong_provenance_for_all_labeled = False
                break

    dataset_ready = (
        record_count > 0
        and not report.get("validation_errors")
        and not report.get("leakage_warnings")
        and has_labels
        and strong_provenance_for_all_labeled
    )
    report["dataset_ready_for_training"] = bool(dataset_ready)

    return report
