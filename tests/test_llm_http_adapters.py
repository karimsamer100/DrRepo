from drrepo.advisor.llm_contract import validate_llm_advisor_response
from drrepo.advisor.llm_http import (
    LLM_HTTP_ADAPTER_VERSION,
    build_provider_callables_from_environment,
    call_cerebras_advisor,
    call_gemini_advisor,
    call_groq_advisor,
    call_openrouter_advisor,
    parse_llm_json_response,
)


def test_call_gemini_advisor_returns_missing_api_key_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = call_gemini_advisor({"system_prompt": "x", "user_prompt": "y"})
    assert result.status == "missing_api_key"


def test_call_groq_advisor_returns_missing_api_key_without_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = call_groq_advisor({"system_prompt": "x", "user_prompt": "y"})
    assert result.status == "missing_api_key"


def test_call_cerebras_advisor_returns_missing_api_key_without_key(monkeypatch):
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    result = call_cerebras_advisor({"system_prompt": "x", "user_prompt": "y"})
    assert result.status == "missing_api_key"


def test_call_openrouter_advisor_returns_missing_api_key_without_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    result = call_openrouter_advisor({"system_prompt": "x", "user_prompt": "y"})
    assert result.status == "missing_api_key"


def test_fake_gemini_transport_returns_ok():
    captured = {}

    def fake_transport(endpoint, headers, payload):
        captured["endpoint"] = endpoint
        captured["headers"] = headers
        captured["payload"] = payload
        return {"output_text": '{"summary": "ok", "profile_context": "ctx", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}'}

    result = call_gemini_advisor({"system_prompt": "x", "user_prompt": "y"}, api_key="abc", transport=fake_transport)
    assert result.status == "ok"
    assert result.response is not None
    assert captured["payload"]["response_format"]["mime_type"] == "application/json"
    assert captured["payload"]["response_format"]["schema"]["required"] == [
        "summary",
        "profile_context",
        "top_priorities",
        "lower_priority_items",
        "limitations",
        "next_steps",
    ]
    assert captured["payload"]["response_format"]["schema"]["properties"]["top_priorities"]["items"]["required"] == [
        "title",
        "why_it_matters",
        "evidence",
        "suggested_fix",
        "priority",
    ]
    assert captured["payload"]["response_format"]["schema"]["properties"]["lower_priority_items"]["items"]["required"] == [
        "title",
        "why_it_matters",
        "evidence",
        "suggested_fix",
        "priority",
    ]


def test_gemini_output_text_parses_to_ok():
    def fake_transport(endpoint, headers, payload):
        return {"output_text": '{"summary": "ok", "profile_context": "ctx", "top_priorities": [{"title": "Fix tests", "why_it_matters": "Confidence", "evidence": ["PYTEST-FAILED"], "suggested_fix": "Repair the tests", "priority": "high"}], "lower_priority_items": [{"title": "Improve docs", "why_it_matters": "Clarity", "evidence": ["README"], "suggested_fix": "Add usage docs", "priority": "low"}], "limitations": [], "next_steps": []}'}

    result = call_gemini_advisor({"system_prompt": "x", "user_prompt": "y"}, api_key="abc", transport=fake_transport)
    assert result.status == "ok"
    assert result.response is not None


def test_gemini_response_missing_action_item_fields_returns_clear_invalid_response():
    result = parse_llm_json_response(
        "gemini",
        '{"summary": "ok", "profile_context": "ctx", "top_priorities": [{"title": "Fix tests"}], "lower_priority_items": [{"title": "Improve docs"}], "limitations": [], "next_steps": []}',
    )

    assert result.status == "invalid_response"
    assert "top_priorities[0] missing required field: why_it_matters" in (result.safe_message or "")
    assert "lower_priority_items[0] missing required field: why_it_matters" in (result.safe_message or "")


def test_fake_openai_compatible_transport_returns_ok_for_groq():
    def fake_transport(endpoint, headers, payload):
        return {"choices": [{"message": {"content": '{"summary": "ok", "profile_context": "ctx", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}'}}]}

    result = call_groq_advisor({"system_prompt": "x", "user_prompt": "y"}, api_key="abc", transport=fake_transport)
    assert result.status == "ok"


def test_fake_openai_compatible_transport_returns_ok_for_cerebras():
    def fake_transport(endpoint, headers, payload):
        return {"choices": [{"message": {"content": '{"summary": "ok", "profile_context": "ctx", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}'}}]}

    result = call_cerebras_advisor({"system_prompt": "x", "user_prompt": "y"}, api_key="abc", transport=fake_transport)
    assert result.status == "ok"


def test_fake_openai_compatible_transport_returns_ok_for_openrouter():
    def fake_transport(endpoint, headers, payload):
        return {"choices": [{"message": {"content": '{"summary": "ok", "profile_context": "ctx", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}'}}]}

    result = call_openrouter_advisor({"system_prompt": "x", "user_prompt": "y"}, api_key="abc", transport=fake_transport)
    assert result.status == "ok"


def test_invalid_json_returns_invalid_response():
    result = parse_llm_json_response("gemini", '{bad json')
    assert result.status == "invalid_response"


def test_structurally_invalid_advisor_response_returns_invalid_response():
    result = parse_llm_json_response("gemini", '{"summary": 3}')
    assert result.status == "invalid_response"


