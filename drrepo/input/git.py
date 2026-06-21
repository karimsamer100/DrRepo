from __future__ import annotations

import re
from typing import Any


_HTTPS_RE = re.compile(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")
_SSH_RE = re.compile(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$")


def is_public_github_repo_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    v = value.strip()
    if not v:
        return False
    # reject credentials in URL
    if "@" in v and v.startswith("https://"):
        # looks like https://user:token@github.com/...
        return False
    # Reject obvious issue/pull/blob/tree paths by extra segments
    m = _HTTPS_RE.match(v)
    if m:
        owner, repo = m.group(1), m.group(2)
        # owner and repo must be non-empty and repo should not be like 'issues' etc.
        if owner and repo and "/" not in repo:
            return True
        return False
    # SSH form
    m2 = _SSH_RE.match(v)
    if m2:
        owner, repo = m2.group(1), m2.group(2)
        return bool(owner and repo)
    return False


def normalize_github_repo_url(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Invalid GitHub URL: not a string")
    v = value.strip()
    if not v:
        raise ValueError("Invalid GitHub URL: empty string")

    m = _HTTPS_RE.match(v)
    if m:
        owner, repo = m.group(1), m.group(2)
        repo = repo.rstrip(".git")
        return f"https://github.com/{owner}/{repo}.git"

    m2 = _SSH_RE.match(v)
    if m2:
        owner, repo = m2.group(1), m2.group(2)
        repo = repo.rstrip(".git")
        return f"https://github.com/{owner}/{repo}.git"

    raise ValueError(f"Invalid or unsupported GitHub repository URL: {value}")
