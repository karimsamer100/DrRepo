from pathlib import Path
import json
import subprocess

import pytest

from drrepo.audit import build_audit


def test_build_audit_on_sample_good_repo():
    p = Path("examples/sample_good_repo")
    audit = build_audit(p)
    assert audit.get("status") == "ok"
    # required top-level keys
    for key in (
        "path",
        "metadata",
        "static_analysis",
        "test_analysis",
        "repository_analysis",
        "scoring",
        "diagnosis",
        "remediation_suggestions",
        "remediation_summary",
    ):
        assert key in audit

    scoring = audit.get("scoring", {})
    assert "overall_score" in scoring or "overall" in scoring

    assert "repository_health" in audit.get("diagnosis", {})
    assert isinstance(audit.get("remediation_suggestions", []), list)


def test_build_audit_on_sample_bad_repo():
    p = Path("examples/sample_bad_repo")
    audit = build_audit(p)
    assert audit.get("status") == "ok"
    assert isinstance(audit.get("remediation_suggestions", []), list)
    assert "diagnosis" in audit

    # at least one evidence finding section or remediation suggestion exists
    findings_present = False
    for section in ("static_analysis", "test_analysis", "repository_analysis"):
        items = audit.get(section) or []
        if any(isinstance(it, dict) and it.get("findings") for it in items):
            findings_present = True
            break
    if not findings_present:
        # fallback: remediation suggestions should exist for a bad repo
        findings_present = len(audit.get("remediation_suggestions", [])) > 0

    assert findings_present


def test_build_audit_on_self_repo():
    p = Path(".")
    audit = build_audit(p)
    assert audit.get("status") == "ok"
    metadata = audit.get("metadata", {})
    # metadata should report some python files
    py_files = metadata.get("python_files") or metadata.get("num_python_files") or metadata.get("file_count")
    assert py_files is not None and int(py_files) >= 1
    assert "scoring" in audit
    assert "diagnosis" in audit


def _run_cli(args):
    # use subprocess to run the installed entry point via module
    cmd = ["python", "-m", "drrepo.cli"] + args
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    return proc


def test_cli_json_end_to_end_sample_good_repo():
    proc = _run_cli(["audit", "examples/sample_good_repo", "--format", "json"])
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert "diagnosis" in data
    assert "remediation_summary" in data


def test_cli_markdown_end_to_end_sample_good_repo():
    proc = _run_cli(["audit", "examples/sample_good_repo", "--format", "markdown"])
    assert proc.returncode == 0
    out = proc.stdout
    assert "# DrRepo Audit Report" in out
    assert "## Diagnosis" in out
    assert "## Prioritized Action Plan" in out


def test_cli_summary_end_to_end_sample_good_repo():
    proc = _run_cli(["audit", "examples/sample_good_repo", "--format", "summary"])
    assert proc.returncode == 0
    out = proc.stdout
    assert "DrRepo Audit Summary" in out
    assert "Overall score" in out
    assert "Diagnosis" in out
    assert "Suggestions:" in out


def test_cli_output_file_for_all_formats(tmp_path):
    out_json = tmp_path / "audit.json"
    out_md = tmp_path / "audit.md"
    out_txt = tmp_path / "audit.txt"

    proc = _run_cli(["audit", "examples/sample_good_repo", "--format", "json", "--output", str(out_json)])
    assert proc.returncode == 0
    assert out_json.exists()
    json.loads(out_json.read_text())

    proc = _run_cli(["audit", "examples/sample_good_repo", "--format", "markdown", "--output", str(out_md)])
    assert proc.returncode == 0
    assert out_md.exists()
    assert "# DrRepo Audit Report" in out_md.read_text()

    proc = _run_cli(["audit", "examples/sample_good_repo", "--format", "summary", "--output", str(out_txt)])
    assert proc.returncode == 0
    assert out_txt.exists()
    assert "DrRepo Audit Summary" in out_txt.read_text()


def test_generated_files_do_not_pollute_repo(tmp_path):
    # ensure files are created only under tmp_path
    out = tmp_path / "audit.json"
    proc = _run_cli(["audit", "examples/sample_good_repo", "--format", "json", "--output", str(out)])
    assert proc.returncode == 0
    # ensure no files in repo root like ./audit.json or ./reports are created
    assert not Path("./audit.json").exists()
    assert not Path("./reports").exists() or not any(Path("./reports").iterdir())
