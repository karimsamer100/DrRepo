from __future__ import annotations

import json
import pytest

from drrepo.analyzers.models import (
    ToolFinding,
    ToolResult,
    tool_finding_to_dict,
    tool_result_to_dict,
    allowed_statuses,
)


def test_completed_tool_result_to_dict():
    r = ToolResult(tool="dummy", status="completed")
    d = tool_result_to_dict(r)
    assert d["tool"] == "dummy"
    assert d["status"] == "completed"
    assert d["findings"] == []


def test_tool_finding_to_dict():
    f = ToolFinding(
        tool="dummy",
        message="issue",
        file_path="a.py",
        line=5,
        column=2,
        severity="error",
        code="E1",
    )
    fd = tool_finding_to_dict(f)
    assert fd["tool"] == "dummy"
    assert fd["file_path"] == "a.py"
    assert fd["line"] == 5


def test_invalid_tool_result_status():
    with pytest.raises(ValueError):
        ToolResult(tool="x", status="not-a-status")


def test_tool_finding_invalid_line():
    with pytest.raises(ValueError):
        ToolFinding(tool="t", message="m", line=0)


def test_tool_result_with_findings_to_dict():
    f = ToolFinding(tool="t", message="m", file_path="x.py", line=1)
    r = ToolResult(tool="t", status="completed", findings=[f])
    d = tool_result_to_dict(r)
    assert isinstance(d["findings"], list)
    assert d["findings"][0]["file_path"] == "x.py"


def test_json_serialization():
    f = ToolFinding(tool="t", message="m", file_path="x.py", line=1)
    r = ToolResult(tool="t", status="completed", findings=[f])
    d = tool_result_to_dict(r)
    s = json.dumps(d)
    assert isinstance(s, str)
