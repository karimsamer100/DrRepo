from drrepo.advisor.llm_smoke import SMOKE_PROMPT, SMOKE_PROMPT_DISPLAY, _sanitize_error_category, print_smoke_summary, run_llm_smoke_test


def test_sanitize_error_category_uses_safe_labels(monkeypatch):
    assert _sanitize_error_category("missing_api_key", None) == "missing_api_key"
    assert _sanitize_error_category("error", "401 unauthorized") == "auth_error"
    assert _sanitize_error_category("error", "429 rate limit") == "rate_limit"
    assert _sanitize_error_category("error", "timed out") == "network_error"
    assert _sanitize_error_category("error", "provider exploded") == "provider_error"


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
    assert SMOKE_PROMPT_DISPLAY in result["prompt"]


def test_smoke_prompt_mentions_advisor_json_contract():
    assert "advisor response contract" in SMOKE_PROMPT.lower()
    assert "summary" in SMOKE_PROMPT
    assert "top_priorities" in SMOKE_PROMPT


def test_print_smoke_summary_includes_safe_diagnostics(capsys):
    result = {
        "prompt": "test",
        "provider_results": [
            {
                "provider_name": "Google Gemini",
                "model": "gemini-2.5-flash",
                "status": "failed",
                "error_category": "auth_error",
                "http_status": 403,
                "safe_message": "API key not valid",
            }
        ],
        "fallback_used": True,
    }

    print_smoke_summary(result)
    output = capsys.readouterr().out
    assert "Error category" in output
    assert "auth_error" in output
    assert "403" in output
    assert "API key not valid" in output
