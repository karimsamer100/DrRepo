import pytest

from drrepo.advisor.llm_providers import (
    LLM_PROVIDER_INTERFACE_VERSION,
    LLMProviderResult,
    build_provider_metadata,
    get_default_provider_order,
    get_supported_provider_ids,
    validate_provider_id,
)


def test_default_provider_order_is_expected():
    assert get_default_provider_order() == [
        "gemini",
        "groq",
        "cerebras",
        "deterministic_fallback",
    ]


def test_supported_provider_ids_include_core_ids():
    supported = set(get_supported_provider_ids())
    assert {"gemini", "groq", "cerebras", "deterministic_fallback"} <= supported


def test_validate_provider_id_accepts_known_ids():
    for provider_id in get_supported_provider_ids():
        validate_provider_id(provider_id)


def test_validate_provider_id_rejects_unknown_ids():
    with pytest.raises(ValueError):
        validate_provider_id("unknown_provider")


def test_build_provider_metadata_returns_provider_id_and_model():
    metadata = build_provider_metadata("gemini")
    assert metadata["provider_id"] == "gemini"
    assert metadata["model"] == "gemini-2.5-flash"


def test_deterministic_fallback_metadata_has_deterministic_role():
    metadata = build_provider_metadata("deterministic_fallback")
    assert metadata["role"] == "deterministic_fallback"


def test_external_provider_metadata_includes_api_key_environment():
    metadata = build_provider_metadata("groq")
    assert metadata["api_key_env"] == "GROQ_API_KEY"


def test_llm_provider_result_stores_status_response_and_error():
    result = LLMProviderResult(
        provider_id="gemini",
        status="ok",
        response={"summary": "ok"},
        error=None,
    )
    assert result.provider_id == "gemini"
    assert result.status == "ok"
    assert result.response == {"summary": "ok"}
    assert result.error is None


def test_interface_version_is_available():
    assert LLM_PROVIDER_INTERFACE_VERSION == "v1"
