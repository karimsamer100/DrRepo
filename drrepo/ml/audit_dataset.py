from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any
import json

from .dataset_builder import build_dataset_records, validate_dataset
from .dataset import write_jsonl, read_jsonl
from .artifacts import build_dataset_artifact_manifest


def load_audit_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("audit JSON root must be an object")
    return data


def _stem(p: str | Path) -> str:
    return Path(p).stem


def build_dataset_records_from_audit_files(
    audit_paths: List[str | Path],
    source_type: str = "manual",
    labels_by_identifier: Dict[str, Dict[str, Any]] | None = None,
    label_provenance_by_identifier: Dict[str, Dict[str, Any]] | None = None,
    source_metadata_by_identifier: Dict[str, Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    audits: List[Dict[str, Any]] = []
    identifiers: List[str] = []
    for p in audit_paths:
        audits.append(load_audit_json(p))
        identifiers.append(_stem(p))

    records = build_dataset_records(
        audits,
        source_type,
        identifiers,
        labels_by_identifier=labels_by_identifier,
        label_provenance_by_identifier=label_provenance_by_identifier,
        source_metadata_by_identifier=source_metadata_by_identifier,
    )
    return records


def export_dataset_from_audit_files(
    audit_paths: List[str | Path],
    dataset_path: str | Path,
    manifest_path: str | Path,
    dataset_name: str,
    dataset_description: str = "",
    source_type: str = "manual",
    labels_by_identifier: Dict[str, Dict[str, Any]] | None = None,
    label_provenance_by_identifier: Dict[str, Dict[str, Any]] | None = None,
    source_metadata_by_identifier: Dict[str, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    # Build records
    records = build_dataset_records_from_audit_files(
        audit_paths,
        source_type=source_type,
        labels_by_identifier=labels_by_identifier,
        label_provenance_by_identifier=label_provenance_by_identifier,
        source_metadata_by_identifier=source_metadata_by_identifier,
    )

    # Validate dataset (collect errors but proceed)
    validation_errors = validate_dataset(records)

    # Write dataset JSONL
    write_jsonl(records, dataset_path)

    # Build manifest (includes quality report which should surface validation issues)
    manifest = build_dataset_artifact_manifest(records, dataset_name, description=dataset_description)

    # augment manifest with validation errors if any
    if validation_errors:
        manifest.setdefault("validation_errors", validation_errors)

    # write manifest JSON
    mp = Path(manifest_path)
    with mp.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return manifest
