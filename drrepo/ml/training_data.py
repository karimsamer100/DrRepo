from __future__ import annotations

from typing import List, Dict, Any
from copy import deepcopy

from drrepo.features.schema import FEATURE_FIELDS


REPOSITORY_LABEL_FIELD = "repository_readiness_label"
PORTFOLIO_LABEL_FIELD = "portfolio_readiness_label"


def get_ordered_feature_names() -> List[str]:
    return list(FEATURE_FIELDS)


def _convert_value_to_float(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    # intentionally reject strings and complex types
    raise ValueError(f"unsupported feature value type: {type(v)}")


def extract_feature_matrix(records: List[Dict[str, Any]], feature_names: List[str] | None = None) -> List[List[float]]:
    fnames = list(feature_names) if feature_names is not None else get_ordered_feature_names()
    out: List[List[float]] = []
    for rec in records:
        features = rec.get("features") or {}
        row: List[float] = []
        for n in fnames:
            val = features.get(n, None)
            if val is None:
                row.append(0.0)
            else:
                try:
                    row.append(_convert_value_to_float(val))
                except ValueError:
                    raise
        out.append(row)
    return out


def extract_labels(records: List[Dict[str, Any]], label_field: str = REPOSITORY_LABEL_FIELD) -> List[str]:
    if label_field not in (REPOSITORY_LABEL_FIELD, PORTFOLIO_LABEL_FIELD):
        raise ValueError("unsupported label_field")
    labels: List[str] = []
    for rec in records:
        lab = (rec.get("labels") or {}).get(label_field)
        if lab is not None:
            labels.append(lab)
    return labels


def filter_labeled_records(records: List[Dict[str, Any]], label_field: str = REPOSITORY_LABEL_FIELD) -> List[Dict[str, Any]]:
    if label_field not in (REPOSITORY_LABEL_FIELD, PORTFOLIO_LABEL_FIELD):
        raise ValueError("unsupported label_field")
    return [r for r in records if (r.get("labels") or {}).get(label_field) is not None]


def prepare_supervised_dataset(records: List[Dict[str, Any]], label_field: str = REPOSITORY_LABEL_FIELD, feature_names: List[str] | None = None) -> Dict[str, Any]:
    # Do not mutate inputs
    records_copy = list(records)
    labeled = filter_labeled_records(records_copy, label_field)
    if not labeled:
        fnames = list(feature_names) if feature_names is not None else get_ordered_feature_names()
        return {
            "feature_names": fnames,
            "label_field": label_field,
            "record_ids": [],
            "X": [],
            "y": [],
            "record_count": 0,
        }

    fnames = list(feature_names) if feature_names is not None else get_ordered_feature_names()
    record_ids = [r.get("record_id") for r in labeled]
    X = extract_feature_matrix(labeled, fnames)
    y = extract_labels(labeled, label_field)
    if not (len(X) == len(y) == len(record_ids)):
        raise ValueError("mismatched lengths between X, y, and record_ids")

    return {
        "feature_names": fnames,
        "label_field": label_field,
        "record_ids": record_ids,
        "X": X,
        "y": y,
        "record_count": len(record_ids),
    }


def prepare_split_supervised_datasets(split_records: Dict[str, List[Dict[str, Any]]], label_field: str = REPOSITORY_LABEL_FIELD, feature_names: List[str] | None = None) -> Dict[str, Dict[str, Any]]:
    # Require split keys
    expected = {"train", "validation", "test"}
    if not expected.issubset(set(split_records.keys())):
        raise ValueError("split_records must contain train, validation, and test keys")
    fnames = list(feature_names) if feature_names is not None else get_ordered_feature_names()
    out: Dict[str, Dict[str, Any]] = {}
    for k in ("train", "validation", "test"):
        out[k] = prepare_supervised_dataset(list(split_records[k]), label_field=label_field, feature_names=fnames)
    return out
