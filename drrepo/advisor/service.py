from __future__ import annotations

from copy import deepcopy

from .priorities import build_profiled_action_plan
from .prompting import build_llm_prompt_bundle
from .profiles import validate_profile_id
from .reporting import build_deterministic_advisor_report

ADVISOR_SERVICE_VERSION = "v1"


def build_advisor_result(
    audit: dict[str, object],
    profile_id: str = "student_portfolio",
    max_actions: int = 5,
    include_prompt_bundle: bool = False,
) -> dict[str, object]:
    validate_profile_id(profile_id)

    audit_copy = deepcopy(audit) if isinstance(audit, dict) else {}
    profiled_action_plan = build_profiled_action_plan(audit_copy, profile_id=profile_id, max_actions=max_actions)
    advisor_report = build_deterministic_advisor_report(audit_copy, profile_id=profile_id, max_actions=max_actions)

    result: dict[str, object] = {
        "advisor_service_version": ADVISOR_SERVICE_VERSION,
        "profile_id": profile_id,
        "advisor_report": advisor_report,
    }

    if include_prompt_bundle:
        result["prompt_bundle"] = build_llm_prompt_bundle(audit_copy, profiled_action_plan)

    return result
