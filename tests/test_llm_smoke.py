from drrepo.advisor.llm_smoke import _sanitize_error_category, run_llm_smoke_test


def test_sanitize_error_category_uses_safe_labels(monkeypatch):
    assert _sanitize_error_category("missing_api_key", None) == "missing_api_key"
    assert _sanitize_error_category("error", "401 unauthorized") == "auth_or_rate_limit"
    assert _sanitize_error_category("error", "timed out") == "timeout"


def test_run_llm_smoke_test_reports_results_without_real_calls(monkeypatch):
    class FakeResult:
        def __init__(self, status, error=None):
            self.status = status
            self.error = error

    def fake_gemini(prompt_bundle):
        return FakeResult("ok")

    def fake_groq(prompt_bundle):
        return FakeResult("missing_api_key")

    def fake_cerebras(prompt_bundle):
        return FakeResult("error", "timed out")

    monkeypatch.setattr("drrepo.advisor.llm_smoke.call_gemini_advisor", fake_gemini)
    monkeypatch.setattr("drrepo.advisor.llm_smoke.call_groq_advisor", fake_groq)
    monkeypatch.setattr("drrepo.advisor.llm_smoke.call_cerebras_advisor", fake_cerebras)

    result = run_llm_smoke_test()
    assert result["succeeded"] == ["gemini"]
    assert result["failed"] == ["groq", "cerebras"]
    assert result["fallback_used"] is False
    assert result["provider_results"][0]["status"] == "ok"