def test_parse_llm_json_response_accepts_raw_dict_advisor_response():
    response = {"summary": "ok", "profile_context": "ctx", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}
    result = parse_llm_json_response("gemini", response)
    assert result.status == "ok"
    assert result.response == response


def test_gemini_legacy_candidates_response_parses_to_ok():
    def fake_transport(endpoint, headers, payload):
        return {"candidates": [{"content": {"parts": [{"text": '{"summary": "ok", "profile_context": "ctx", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}'}]}}]}

    result = call_gemini_advisor({"system_prompt": "x", "user_prompt": "y"}, api_key="abc", transport=fake_transport)
    assert result.status == "ok"
    assert result.response is not None


def test_gemini_wrapper_without_final_text_returns_safe_invalid_response():
    raw_response = {
        "steps": [{"state": {"done": True}}],
        "model_output": {"tokens": []},
        "content": [{"parts": [{}]}],
    }

    result = parse_llm_json_response("gemini", raw_response)
    assert result.status == "invalid_response"
    assert result.safe_message == "no final Gemini output text found"


def test_gemini_wrapper_dict_missing_advisor_fields_is_not_validated_directly():
    raw_response = {
        "steps": [{"state": {"done": True}}],
        "model_output": {"tokens": []},
        "content": [{"parts": [{}]}],
    }

    result = parse_llm_json_response("gemini", raw_response)
    assert result.status == "invalid_response"
    assert result.safe_message == "no final Gemini output text found"


def test_transport_exception_returns_error_status():
    def broken_transport(payload):
        raise RuntimeError("boom")

    result = call_gemini_advisor({"system_prompt": "x", "user_prompt": "y"}, api_key="abc", transport=broken_transport)
    assert result.status == "error"


def test_api_key_is_not_exposed_in_error():
    def broken_transport(payload):
        raise RuntimeError("abc123")

    result = call_gemini_advisor({"system_prompt": "x", "user_prompt": "y"}, api_key="abc123", transport=broken_transport)
    assert result.status == "error"
    assert "abc123" not in (result.error or "")


def test_gemini_transport_uses_x_goog_api_key_and_does_not_expose_key():
    captured = {}

    def fake_transport(endpoint, headers, payload):
        captured["endpoint"] = endpoint
        captured["headers"] = headers
        captured["payload"] = payload
        raise RuntimeError("abc123")

    result = call_gemini_advisor({"system_prompt": "x", "user_prompt": "y"}, api_key="abc123", transport=fake_transport)

    assert result.status == "error"
    assert captured["headers"]["x-goog-api-key"] == "abc123"
    assert "Authorization" not in captured["headers"]
    assert captured["endpoint"].endswith("/interactions")
    assert "abc123" not in (result.error or "")


def test_gemini_interactions_like_response_parses_to_ok():
    def fake_transport(endpoint, headers, payload):
        return {"output_text": '{"summary": "ok", "profile_context": "ctx", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []}'}

    result = call_gemini_advisor({"system_prompt": "x", "user_prompt": "y"}, api_key="abc", transport=fake_transport)

    assert result.status == "ok"
    assert result.response is not None


def test_http_status_mapping_behaves_for_auth_rate_and_provider_errors():
    class FakeHTTPError(Exception):
        def __init__(self, code, message):
            super().__init__(message)
            self.code = code
            self.reason = message

    def fake_transport(endpoint, headers, payload):
        raise FakeHTTPError(401, "Unauthorized")

    result = call_groq_advisor({"system_prompt": "x", "user_prompt": "y"}, api_key="abc", transport=fake_transport)
    assert result.status == "error"
    assert result.error_category == "auth_error"
    assert result.http_status == 401

    def fake_rate_limit_transport(endpoint, headers, payload):
        raise FakeHTTPError(429, "Rate limit")

    rate_result = call_groq_advisor({"system_prompt": "x", "user_prompt": "y"}, api_key="abc", transport=fake_rate_limit_transport)
    assert rate_result.error_category == "rate_limit"
    assert rate_result.http_status == 429

    def fake_provider_error_transport(endpoint, headers, payload):
        raise FakeHTTPError(503, "Service unavailable")

    provider_result = call_groq_advisor({"system_prompt": "x", "user_prompt": "y"}, api_key="abc", transport=fake_provider_error_transport)
    assert provider_result.error_category == "provider_error"
    assert provider_result.http_status == 503


def test_build_provider_callables_from_environment_registers_expected_providers(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    callables = build_provider_callables_from_environment()
    assert len(callables) == 4


def test_http_adapter_version_is_available():
    assert LLM_HTTP_ADAPTER_VERSION == "v1"


def test_default_transport_salvages_json_from_text_body(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"noise before {\"output_text\": \"{\\\"summary\\\": \\\"ok\\\", \\\"profile_context\\\": \\\"ctx\\\", \\\"top_priorities\\\": [], \\\"lower_priority_items\\\": [], \\\"limitations\\\": [], \\\"next_steps\\\": []}\"} noise after"

    monkeypatch.setattr("drrepo.advisor.llm_http.request.urlopen", lambda req, timeout=10: FakeResponse())

    result = call_gemini_advisor({"system_prompt": "x", "user_prompt": "y"}, api_key="abc")
    assert result.status == "ok"
