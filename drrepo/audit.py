from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from drrepo.input.resolver import resolve_local_path
from drrepo.scanner.repository_scanner import scan_repository
from drrepo.analyzers.service import (
    run_static_analyzers,
    static_analyzers_to_dict,
)
from drrepo.analyzers.test_service import run_test_analyzers, test_analyzers_to_dict
from drrepo.analyzers.repository_service import (
    run_repository_analyzers,
    repository_analyzers_to_dict,
)
from drrepo.scoring import score_audit_sections
from drrepo.diagnosis import build_diagnosis
from drrepo.remediation.suggestions import generate_suggestions, count_suggestions_by_severity
from drrepo.analyzers.registry import validate_analysis_mode
from drrepo.environment import detect_dependency_environment
from drrepo.intelligence import build_repository_intelligence
from drrepo.readiness import build_devops_readiness
from drrepo.architecture import build_architecture_assessment


def _run_with_mode(fn, root: str | Path, *, source_type: str, analysis_mode: str):
    try:
        return fn(root, source_type=source_type, analysis_mode=analysis_mode)
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        return fn(root)


def _run_tests_with_mode(fn, root: str | Path, *, source_type: str, analysis_mode: str, execute_tests: bool | None, isolated_options: dict[str, Any] | None):
    try:
        return fn(root, source_type=source_type, analysis_mode=analysis_mode, isolated_options=isolated_options)
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        if execute_tests is not None:
            return fn(root, execute_tests=execute_tests)
        return fn(root)


