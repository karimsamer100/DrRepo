from drrepo.advisor.llm_contract import build_fallback_advisor_response
from drrepo.advisor.llm_providers import LLMProviderResult
from drrepo.advisor.llm_router import (
    LLM_ROUTER_VERSION,
    build_default_router_providers_from_environment,
    build_deterministic_provider,
    route_llm_advisor_response,
)
from drrepo.advisor.prompting import build_llm_prompt_bundle


def _synthetic_audit():
    return {
        "status": "ok",
        "scoring": {"overall_score": 88},
        "diagnosis": {"summary": "healthy"},
    }


def _synthetic_action_plan():
    return {
        "profile": {"profile_id": "student_portfolio", "display_name": "Student Portfolio"},
        "profile_fit_summary": "Student-friendly guidance.",
        "top_actions": [{"title": "Add docs", "reason": "improve clarity", "priority": "high", "user_impact": "help users"}],
        "deprioritized_actions": [],
        "limitations": [],
        "evidence_notes": [],
    }


def test_router_uses_deterministic_fallback_when_all_environment_providers_missing_keys(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    prompt_bundle = build_llm_prompt_bundle(_synthetic_audit(), _synthetic_action_plan())
    fallback = build_fallback_advisor_response(_synthetic_action_plan())
    result = route_llm_advisor_response(prompt_bundle, fallback)
    assert result["selected_provider_id"] == "deterministic_fallback"
    assert result["used_fallback"] is True


def test_router_returns_router_version_v1():
    result = route_llm_advisor_response({"system_prompt": "x", "user_prompt": "y"}, {"summary": "x", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}, providers=[lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="gemini", status="error", error="boom")])
    assert result["router_version"] == "v1"


def test_router_selects_first_valid_mock_provider_response():
    providers = [
        lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="gemini", status="ok", response={"summary": "x", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}),
        lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="groq", status="ok", response={"summary": "y", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}),
    ]
    result = route_llm_advisor_response({"system_prompt": "x", "user_prompt": "y"}, {"summary": "fallback", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}, providers=providers)
    assert result["selected_provider_id"] == "gemini"
    assert result["used_fallback"] is False


def test_router_skips_provider_with_error_status():
    providers = [lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="gemini", status="error", error="boom")]
    result = route_llm_advisor_response({"system_prompt": "x", "user_prompt": "y"}, {"summary": "fallback", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}, providers=providers)
    assert result["selected_provider_id"] == "deterministic_fallback"


def test_router_skips_provider_with_missing_api_key():
    providers = [lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="gemini", status="missing_api_key")]
    result = route_llm_advisor_response({"system_prompt": "x", "user_prompt": "y"}, {"summary": "fallback", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}, providers=providers)
    assert result["selected_provider_id"] == "deterministic_fallback"


def test_router_skips_provider_with_invalid_response():
    providers = [lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="gemini", status="invalid_response", error="bad")]
    result = route_llm_advisor_response({"system_prompt": "x", "user_prompt": "y"}, {"summary": "fallback", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}, providers=providers)
    assert result["selected_provider_id"] == "deterministic_fallback"


def test_router_uses_deterministic_fallback_when_all_providers_fail():
    providers = [lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="gemini", status="error", error="boom")]
    result = route_llm_advisor_response({"system_prompt": "x", "user_prompt": "y"}, {"summary": "fallback", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}, providers=providers)
    assert result["selected_provider_id"] == "deterministic_fallback"


def test_provider_attempts_records_each_attempt():
    providers = [
        lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="gemini", status="error", error="boom"),
        lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="groq", status="missing_api_key"),
    ]
    result = route_llm_advisor_response({"system_prompt": "x", "user_prompt": "y"}, {"summary": "fallback", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}, providers=providers)
    assert [attempt["provider_id"] for attempt in result["provider_attempts"]] == ["gemini", "groq", "deterministic_fallback"]


def test_invalid_provider_order_raises_value_error():
    try:
        route_llm_advisor_response({"system_prompt": "x", "user_prompt": "y"}, {"summary": "fallback", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}, provider_order=["unknown"])
    except ValueError:
        return
    assert False


def test_router_does_not_mutate_prompt_bundle_or_fallback_response():
    prompt_bundle = {"system_prompt": "x", "user_prompt": "y"}
    fallback_response = {"summary": "fallback", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}
    original_prompt = dict(prompt_bundle)
    original_fallback = dict(fallback_response)
    route_llm_advisor_response(prompt_bundle, fallback_response, providers=[lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="gemini", status="ok", response={"summary": "ok", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []})])
    assert prompt_bundle == original_prompt
    assert fallback_response == original_fallback


def test_deterministic_provider_returns_valid_llm_provider_result():
    provider = build_deterministic_provider({"summary": "fallback", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []})
    result = provider({"system_prompt": "x", "user_prompt": "y"}, {"summary": "fallback", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []})
    assert result.status == "ok"
    assert result.provider_id == "deterministic_fallback"


def test_selected_advisor_response_validates_with_contract():
    result = route_llm_advisor_response({"system_prompt": "x", "user_prompt": "y"}, {"summary": "fallback", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}, providers=[lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="gemini", status="ok", response={"summary": "ok", "profile_context": "p", "top_priorities": [{"title": "Fix tests", "why_it_matters": "Confidence", "evidence": ["PYTEST-FAILED"], "suggested_fix": "Repair the tests", "priority": "high"}], "lower_priority_items": [], "limitations": [], "next_steps": []})])
    assert result["advisor_response"]["summary"] == "ok"


def test_used_fallback_is_false_when_mock_external_provider_succeeds():
    result = route_llm_advisor_response({"system_prompt": "x", "user_prompt": "y"}, {"summary": "fallback", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}, providers=[lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="gemini", status="ok", response={"summary": "ok", "profile_context": "p", "top_priorities": [{"title": "Fix tests", "why_it_matters": "Confidence", "evidence": ["PYTEST-FAILED"], "suggested_fix": "Repair the tests", "priority": "high"}], "lower_priority_items": [], "limitations": [], "next_steps": []})])
    assert result["used_fallback"] is False


def test_router_falls_back_when_provider_missing_action_item_fields():
    result = route_llm_advisor_response(
        {"system_prompt": "x", "user_prompt": "y"},
        {"summary": "fallback", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []},
        providers=[lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="gemini", status="ok", response={"summary": "ok", "profile_context": "p", "top_priorities": [{"title": "Fix tests"}], "lower_priority_items": [{"title": "Improve docs"}], "limitations": [], "next_steps": []})],
    )

    assert result["selected_provider_id"] == "deterministic_fallback"
    assert result["used_fallback"] is True


def test_used_fallback_is_true_when_deterministic_fallback_is_selected():
    result = route_llm_advisor_response({"system_prompt": "x", "user_prompt": "y"}, {"summary": "fallback", "profile_context": "p", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}, providers=[lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="gemini", status="error", error="boom")])
    assert result["used_fallback"] is True


def test_default_router_providers_from_environment_returns_callables():
    providers = build_default_router_providers_from_environment()
    assert len(providers) == 4
