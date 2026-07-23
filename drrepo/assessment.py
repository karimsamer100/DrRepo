from __future__ import annotations

from typing import Any, Iterable

from drrepo.analyzers.registry import is_core_analyzer


OPTIONAL_EVIDENCE_TOOLS = ("ruff", "bandit", "radon", "coverage", "pytest")

GENERAL_HARD_FLAG_SCORE_CAP = 84
HARD_FLAG_SCORE_CAPS = {
    "TESTS_FAILING": 79,
    "TESTS_COULD_NOT_RUN": 79,
    "ANALYZER_ERRORS_PRESENT": 79,
}


def _get(entry: Any, key: str, default: Any = None) -> Any:
    if isinstance(entry, dict):
        return entry.get(key, default)
    return getattr(entry, key, default)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _finding_value(finding: Any, key: str, default: Any = None) -> Any:
    if isinstance(finding, dict):
        return finding.get(key, default)
    return getattr(finding, key, default)


def first_seen_dedup(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def derive_hard_flags(entries: Iterable[Any]) -> list[str]:
    flags: list[str] = []

    for entry in entries:
        tool = _get(entry, "tool") or _get(entry, "name") or ""
        status = _get(entry, "status")
        findings = _as_list(_get(entry, "findings"))
        summary = _get(entry, "summary") or {}
        outcome = summary.get("outcome") if isinstance(summary, dict) else None

        if status in ("failed_to_run", "partial") and is_core_analyzer(str(tool)):
            flags.append("ANALYZER_ERRORS_PRESENT")

        if tool == "bandit":
            if any(str(_finding_value(f, "severity", "")).lower() in {"high", "critical"} for f in findings):
                flags.append("SECURITY_FINDINGS_PRESENT")
        if tool == "pytest":
            finding_codes = {_finding_value(f, "code") for f in findings}
            if "PYTEST-FAILED" in finding_codes or outcome == "failed_tests":
                flags.append("TESTS_FAILING")
            if status == "failed_to_run" or "PYTEST-ERROR" in finding_codes or outcome in {"collection_error", "env_error", "timeout"}:
                flags.append("TESTS_COULD_NOT_RUN")

    return first_seen_dedup(flags)


def cap_score_for_hard_flags(score: int | float | None, hard_flags: list[str]) -> int | float | None:
    if score is None:
        return None
    if not hard_flags:
        return score

    cap = GENERAL_HARD_FLAG_SCORE_CAP
    for flag in hard_flags:
        cap = min(cap, HARD_FLAG_SCORE_CAPS.get(flag, GENERAL_HARD_FLAG_SCORE_CAP))

    try:
        numeric_score = int(round(float(score)))
    except Exception:
        return score
    return min(numeric_score, cap)


def build_evidence_confidence(entries: Iterable[Any]) -> dict[str, Any]:
    statuses: dict[str, str | None] = {tool: None for tool in OPTIONAL_EVIDENCE_TOOLS}
    for entry in entries:
        tool = _get(entry, "tool") or _get(entry, "name") or ""
        status = _get(entry, "status")
        if tool in statuses and statuses[tool] is None and isinstance(status, str):
            statuses[tool] = status

    available = [
        tool
        for tool, status in statuses.items()
        if status not in (None, "not_available", "not_applicable", "skipped_by_config", "failed_to_run", "partial")
    ]
    unavailable = [tool for tool, status in statuses.items() if status in (None, "not_available")]
    skipped = [tool for tool, status in statuses.items() if status in ("not_applicable", "skipped_by_config")]
    failed = [tool for tool, status in statuses.items() if status == "failed_to_run"]
    incomplete = [tool for tool, status in statuses.items() if status == "partial"]
    limited_tools = unavailable + skipped + failed + incomplete

    total = len(OPTIONAL_EVIDENCE_TOOLS)
    assessed_ratio = round(len(available) / total, 2) if total else 0.0

    if not limited_tools:
        return {
            "label": "full",
            "summary": f"Full evidence: all {total} optional tools were available.",
            "assessed_optional_tool_ratio": assessed_ratio,
            "available_optional_tools": available,
            "missing_optional_tools": [],
            "skipped_optional_tools": [],
            "failed_optional_tools": [],
            "incomplete_optional_tools": [],
        }

    label = "limited" if len(limited_tools) * 2 >= len(OPTIONAL_EVIDENCE_TOOLS) else "partial"
    title = "Limited evidence" if label == "limited" else "Partial evidence"
    unavailable_text = ", ".join(unavailable) if unavailable else "none"
    skipped_text = ", ".join(skipped) if skipped else "none"
    failed_text = ", ".join(failed) if failed else "none"
    incomplete_text = ", ".join(incomplete) if incomplete else "none"
    summary = (
        f"{title}: {len(available)} of {total} optional tools were available. "
        f"Unavailable: {unavailable_text}. Skipped: {skipped_text}. Failed: {failed_text}. Incomplete: {incomplete_text}."
    )
    return {
        "label": label,
        "summary": summary,
        "assessed_optional_tool_ratio": assessed_ratio,
        "available_optional_tools": available,
        "missing_optional_tools": unavailable,
        "skipped_optional_tools": skipped,
        "failed_optional_tools": failed,
        "incomplete_optional_tools": incomplete,
    }
