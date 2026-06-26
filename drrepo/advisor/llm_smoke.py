from __future__ import annotations

from typing import Any

from drrepo.config import load_repo_dotenv

from .llm_http import call_cerebras_advisor, call_gemini_advisor, call_groq_advisor
from .llm_providers import build_provider_metadata

SMOKE_PROMPT = "Reply with exactly: DRREPO_LLM_OK"


def _load_smoke_environment() -> None:
    load_repo_dotenv()


def _build_prompt_bundle() -> dict[str, object]:
    return {
        "system_prompt": "You are a concise DrRepo advisor helper.",
        "user_prompt": SMOKE_PROMPT,
    }


def _sanitize_error_category(status: str, error: str | None) -> str:
    if status == "missing_api_key":
        return "missing_api_key"
    if status == "invalid_response":
        return "invalid_response"
    if status == "error":
        if error is None:
            return "provider_error"
        lowered = error.lower()
        if "401" in lowered or "403" in lowered or "unauthorized" in lowered or "forbidden" in lowered:
            return "auth_error"
        if "429" in lowered or "rate limit" in lowered or "too many requests" in lowered:
            return "rate_limit"
        if "timeout" in lowered or "timed out" in lowered or "network" in lowered:
            return "network_error"
        return "provider_error"
    return status


def run_llm_smoke_test() -> dict[str, Any]:
    _load_smoke_environment()
    prompt_bundle = _build_prompt_bundle()
    provider_callables = [
        ("gemini", call_gemini_advisor),
        ("groq", call_groq_advisor),
        ("cerebras", call_cerebras_advisor),
    ]

    results: list[dict[str, Any]] = []
    for provider_id, provider_callable in provider_callables:
        metadata = build_provider_metadata(provider_id)
        result = provider_callable(prompt_bundle)
        results.append(
            {
                "provider_id": provider_id,
                "provider_name": metadata["display_name"],
                "model": metadata["model"],
                "status": result.status,
                "success": result.status == "ok",
                "error_category": _sanitize_error_category(result.status, result.error),
            }
        )

    succeeded = [entry for entry in results if entry["success"]]
    fallback_used = not succeeded
    return {
        "prompt": SMOKE_PROMPT,
        "provider_results": results,
        "succeeded": [entry["provider_id"] for entry in succeeded],
        "failed": [entry["provider_id"] for entry in results if not entry["success"]],
        "fallback_used": fallback_used,
    }


def print_smoke_summary(result: dict[str, Any]) -> None:
    print("DrRepo LLM smoke test")
    print(f"Prompt: {result['prompt']}")
    print("Provider | Model | Status | Error")
    for entry in result["provider_results"]:
        error = entry["error_category"] if not entry["success"] else "-"
        print(f"{entry['provider_name']} | {entry['model']} | {'ok' if entry['success'] else 'failed'} | {error}")

    if result["fallback_used"]:
        print("Fallback: AI advice is temporarily unavailable; deterministic fallback is being used.")
    else:
        print("Fallback: not needed; at least one provider responded successfully.")


def main() -> None:
    result = run_llm_smoke_test()
    print_smoke_summary(result)


if __name__ == "__main__":
    main()
