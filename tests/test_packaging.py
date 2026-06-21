import pathlib
import tomllib


def _load_pyproject():
    path = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
    content = path.read_text(encoding="utf-8")
    return tomllib.loads(content)


def test_pyproject_toml_loads():
    data = _load_pyproject()
    assert isinstance(data, dict)


def test_project_metadata_exists():
    data = _load_pyproject()
    project = data.get("project")
    assert project is not None
    assert project.get("name") == "drrepo"
    assert "requires-python" in project


def test_console_script_exists():
    data = _load_pyproject()
    project = data.get("project", {})
    scripts = project.get("scripts", {})
    assert scripts.get("drrepo") == "drrepo.cli:app"


def test_typer_in_runtime_dependencies():
    data = _load_pyproject()
    project = data.get("project", {})
    deps = project.get("dependencies", []) or []
    assert any(d.startswith("typer") for d in deps)


def test_optional_dev_dependencies_include_tools():
    data = _load_pyproject()
    project = data.get("project", {})
    optional = project.get("optional-dependencies", {}) or {}
    dev = optional.get("dev", []) or []
    required_tools = ["pytest", "ruff", "bandit", "radon", "coverage"]
    for tool in required_tools:
        assert any(d.startswith(tool) for d in dev), f"{tool} missing from dev optional-dependencies"


def test_tools_not_runtime_dependencies_unless_intended():
    data = _load_pyproject()
    project = data.get("project", {})
    deps = project.get("dependencies", []) or []
    dev_tools = ["ruff", "bandit", "radon", "coverage"]
    for tool in dev_tools:
        assert not any(d.startswith(tool) for d in deps)
