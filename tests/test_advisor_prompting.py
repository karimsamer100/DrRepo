from copy import deepcopy

from drrepo.advisor.llm_contract import build_llm_advisor_payload
from drrepo.advisor.prompting import (
    build_llm_prompt_bundle,
    build_llm_system_prompt,
    build_llm_user_prompt,
)
from tests.test_llm_contract import _sample_audit, _sample_plan


def test_system_prompt_mentions_evidence_grounded_behavior():
    prompt = build_llm_system_prompt()
    assert "evidence-grounded" in prompt


def test_system_prompt_says_not_to_invent_findings():
    prompt = build_llm_system_prompt()
    assert "must not invent findings" in prompt


def test_system_prompt_requires_json_only_output():
    prompt = build_llm_system_prompt()
    assert "Return JSON only" in prompt


def test_user_prompt_includes_serialized_payload():
    payload = build_llm_advisor_payload(_sample_audit(), _sample_plan())
    prompt = build_llm_user_prompt(payload)
    assert '```json' in prompt
    assert '"contract_version": "v1"' in prompt


def test_user_prompt_includes_contract_version():
    payload = build_llm_advisor_payload(_sample_audit(), _sample_plan())
    prompt = build_llm_user_prompt(payload)
    assert '"contract_version": "v1"' in prompt


def test_prompt_bundle_includes_required_fields():
    bundle = build_llm_prompt_bundle(_sample_audit(), _sample_plan())
    assert set(bundle.keys()) == {"contract_version", "system_prompt", "user_prompt", "payload", "expected_output_schema"}


def test_prompt_bundle_does_not_mutate_inputs():
    audit = _sample_audit()
    plan = _sample_plan()
    audit_before = deepcopy(audit)
    plan_before = deepcopy(plan)
    _ = build_llm_prompt_bundle(audit, plan)
    assert audit == audit_before
    assert plan == plan_before


def test_prompt_bundle_uses_same_payload_as_build_llm_advisor_payload():
    audit = _sample_audit()
    plan = _sample_plan()
    bundle = build_llm_prompt_bundle(audit, plan)
    assert bundle["payload"] == build_llm_advisor_payload(audit, plan)


def test_prompt_bundle_has_contract_version_v1():
    bundle = build_llm_prompt_bundle(_sample_audit(), _sample_plan())
    assert bundle["contract_version"] == "v1"