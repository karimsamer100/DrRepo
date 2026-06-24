from __future__ import annotations

from typing import List, Dict, Any

from .dataset import build_dataset_record, validate_dataset_record


def build_dataset_records(
    audits: List[Dict[str, Any]],
    source_type: str,
    source_identifiers: List[str],
    labels_by_identifier: Dict[str, Dict[str, Any]] | None = None,
    label_provenance_by_identifier: Dict[str, Dict[str, Any]] | None = None,
    source_metadata_by_identifier: Dict[str, Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    if len(audits) != len(source_identifiers):
        raise ValueError("audits and source_identifiers must have the same length")

    labels_by_identifier = labels_by_identifier or {}
    label_provenance_by_identifier = label_provenance_by_identifier or {}
    source_metadata_by_identifier = source_metadata_by_identifier or {}

    records: List[Dict[str, Any]] = []
    for audit, identifier in zip(audits, source_identifiers):
        labels = labels_by_identifier.get(identifier) or {}
        prov = label_provenance_by_identifier.get(identifier) or {}
        src_meta = source_metadata_by_identifier.get(identifier) or {}
        rec = build_dataset_record(audit, source_type, identifier, labels=labels, label_provenance=prov, source_metadata=src_meta)
        records.append(rec)

    return records


def validate_dataset(records: object) -> List[str]:
    errors: List[str] = []
    if not isinstance(records, list):
        errors.append("records must be a list")
        return errors

    seen_ids: set = set()
    seen_source_pairs: set = set()
    for idx, rec in enumerate(records):
        # validate structure
        errs = validate_dataset_record(rec)
        for e in errs:
            errors.append(f"record[{idx}]: {e}")

        # duplicate record_id
        rid = rec.get("record_id")
        if rid in seen_ids:
            errors.append(f"record[{idx}]: duplicate record_id {rid}")
        else:
            seen_ids.add(rid)

        # duplicate source pair
        src = rec.get("source") or {}
        st = src.get("type")
        si = src.get("identifier")
        pair = (st, si)
        if pair in seen_source_pairs:
            errors.append(f"record[{idx}]: duplicate source pair {pair}")
        else:
            seen_source_pairs.add(pair)

    return errors
