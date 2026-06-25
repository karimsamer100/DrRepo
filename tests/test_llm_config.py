from drrepo.advisor.llm_http import call_gemini_advisor, call_groq_advisor, call_cerebras_advisor
from drrepo.advisor.llm_providers import get_default_provider_order


def test_provider_order_prefers_free_tier_providers():
    assert get_default_provider_order() == ["gemini", "groq", "cerebras", "deterministic_fallback"]


def test_missing_environment_keys_return_missing_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)

    assert call_gemini_advisor({"system_prompt": "x", "user_prompt": "y"}).status == "missing_api_key"
    assert call_groq_advisor({"system_prompt": "x", "user_prompt": "y"}).status == "missing_api_key"
    assert call_cerebras_advisor({"system_prompt": "x", "user_prompt": "y"}).status == "missing_api_key"
