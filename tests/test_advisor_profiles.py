import pytest

from drrepo.advisor.profiles import (
    PROFILE_VERSION,
    get_supported_profile_ids,
    get_profile,
    list_profiles,
    validate_profile_id,
)


def test_supported_profile_ids_include_student_portfolio():
    ids = get_supported_profile_ids()
    assert "student_portfolio" in ids


def test_get_profile_returns_profile_version_v1():
    profile = get_profile("student_portfolio")
    assert profile["profile_version"] == PROFILE_VERSION


def test_get_profile_rejects_unknown_profile_ids():
    with pytest.raises(ValueError):
        get_profile("unknown_profile")


def test_list_profiles_returns_all_supported_profiles():
    profiles = list_profiles()
    assert len(profiles) == 4


def test_each_profile_has_primary_user_goal():
    for profile_id in get_supported_profile_ids():
        profile = get_profile(profile_id)
        assert profile["primary_user_goal"]


def test_student_portfolio_prioritizes_documentation_presentation_reproducibility_and_testing():
    profile = get_profile("student_portfolio")
    for key in ["documentation", "presentation", "reproducibility", "basic_testing", "structure"]:
        assert key in profile["high_priority_categories"]


def test_production_service_prioritizes_security_tests_and_deployment_readiness():
    profile = get_profile("production_service")
    for key in ["security", "tests", "coverage", "ci_cd", "deployment_readiness", "environment_configuration", "maintainability"]:
        assert key in profile["high_priority_categories"]
