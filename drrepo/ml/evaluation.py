from __future__ import annotations

from typing import List, Dict, Any
from collections import defaultdict
from copy import deepcopy

from .baseline import predict_record_baseline


EVALUATION_REPORT_VERSION = "v1"


def confusion_matrix(y_true: List[str], y_pred: List[str], labels: List[str] | None = None) -> Dict[str, Dict[str, int]]:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    if labels is None:
        labels = sorted(set(list(y_true) + list(y_pred)))
    labels = list(labels)
    # initialize
    mat: Dict[str, Dict[str, int]] = {}
    for a in labels:
        mat[a] = {p: 0 for p in labels}

    for t, p in zip(y_true, y_pred):
        if t not in mat:
            # ensure unseen label appears
            mat.setdefault(t, {lbl: 0 for lbl in labels})
        if p not in mat[t]:
            mat[t].setdefault(p, 0)
        mat[t][p] += 1

    # ensure all rows/cols present for any labels seen in data
    all_labels = labels
    for a in all_labels:
        if a not in mat:
            mat[a] = {p: 0 for p in all_labels}
        else:
            for p in all_labels:
                mat[a].setdefault(p, 0)

    return mat


def _safe_div(n: float, d: float) -> float:
    if d == 0:
        return 0.0
    return n / d


def classification_metrics(y_true: List[str], y_pred: List[str], labels: List[str] | None = None) -> Dict[str, Any]:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    n = len(y_true)
    if n == 0:
        return {
            "sample_count": 0,
            "accuracy": 0.0,
            "macro_precision": 0.0,
            "macro_recall": 0.0,
            "macro_f1": 0.0,
            "weighted_precision": 0.0,
            "weighted_recall": 0.0,
            "weighted_f1": 0.0,
            "per_class": {},
            "confusion_matrix": {},
        }

    cm = confusion_matrix(y_true, y_pred, labels)
    labels_list = list(sorted(cm.keys()))

    per_class: Dict[str, Dict[str, Any]] = {}
    supports: Dict[str, int] = {}
    precisions: List[float] = []
    recalls: List[float] = []
    f1s: List[float] = []
    weights: List[int] = []

    correct = 0
    for a in labels_list:
        row = cm.get(a, {})
        tp = row.get(a, 0)
        fn = sum(v for k, v in row.items() if k != a)
        fp = sum(cm.get(o, {}).get(a, 0) for o in labels_list if o != a)
        support = sum(row.values())
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall) if (precision + recall) > 0 else 0.0
        per_class[a] = {
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "support": support,
        }
        supports[a] = support
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)
        weights.append(support)
        correct += tp

    accuracy = _safe_div(correct, n)

    # macro
    macro_precision = round(sum(precisions) / len(precisions), 6) if precisions else 0.0
    macro_recall = round(sum(recalls) / len(recalls), 6) if recalls else 0.0
    macro_f1 = round(sum(f1s) / len(f1s), 6) if f1s else 0.0

    # weighted
    total_support = sum(weights)
    if total_support == 0:
        weighted_precision = weighted_recall = weighted_f1 = 0.0
    else:
        weighted_precision = round(sum(p * w for p, w in zip(precisions, weights)) / total_support, 6)
        weighted_recall = round(sum(r * w for r, w in zip(recalls, weights)) / total_support, 6)
        weighted_f1 = round(sum(f * w for f, w in zip(f1s, weights)) / total_support, 6)

    result = {
        "sample_count": n,
        "accuracy": round(accuracy, 6),
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "weighted_precision": weighted_precision,
        "weighted_recall": weighted_recall,
        "weighted_f1": weighted_f1,
        "per_class": per_class,
        "confusion_matrix": cm,
    }

    return result


def _collect_labeled_records(records: List[Dict[str, Any]], label_field: str) -> List[Dict[str, Any]]:
    return [r for r in records if (r.get("labels") or {}).get(label_field) is not None]


def evaluate_repository_baseline(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    # do not mutate
    recs = list(records)
    label_field = "repository_readiness_label"
    pred_field = "repository_readiness_baseline"
    labeled = _collect_labeled_records(recs, label_field)
    record_ids: List[str] = [r.get("record_id") for r in labeled]
    y_true = [ (r.get("labels") or {}).get(label_field) for r in labeled ]
    y_pred = [ predict_record_baseline(r).get(pred_field) for r in labeled ]
    metrics = classification_metrics(y_true, y_pred) if labeled else classification_metrics([], [])
    return {
        "report_version": EVALUATION_REPORT_VERSION,
        "label_field": label_field,
        "prediction_field": pred_field,
        "metrics": metrics,
        "record_ids": record_ids,
    }


def evaluate_portfolio_baseline(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    recs = list(records)
    label_field = "portfolio_readiness_label"
    pred_field = "portfolio_readiness_baseline"
    labeled = _collect_labeled_records(recs, label_field)
    record_ids: List[str] = [r.get("record_id") for r in labeled]
    y_true = [ (r.get("labels") or {}).get(label_field) for r in labeled ]
    y_pred = [ predict_record_baseline(r).get(pred_field) for r in labeled ]
    metrics = classification_metrics(y_true, y_pred) if labeled else classification_metrics([], [])
    return {
        "report_version": EVALUATION_REPORT_VERSION,
        "label_field": label_field,
        "prediction_field": pred_field,
        "metrics": metrics,
        "record_ids": record_ids,
    }


def evaluate_split_baselines(split_records: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    expected = {"train", "validation", "test"}
    if not expected.issubset(set(split_records.keys())):
        raise ValueError("split_records must contain train, validation, and test keys")
    out: Dict[str, Dict[str, Any]] = {}
    for k in ("train", "validation", "test"):
        recs = list(split_records[k])
        out[k] = {
            "repository": evaluate_repository_baseline(recs),
            "portfolio": evaluate_portfolio_baseline(recs),
        }
    return out
