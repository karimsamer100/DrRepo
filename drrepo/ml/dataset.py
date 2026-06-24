from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List

from drrepo.features.schema import FEATURE_SCHEMA_VERSION, FEATURE_FIELDS
from drrepo.features import build_feature_row, validate_feature_row
from .labels import LABEL_RUBRIC_VERSION, validate_labels


DATASET_RECORD_VERSION = "v1"
ALLOWED_SOURCE_TYPES = ("local_path", "github_url", "synthetic", "fixture", "manual")


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _make_record_id(record_version: str, feature_schema_version: str, source_type: str, source_identifier: str, features: Dict[str, Any]) -> str:
    payload = {
        "record_version": record_version,
        "feature_schema_version": feature_schema_version,
        "source_type": source_type,
        "source_identifier": source_identifier,
        "features": features,
    }
    s = _stable_json(payload)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def build_dataset_record(
    audit: Dict[str, Any],
    source_type: str,
    source_identifier: str,
    labels: Dict[str, Any] | None = None,
    label_provenance: Dict[str, Any] | None = None,
    source_metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if source_type not in ALLOWED_SOURCE_TYPES:
        raise ValueError(f"invalid source_type: {source_type}")
    if not isinstance(source_identifier, str) or not source_identifier:
        raise ValueError("source_identifier must be a non-empty string")

    features_row = build_feature_row(audit or {})

    # extract only FEATURE_FIELDS
    features: Dict[str, Any] = {k: features_row.get(k) for k in FEATURE_FIELDS}

    feature_schema_version = features_row.get("schema_version") or FEATURE_SCHEMA_VERSION

    source = {"type": source_type, "identifier": source_identifier}
    if source_metadata:
        # ensure metadata can't override type or identifier
        for k in ("type", "identifier"):
            if k in source_metadata and source_metadata[k] != source[k]:
                raise ValueError(f"source_metadata must not override {k}")
        source.update({k: v for k, v in source_metadata.items() if k not in ("type", "identifier")})

    labels = labels or {}
    label_provenance = label_provenance or {}

    record = {
        "record_version": DATASET_RECORD_VERSION,
        "feature_schema_version": feature_schema_version,
        "source": source,
        "features": features,
        "labels": labels,
        "label_provenance": label_provenance,
    }

    record_id = _make_record_id(DATASET_RECORD_VERSION, feature_schema_version, source_type, source_identifier, features)
    record["record_id"] = record_id

    return record


def validate_dataset_record(record: object) -> List[str]:
    errors: List[str] = []
    if not isinstance(record, dict):
        errors.append("record must be a dict")
        return errors

    if record.get("record_version") != DATASET_RECORD_VERSION:
        errors.append(f"record_version must be {DATASET_RECORD_VERSION}")

    source = record.get("source")
    if not isinstance(source, dict):
        errors.append("source must be a dict")
    else:
        st = source.get("type")
        si = source.get("identifier")
        if st not in ALLOWED_SOURCE_TYPES:
            errors.append(f"invalid source.type: {st}")
        if not isinstance(si, str) or not si:
            errors.append("source.identifier must be a non-empty string")

    features = record.get("features")
    if not isinstance(features, dict):
        errors.append("features must be a dict")
    else:
        # reconstruct feature row and call validate_feature_row
        feature_schema_version = record.get("feature_schema_version")
        if not feature_schema_version:
            errors.append("missing feature_schema_version")
        else:
            reconstructed = {"schema_version": feature_schema_version, **features}
            errors.extend(validate_feature_row(reconstructed))

    labels = record.get("labels") or {}
    # validate labels
    label_errors = validate_labels(labels)
    errors.extend(label_errors)

    # if labels present, require provenance
    if labels:
        prov = record.get("label_provenance")
        if not isinstance(prov, dict):
            errors.append("label_provenance must be a dict when labels are provided")
        else:
            if prov.get("rubric_version") != LABEL_RUBRIC_VERSION:
                errors.append(f"label_provenance.rubric_version must be {LABEL_RUBRIC_VERSION}")
            for k in ("method", "labeler"):
                if k not in prov:
                    errors.append(f"label_provenance missing required key: {k}")

    return errors


def write_jsonl(records: List[Dict[str, Any]], path: str | Path) -> None:
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    p = Path(path)
    out: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out
