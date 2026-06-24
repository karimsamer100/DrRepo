from __future__ import annotations

import hashlib
from typing import Dict, List, Any

DEFAULT_SPLIT_RATIOS: Dict[str, float] = {"train": 0.7, "validation": 0.15, "test": 0.15}


def _validate_ratios(ratios: Dict[str, float]) -> None:
    if set(ratios.keys()) != {"train", "validation", "test"}:
        raise ValueError("ratios must include exactly train, validation, test")
    for k, v in ratios.items():
        if not isinstance(v, (int, float)) or v < 0:
            raise ValueError(f"invalid ratio for {k}: {v}")
    s = sum(ratios.values())
    if abs(s - 1.0) > 1e-6:
        raise ValueError(f"ratios must sum to 1.0, got {s}")


def assign_split(identifier: str, ratios: Dict[str, float] | None = None) -> str:
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("identifier must be a non-empty string")
    ratios = ratios or DEFAULT_SPLIT_RATIOS
    _validate_ratios(ratios)

    h = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
    val = int(h, 16) / float(2 ** (len(h) * 4))

    # determine split by cumulative ranges
    cum = 0.0
    for split in ("train", "validation", "test"):
        r = ratios[split]
        if val < cum + r:
            return split
        cum += r
    return "test"


def split_dataset(records: List[Dict[str, Any]], ratios: Dict[str, float] | None = None) -> Dict[str, List[Dict[str, Any]]]:
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    ratios = ratios or DEFAULT_SPLIT_RATIOS
    _validate_ratios(ratios)

    out = {"train": [], "validation": [], "test": []}
    for rec in records:
        src = rec.get("source")
        if not isinstance(src, dict):
            raise ValueError("record missing source")
        identifier = src.get("identifier")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("record source.identifier must be a non-empty string")
        split = assign_split(identifier, ratios)
        out[split].append(rec)

    return out
