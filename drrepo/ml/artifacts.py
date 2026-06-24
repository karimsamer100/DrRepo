from __future__ import annotations

from typing import List, Dict, Any
import json
import hashlib

from drrepo.ml.quality import build_dataset_quality_report


DATASET_ARTIFACT_VERSION = "v1"


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_dataset_artifact_manifest(records: List[Dict[str, Any]], name: str, description: str = "") -> Dict[str, Any]:
    if not isinstance(name, str) or not name:
        raise ValueError("name must be a non-empty string")

    record_ids = [r.get("record_id") for r in records]
    record_ids_stable = list(record_ids)
    feature_versions = sorted({r.get("feature_schema_version") for r in records if r.get("feature_schema_version")})

    fingerprint_payload = {
        "artifact_version": DATASET_ARTIFACT_VERSION,
        "name": name,
        "record_ids": record_ids_stable,
        "feature_schema_versions": feature_versions,
        "record_count": len(records),
    }
    fingerprint = hashlib.sha256(_stable_json(fingerprint_payload).encode("utf-8")).hexdigest()

    quality = build_dataset_quality_report(records)

    manifest = {
        "artifact_version": DATASET_ARTIFACT_VERSION,
        "name": name,
        "description": description,
        "record_count": len(records),
        "dataset_fingerprint": fingerprint,
        "quality_report": quality,
    }
    return manifest


def validate_dataset_artifact_manifest(manifest: object) -> List[str]:
    errs: List[str] = []
    if not isinstance(manifest, dict):
        errs.append("manifest must be a dict")
        return errs
    if manifest.get("artifact_version") != DATASET_ARTIFACT_VERSION:
        errs.append(f"artifact_version must be {DATASET_ARTIFACT_VERSION}")
    name = manifest.get("name")
    if not isinstance(name, str) or not name:
        errs.append("name must be a non-empty string")
    rc = manifest.get("record_count")
    if not isinstance(rc, int) or rc < 0:
        errs.append("record_count must be a non-negative integer")
    fp = manifest.get("dataset_fingerprint")
    if not isinstance(fp, str) or not fp:
        errs.append("dataset_fingerprint must be a non-empty string")
    qr = manifest.get("quality_report")
    if not isinstance(qr, dict):
        errs.append("quality_report must be a dict")
    return errs
