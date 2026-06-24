from __future__ import annotations

from typing import Dict, Any, List
from drrepo.ml.baseline import predict_record_baseline

_WEAK_METHODS = {"rule_score", "baseline_prediction", "copied_from_score"}


def _is_provenance_weak(prov: dict) -> bool:
    if not isinstance(prov, dict):
        return True
    method = prov.get("method")
    if not method:
        return True
    if isinstance(method, str) and method in _WEAK_METHODS:
        return True
    reviewed = prov.get("reviewed_evidence")
    if not isinstance(reviewed, list) or len(reviewed) == 0:
        return True
    return False


def detect_label_leakage_risks(record: Dict[str, Any]) -> List[str]:
    risks: List[str] = []
    labels = record.get("labels") or {}
    if not labels:
        return risks

    prov = record.get("label_provenance") or {}

    method = prov.get("method")
    if isinstance(method, str) and method in _WEAK_METHODS:
        risks.append("label_provenance.method indicates weak provenance (rule_score/baseline/copied)")

    # missing reviewed evidence
    if "reviewed_evidence" not in prov or not isinstance(prov.get("reviewed_evidence"), list) or len(prov.get("reviewed_evidence") or []) == 0:
        risks.append("label_provenance.reviewed_evidence missing or empty")

    # baseline agreement checks
    baseline = predict_record_baseline(record)
    repo_label = labels.get("repository_readiness_label")
    port_label = labels.get("portfolio_readiness_label")

    if repo_label is not None and repo_label == baseline.get("repository_readiness_baseline") and _is_provenance_weak(prov):
        risks.append("repository readiness label matches baseline and provenance is weak or missing")

    if port_label is not None and port_label == baseline.get("portfolio_readiness_baseline") and _is_provenance_weak(prov):
        risks.append("portfolio readiness label matches baseline and provenance is weak or missing")

    return risks


def detect_dataset_leakage_risks(records: object) -> List[str]:
    warnings: List[str] = []
    if not isinstance(records, list):
        return ["records must be a list"]

    labeled_count = 0
    baseline_match_and_weak = 0

    for idx, rec in enumerate(records):
        src = rec.get("source") or {}
        identifier = src.get("identifier")
        rec_warnings = detect_label_leakage_risks(rec)
        for w in rec_warnings:
            warnings.append(f"record[{idx}] identifier={identifier}: {w}")

        if rec.get("labels"):
            labeled_count += 1
            prov = rec.get("label_provenance") or {}
            baseline = predict_record_baseline(rec)
            repo_label = rec.get("labels", {}).get("repository_readiness_label")
            port_label = rec.get("labels", {}).get("portfolio_readiness_label")
            match_repo = repo_label is not None and repo_label == baseline.get("repository_readiness_baseline")
            match_port = port_label is not None and port_label == baseline.get("portfolio_readiness_baseline")
            if (match_repo or match_port) and _is_provenance_weak(prov):
                baseline_match_and_weak += 1

    if labeled_count > 0 and baseline_match_and_weak == labeled_count:
        warnings.append("All labeled records match baseline predictions with weak provenance — risk of label leakage")

    return warnings
