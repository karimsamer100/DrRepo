from __future__ import annotations

from typing import Any, Dict, List

PROFILE_VERSION = "v1"

_SUPPORTED_PROFILES = {
    "student_portfolio": {
        "profile_version": PROFILE_VERSION,
        "profile_id": "student_portfolio",
        "display_name": "Student Portfolio",
        "description": "Best for student projects where clarity, presentation, and basic trust signals matter most.",
        "primary_user_goal": "Show a credible, understandable project with clear documentation and basic reliability.",
        "high_priority_categories": ["documentation", "presentation", "reproducibility", "basic_testing", "structure"],
        "medium_priority_categories": ["maintainability", "security", "ci_cd"],
        "lower_priority_categories": ["advanced_security_hardening", "deployment_readiness"],
        "always_high_priority_flags": ["failing_tests", "high_security_risk"],
        "deprioritize_when_low_risk": ["advanced_security_hardening", "deployment_readiness", "optional_tooling"],
        "advisor_tone": "Practical and encouraging, focused on visible progress and trustworthy basics.",
    },
    "open_source_library": {
        "profile_version": PROFILE_VERSION,
        "profile_id": "open_source_library",
        "display_name": "Open Source Library",
        "description": "Best for reusable libraries that need strong docs, tests, and packaging signals.",
        "primary_user_goal": "Make the project easy for others to discover, install, use, and contribute to.",
        "high_priority_categories": ["documentation", "tests", "packaging", "ci_cd", "maintainability"],
        "medium_priority_categories": ["security", "structure"],
        "lower_priority_categories": ["deployment_readiness"],
        "always_high_priority_flags": ["failing_tests", "high_security_risk"],
        "deprioritize_when_low_risk": ["deployment_readiness", "advanced_security_hardening"],
        "advisor_tone": "Supportive and community-focused, emphasizing usability and contribution readiness.",
    },
    "production_service": {
        "profile_version": PROFILE_VERSION,
        "profile_id": "production_service",
        "display_name": "Production Service",
        "description": "Best for systems that must be safe, tested, and deployment-ready.",
        "primary_user_goal": "Reduce operational risk and make the service safe enough to run with real users or data.",
        "high_priority_categories": ["security", "tests", "coverage", "ci_cd", "deployment_readiness", "environment_configuration", "maintainability"],
        "medium_priority_categories": ["documentation", "structure"],
        "lower_priority_categories": ["presentation"],
        "always_high_priority_flags": ["failing_tests", "high_security_risk", "exposed_secrets"],
        "deprioritize_when_low_risk": ["presentation", "optional_tooling"],
        "advisor_tone": "Direct and risk-focused, emphasizing reliability and operational safety.",
    },
    "learning_or_research_project": {
        "profile_version": PROFILE_VERSION,
        "profile_id": "learning_or_research_project",
        "display_name": "Learning or Research Project",
        "description": "Best for experiments, coursework, or research artifacts where clarity and reproducibility matter most.",
        "primary_user_goal": "Make the project understandable, reproducible, and easy to run or explain.",
        "high_priority_categories": ["clarity", "reproducibility", "documentation", "dependencies", "basic_testing"],
        "medium_priority_categories": ["structure", "maintainability"],
        "lower_priority_categories": ["advanced_security_hardening", "deployment_readiness"],
        "always_high_priority_flags": ["failing_tests", "high_security_risk"],
        "deprioritize_when_low_risk": ["advanced_security_hardening", "deployment_readiness", "optional_tooling"],
        "advisor_tone": "Clear and explanatory, focused on making the work understandable and repeatable.",
    },
}


def get_supported_profile_ids() -> List[str]:
    return list(_SUPPORTED_PROFILES.keys())


def validate_profile_id(profile_id: str) -> None:
    if profile_id not in _SUPPORTED_PROFILES:
        raise ValueError("unsupported profile_id")


def get_profile(profile_id: str) -> Dict[str, Any]:
    validate_profile_id(profile_id)
    return dict(_SUPPORTED_PROFILES[profile_id])


def list_profiles() -> List[Dict[str, Any]]:
    return [dict(_SUPPORTED_PROFILES[k]) for k in sorted(_SUPPORTED_PROFILES)]
