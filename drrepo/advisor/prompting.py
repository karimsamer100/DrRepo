from __future__ import annotations

import json
from copy import deepcopy

from .llm_contract import (
    ADVISOR_ACTION_REQUIRED_FIELDS,
    LLM_ADVISOR_CONTRACT_VERSION,
    build_llm_advisor_payload,
    get_llm_advisor_output_schema,
)


def build_llm_system_prompt() -> str:
    return (
        "You are DrRepo's evidence-grounded repository advisor. "
        "Use only the supplied audit evidence and profiled action plan. "
        "You are not a source-code oracle and must not invent findings, tools, tests, vulnerabilities, dependencies, or project features. "
        f"Every item in top_priorities and lower_priority_items must include title, why_it_matters, evidence, suggested_fix, and priority. "
        "If there are no urgent priorities, use an empty top_priorities list. "
        "Do not invent evidence or fixes. "
        "Prioritize advice by the selected project goal, explain what to fix first and why, what can wait, and what evidence is missing. "
        "Return JSON only."
    )


def build_llm_user_prompt(payload: dict[str, object]) -> str:
    payload_copy = deepcopy(payload) if isinstance(payload, dict) else {}
    serialized = json.dumps(payload_copy, indent=2, sort_keys=True)
    return f"Use the grounded payload below and return JSON only.\n\n```json\n{serialized}\n```"


def build_llm_prompt_bundle(
    audit: dict[str, object],
    profiled_action_plan: dict[str, object],
) -> dict[str, object]:
    payload = build_llm_advisor_payload(audit, profiled_action_plan)
    return {
        "contract_version": LLM_ADVISOR_CONTRACT_VERSION,
        "system_prompt": build_llm_system_prompt(),
        "user_prompt": build_llm_user_prompt(payload),
        "payload": payload,
        "expected_output_schema": get_llm_advisor_output_schema(),
    }