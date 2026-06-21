import pytest

from drrepo.input.git import (
    is_public_github_repo_url,
    normalize_github_repo_url,
)


def test_accepts_https():
    assert is_public_github_repo_url("https://github.com/owner/repo")


def test_accepts_https_trailing_slash():
    assert is_public_github_repo_url("https://github.com/owner/repo/")


def test_accepts_https_dotgit():
    assert is_public_github_repo_url("https://github.com/owner/repo.git")


def test_accepts_ssh():
    assert is_public_github_repo_url("git@github.com:owner/repo.git")


def test_rejects_owner_only():
    assert not is_public_github_repo_url("https://github.com/owner")


def test_rejects_issue_url():
    assert not is_public_github_repo_url("https://github.com/owner/repo/issues/1")


def test_rejects_non_github():
    assert not is_public_github_repo_url("https://gitlab.com/owner/repo")


def test_normalize_https():
    assert normalize_github_repo_url("https://github.com/owner/repo") == "https://github.com/owner/repo.git"


def test_normalize_ssh():
    assert normalize_github_repo_url("git@github.com:owner/repo.git") == "https://github.com/owner/repo.git"


def test_normalize_invalid_raises():
    with pytest.raises(ValueError):
        normalize_github_repo_url("https://github.com/owner/repo/issues/1")