def build_audit(
    path: str | Path,
    *,
    execute_tests: bool | None = None,
    source_type: str = "local_path",
    analysis_mode: str | None = None,
    profile_id: str = "student_portfolio",
    isolated_options: dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build the full audit dictionary for the given path.

    This function resolves the path, scans the repository, runs analyzers,
    computes scoring, and returns the final audit dict without printing.
    It intentionally does not catch broad exceptions so callers (CLI/tests)
    can handle them consistently.
    """
    if analysis_mode is None:
        if execute_tests is None:
            mode = validate_analysis_mode(source_type, None)
        else:
            mode = "deep_local" if execute_tests else "quick_safe"
            mode = validate_analysis_mode(source_type, mode)
    else:
        mode = validate_analysis_mode(source_type, analysis_mode)

    resolved = resolve_local_path(path)
    scanned = scan_repository(resolved)

    root = scanned["path"]

    static_results = _run_with_mode(run_static_analyzers, root, source_type=source_type, analysis_mode=mode)
    test_results = _run_tests_with_mode(
        run_test_analyzers,
        root,
        source_type=source_type,
        analysis_mode=mode,
        execute_tests=execute_tests,
        isolated_options=isolated_options,
    )
    repo_results = _run_with_mode(run_repository_analyzers, root, source_type=source_type, analysis_mode=mode)

    scoring = score_audit_sections(static_results, test_results, repo_results)

    scanned["static_analysis"] = static_analyzers_to_dict(static_results)
    scanned["test_analysis"] = test_analyzers_to_dict(test_results)
    scanned["repository_analysis"] = repository_analyzers_to_dict(repo_results)
    scanned["analysis"] = {
        "mode": mode,
        "source_type": source_type,
        "executes_repository_code": mode in {"deep_local", "deep_isolated"},
        "isolated_options": isolated_options if mode == "deep_isolated" else None,
    }
    scanned["dependency_environment"] = detect_dependency_environment(root)
    scanned["scoring"] = scoring

    # Build diagnosis before remediation so future remediations can use it
    scanned["diagnosis"] = build_diagnosis(scanned)

    # Generate remediation suggestions after analyzers, scoring, and diagnosis are attached
    remediation = generate_suggestions(scanned)
    scanned["remediation_suggestions"] = remediation
    scanned["remediation_summary"] = {
        "total": len(remediation),
        "by_severity": count_suggestions_by_severity(remediation),
    }
    scanned.update(build_repository_intelligence(scanned, profile_id=profile_id))
    scanned["devops_readiness"] = build_devops_readiness(scanned, profile_id=profile_id)
    scanned["architecture_assessment"] = build_architecture_assessment(scanned)
    devops_recommendations = scanned["devops_readiness"].get("recommendations", [])
    if isinstance(devops_recommendations, list):
        existing = scanned.get("recommendations_v2", [])
        scanned["recommendations_v2"] = _prioritize_recommendations([*existing, *devops_recommendations], profile_id=profile_id)
        _refresh_executive_priorities(scanned)

    return scanned


def _prioritize_recommendations(recommendations: list[dict[str, Any]], *, profile_id: str) -> list[dict[str, Any]]:
    profile_category_rank = _profile_category_rank(profile_id)
    type_rank = {
        "release_blocker": 0,
        "security_review": 1,
        "repository_fix": 2,
        "verification_step": 3,
        "optional_improvement": 4,
        "audit_environment": 5,
    }
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
    deduped = _dedupe_recommendation_dicts(recommendations)
    sorted_recs = sorted(
        deduped,
        key=lambda rec: (
            profile_category_rank.get(str(rec.get("category", "")), 50),
            type_rank.get(str(rec.get("recommendation_type", "repository_fix")), 2),
            severity_rank.get(str(rec.get("severity", "unknown")), 4),
            int(rec.get("priority", 999) or 999),
            str(rec.get("title", "")),
        ),
    )
    for index, rec in enumerate(sorted_recs, start=1):
        rec["priority"] = index
    return sorted_recs


def _profile_category_rank(profile_id: str) -> dict[str, int]:
    if profile_id in {"production_service", "production_api"}:
        order = ["security", "testing", "ci_cd", "deployment", "containerization", "observability", "reproducibility"]
    elif profile_id == "ai_ml_project":
        order = ["reproducibility", "documentation", "testing", "architecture", "code_quality", "security"]
    else:
        order = ["documentation", "reproducibility", "testing", "architecture", "code_quality", "security", "ci_cd", "containerization"]
    return {category: index for index, category in enumerate(order)}


def _dedupe_recommendation_dicts(recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for rec in recommendations:
        if not isinstance(rec, dict):
            continue
        key = _recommendation_root_key(rec)
        if key in seen:
            continue
        seen.add(key)
        result.append(rec)
    return result


def _recommendation_root_key(rec: dict[str, Any]) -> str:
    rec_id = str(rec.get("id") or "")
    category = str(rec.get("category") or "")
    if rec_id in {"readme-documentation", "devops-ci.missing"} or "ci.missing" in rec_id:
        return "ci" if category == "ci_cd" else rec_id
    if "readme" in rec_id or category == "documentation":
        return "documentation"
    if "ruff" in rec_id or category == "code_quality":
        return "code_quality"
    if "bandit" in rec_id or category == "security":
        return "security"
    title = str(rec.get("title") or "").lower()
    return f"{category}:{title}"


def _refresh_executive_priorities(audit: Dict[str, Any]) -> None:
    executive = audit.get("executive_report")
    recommendations = audit.get("recommendations_v2")
    if not isinstance(executive, dict) or not isinstance(recommendations, list) or not recommendations:
        return
    top = next((rec for rec in recommendations if isinstance(rec, dict)), None)
    if not top:
        return
    title = top.get("title")
    if isinstance(title, str) and title:
        executive["biggest_gap"] = title
    steps = top.get("recommended_steps")
    if isinstance(steps, list) and steps:
        first_step = str(steps[0])
    else:
        first_step = str(top.get("success_check") or top.get("why_it_matters") or "")
    if first_step:
        executive["next_best_step"] = first_step
    executive["recommended_next_move"] = {
        "recommendation_id": top.get("id"),
        "title": title,
        "reason": top.get("why_it_matters"),
        "evidence_references": top.get("source_finding_ids") or top.get("related_findings") or top.get("evidence") or [],
        "first_step": first_step,
        "success_check": top.get("success_check"),
        "profile_relevance": top.get("profile_relevance"),
        "confidence": top.get("confidence"),
    }
