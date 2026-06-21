from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from .git import normalize_github_repo_url, is_public_github_repo_url


def create_temp_workspace(prefix: str = "drrepo-") -> Path:
    d = tempfile.mkdtemp(prefix=prefix)
    return Path(d)


def _is_safe_to_delete(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except Exception:
        return False
    # refuse root drives
    if resolved == Path(resolved.anchor):
        return False
    # refuse home or cwd
    from pathlib import Path as _P

    if resolved == _P.cwd() or resolved == _P.home():
        return False
    # refuse paths shorter than tempdir base
    import tempfile as _tmp

    if len(str(resolved)) < len(str(_tmp.gettempdir())):
        return False
    return True


def cleanup_workspace(path: Path) -> None:
    if not isinstance(path, Path):
        path = Path(path)
    if not path.exists():
        return
    if not _is_safe_to_delete(path):
        raise ValueError(f"Refusing to delete unsafe path: {path}")
    shutil.rmtree(path)


def clone_public_github_repo(url: str, workspace: Path, timeout_seconds: int = 60) -> Path:
    if not is_public_github_repo_url(url):
        raise ValueError("URL is not a recognized public GitHub repository URL")
    norm = normalize_github_repo_url(url)
    target = Path(workspace) / "repo"
    if target.exists():
        raise FileExistsError(f"Target path already exists: {target}")

    cmd = ["git", "clone", "--depth", "1", norm, str(target)]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_seconds)
    except FileNotFoundError:
        raise RuntimeError("git executable not found; ensure git is installed and on PATH")
    except subprocess.TimeoutExpired:
        raise RuntimeError("git clone timed out")

    if proc.returncode != 0:
        msg = proc.stderr.strip() or proc.stdout.strip() or "git clone failed"
        raise RuntimeError(f"git clone failed: {msg}")

    return target
