from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

from drrepo.advisor.profiles import get_profile, validate_profile_id
from drrepo.intelligence.models import (
    ArchitectureSummary,
    EntryPoint,
    EvidenceItem,
    ExecutiveReport,
    ProjectIdentity,
    ProjectUnderstanding,
    Runnability,
    StructuredRecommendation,
    to_plain_dict,
)

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
}

SIGNAL_EXCLUDED_DIRS = {"tests", "test", "docs", "examples", "fixtures"}
APP_DIR_NAMES = {"app", "api", "backend", "server", "service"}
FRONTEND_DIR_NAMES = {"frontend", "web", "client", "ui"}


def build_repository_intelligence(audit: dict[str, Any], *, profile_id: str = "student_portfolio") -> dict[str, Any]:
    """Build deterministic project understanding and executive reporting.

    The implementation is intentionally read-only: it parses metadata and source
    text but never imports project modules or executes target repository code.
    """
    validate_profile_id(profile_id)
    root = Path(str(audit.get("path", ".")))
    understanding = ProjectUnderstandingBuilder(root, audit).build()
    recommendations = build_structured_recommendations(audit, understanding, profile_id=profile_id)
    executive_report = build_executive_report(audit, understanding, recommendations, profile_id=profile_id)
    return {
        "project_understanding": to_plain_dict(understanding),
        "executive_report": to_plain_dict(executive_report),
        "recommendations_v2": [to_plain_dict(item) for item in recommendations],
    }


class ProjectUnderstandingBuilder:
    def __init__(self, root: Path, audit: dict[str, Any]):
        self.root = root
        self.audit = audit
        self.metadata = audit.get("metadata") if isinstance(audit.get("metadata"), dict) else {}
        self.package_json_path: Path | None = None

    def build(self) -> ProjectUnderstanding:
        pyproject = self._read_pyproject()
        package_json = self._read_package_json()
        python_files = self._python_files(limit=250)
        signal_files = [path for path in python_files if self._is_signal_file(path)]
        text_cache = {path: self._read_text(path) for path in python_files[:160]}
        signal_text_cache = {path: self._read_text(path) for path in signal_files[:160]}
        evidence: list[EvidenceItem] = []

        frameworks = self._detect_frameworks(signal_text_cache, pyproject, evidence)
        interfaces = self._detect_interfaces(pyproject, package_json, signal_text_cache, evidence)
        architecture = self._build_architecture_summary(signal_text_cache, package_json)
        package_layout = self._detect_package_layout(pyproject, architecture)
        entry_points = self._detect_entry_points(pyproject, package_json, signal_text_cache)
        project_types = self._detect_project_types(frameworks, interfaces, architecture, entry_points, signal_text_cache, package_json)
        primary_type = project_types[0] if project_types else "unknown/mixed project"
        secondary_types = project_types[1:]
        domain_specializations = [item for item in secondary_types if item in {"ML training project", "ML inference/service project", "RAG/LLM application", "data-science/notebook project"}]
        confidence = self._confidence(evidence, high=4, medium=2)

        identity = ProjectIdentity(
            primary_language="Python" if self.metadata.get("python_files", 0) else "unknown",
            project_type=primary_type,
            secondary_project_types=secondary_types,
            architecture_type=primary_type if primary_type in {"backend + frontend application", "FastAPI API", "Flask application", "Django application", "CLI tool", "Python library/package", "automation/script repository"} else None,
            domain_specializations=domain_specializations,
            frameworks=frameworks,
            interfaces=interfaces,
            package_layout=package_layout,
            confidence=confidence,
            evidence=evidence[:12],
        )
        runnability = self._build_runnability(pyproject, package_json, entry_points)
        return ProjectUnderstanding(
            project_identity=identity,
            entry_points=entry_points,
            runnability=runnability,
            architecture_summary=architecture,
        )

    def _read_pyproject(self) -> dict[str, Any]:
        path = self.root / "pyproject.toml"
        if not path.exists():
            return {}
        try:
            return tomllib.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _read_package_json(self) -> dict[str, Any]:
        candidates = [self.root / "package.json", *[self.root / name / "package.json" for name in sorted(FRONTEND_DIR_NAMES)]]
        for path in candidates:
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(data, dict):
                self.package_json_path = path
                return data
        return {}

    def _package_json_rel(self) -> str:
        return self._rel(self.package_json_path) if self.package_json_path else "package.json"

    def _python_files(self, *, limit: int) -> list[Path]:
        files: list[Path] = []
        for path in self.root.rglob("*.py"):
            if self._ignored(path):
                continue
            files.append(path)
            if len(files) >= limit:
                break
        return sorted(files)

    def _ignored(self, path: Path) -> bool:
        try:
            rel = path.relative_to(self.root)
        except Exception:
            return True
        return any(part in IGNORED_DIRS for part in rel.parts)

    def _is_signal_file(self, path: Path) -> bool:
        try:
            rel = path.relative_to(self.root)
        except Exception:
            return False
        if len(rel.parts) >= 3 and rel.parts[0] == "drrepo" and rel.parts[1] in {"intelligence", "readiness", "analyzers"}:
            return False
        return not any(part in SIGNAL_EXCLUDED_DIRS for part in rel.parts)

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    def _rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root)).replace("\\", "/")
        except Exception:
            return str(path)

    def _add_evidence(self, evidence: list[EvidenceItem], path: str, reason: str, detail: str | None = None) -> None:
        item = EvidenceItem(path=path, reason=reason, detail=detail)
        if item not in evidence:
            evidence.append(item)

    def _detect_frameworks(self, text_cache: dict[Path, str], pyproject: dict[str, Any], evidence: list[EvidenceItem]) -> list[str]:
        frameworks: list[str] = []
        checks = [
            ("FastAPI", [r"\bfrom\s+fastapi\b", r"\bimport\s+fastapi\b", r"FastAPI\s*\("]),
            ("Flask", [r"\bfrom\s+flask\b", r"\bimport\s+flask\b", r"Flask\s*\("]),
            ("Django", [r"\bimport\s+django\b", r"DJANGO_SETTINGS_MODULE", r"django\."]),
            ("Streamlit", [r"\bimport\s+streamlit\b", r"\bstreamlit\s+run\b"]),
            ("Gradio", [r"\bimport\s+gradio\b", r"\.launch\s*\("]),
            ("LangChain", [r"\blangchain\b"]),
            ("LlamaIndex", [r"\bllama_index\b", r"\bllamaindex\b"]),
            ("scikit-learn", [r"\bsklearn\b"]),
            ("PyTorch", [r"\btorch\b"]),
            ("TensorFlow", [r"\btensorflow\b", r"\bkeras\b"]),
        ]
        dependency_text = json.dumps(pyproject).lower()
        for label, patterns in checks:
            found = False
            for path, text in text_cache.items():
                if any(re.search(pattern, text) for pattern in patterns):
                    self._add_evidence(evidence, self._rel(path), f"{label} signal", "source import or object")
                    found = True
                    break
            if not found and label in {"FastAPI", "Flask", "Django", "Streamlit", "Gradio"} and label.lower() in dependency_text:
                self._add_evidence(evidence, "pyproject.toml", f"{label} dependency", None)
                found = True
            if found:
                frameworks.append(label)
        return frameworks

    def _detect_interfaces(self, pyproject: dict[str, Any], package_json: dict[str, Any], text_cache: dict[Path, str], evidence: list[EvidenceItem]) -> list[str]:
        interfaces: list[str] = []
        scripts = pyproject.get("project", {}).get("scripts", {}) if isinstance(pyproject.get("project"), dict) else {}
        if scripts:
            interfaces.append("CLI")
            self._add_evidence(evidence, "pyproject.toml", "console script entry points", ", ".join(sorted(scripts)))
        if package_json:
            interfaces.append("web frontend")
            self._add_evidence(evidence, self._package_json_rel(), "frontend package metadata", None)
        if any(_has_api_signal(text) for text in text_cache.values()) or any(framework in json.dumps(pyproject).lower() for framework in ("fastapi", "flask", "django")):
            interfaces.append("API")
            self._add_evidence(evidence, "source", "API framework or application object", None)
        for path, text in text_cache.items():
            if re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]", text):
                interfaces.append("script")
                self._add_evidence(evidence, self._rel(path), "Python main guard", None)
                break
        return sorted(set(interfaces))

    def _detect_package_layout(self, pyproject: dict[str, Any], architecture: ArchitectureSummary) -> str:
        source_roots = self.metadata.get("source_roots") or []
        top_dirs = set(self.metadata.get("top_level_directories") or [])
        if architecture.backend_present and architecture.frontend_present:
            return "backend/frontend layout"
        if "src" in source_roots or (self.root / "src").is_dir():
            return "src layout"
        project_name = pyproject.get("project", {}).get("name") if isinstance(pyproject.get("project"), dict) else None
        if project_name and (self.root / str(project_name).replace("-", "_")).is_dir():
            return "package directory"
        package_dirs = [
            name for name in top_dirs
            if name not in SIGNAL_EXCLUDED_DIRS and name not in FRONTEND_DIR_NAMES and (self.root / name / "__init__.py").exists()
        ]
        if package_dirs:
            return "package directory"
        if source_roots:
            roots_without_dot = [root for root in source_roots if root != "."]
            if roots_without_dot:
                return "package directory"
            return "flat scripts"
        return "unknown"

    def _build_architecture_summary(self, text_cache: dict[Path, str], package_json: dict[str, Any]) -> ArchitectureSummary:
        dirs = set(self.metadata.get("top_level_directories") or [])
        files = set(self.metadata.get("top_level_files") or [])
        joined = "\n".join(text_cache.values()).lower()
        database_signals = [sig for sig in ("sqlalchemy", "sqlite", "postgres", "mysql", "mongodb") if sig in joined]
        container_signals = [name for name in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml") if (self.root / name).exists()]
        ci_signals = []
        if (self.root / ".github" / "workflows").is_dir():
            ci_signals.append(".github/workflows")
        if ".gitlab-ci.yml" in files:
            ci_signals.append(".gitlab-ci.yml")
        api_present = any(_has_api_signal(text) for text in text_cache.values())
        backend_present = bool(self.metadata.get("python_files", 0)) and (api_present or bool(APP_DIR_NAMES & dirs) or any((self.root / name).is_dir() for name in APP_DIR_NAMES))
        return ArchitectureSummary(
            backend_present=backend_present or bool(self.metadata.get("python_files", 0)),
            frontend_present=bool(package_json and ((self.root / "frontend").is_dir() or (self.root / "src").is_dir() or "vite" in json.dumps(package_json).lower()) or bool(FRONTEND_DIR_NAMES & dirs)),
            cli_present="cli" in joined or bool(self._console_scripts(self._read_pyproject())),
            api_present=api_present,
            ml_present=_has_strong_ml_signal(joined, dirs),
            notebooks_present=any(not self._ignored(path) for path in self.root.rglob("*.ipynb")),
            database_signals=database_signals,
            container_signals=container_signals,
            ci_signals=ci_signals,
            important_directories=sorted(dirs & {"src", "tests", "docs", "frontend", "backend", "app", "api", "notebooks", "models", "data"}),
        )

    def _console_scripts(self, pyproject: dict[str, Any]) -> dict[str, Any]:
        project = pyproject.get("project") if isinstance(pyproject.get("project"), dict) else {}
        scripts = project.get("scripts") if isinstance(project.get("scripts"), dict) else {}
        return scripts

    def _detect_entry_points(self, pyproject: dict[str, Any], package_json: dict[str, Any], text_cache: dict[Path, str]) -> list[EntryPoint]:
        entries: list[EntryPoint] = []
        for name, target in sorted(self._console_scripts(pyproject).items()):
            entries.append(EntryPoint(
                kind="cli",
                path="pyproject.toml",
                symbol=str(target),
                command=str(name),
                confidence="high",
                evidence=[EvidenceItem("pyproject.toml", "project.scripts entry point", f"{name}={target}")],
            ))
        scripts = package_json.get("scripts") if isinstance(package_json.get("scripts"), dict) else {}
        for name in ("dev", "start", "build", "test"):
            if name in scripts:
                entries.append(EntryPoint(
                    kind="frontend_script",
                    path=self._package_json_rel(),
                    command=f"npm run {name}",
                    confidence="high",
                    evidence=[EvidenceItem(self._package_json_rel(), "npm script", str(scripts[name]))],
                ))
        for path, text in text_cache.items():
            rel = self._rel(path)
            if re.search(r"(\w+)\s*=\s*FastAPI\s*\(", text):
                symbol = re.search(r"(\w+)\s*=\s*FastAPI\s*\(", text)
                entries.append(EntryPoint("api", rel, symbol.group(1) if symbol else "app", f"uvicorn {rel.removesuffix('.py').replace('/', '.')}:app", "high", [EvidenceItem(rel, "FastAPI application object")]))
            if re.search(r"(\w+)\s*=\s*Flask\s*\(", text):
                symbol = re.search(r"(\w+)\s*=\s*Flask\s*\(", text)
                entries.append(EntryPoint("api", rel, symbol.group(1) if symbol else "app", f"flask --app {rel} run", "high", [EvidenceItem(rel, "Flask application object")]))
            if "if __name__" in text and "__main__" in text:
                entries.append(EntryPoint("script", rel, None, f"python {rel}", "medium", [EvidenceItem(rel, "Python main guard")]))
        for name, kind, command in [
            ("manage.py", "django", "python manage.py runserver"),
            ("main.py", "script", "python main.py"),
            ("app.py", "script", "python app.py"),
            ("train.py", "ml_training", "python train.py"),
            ("inference.py", "ml_inference", "python inference.py"),
            ("streamlit_app.py", "streamlit", "streamlit run streamlit_app.py"),
        ]:
            if (self.root / name).exists():
                entries.append(EntryPoint(kind, name, None, command, "medium", [EvidenceItem(name, "common entry-point filename")]))
        return _dedupe_entry_points(entries)

    def _detect_project_types(
        self,
        frameworks: list[str],
        interfaces: list[str],
        architecture: ArchitectureSummary,
        entry_points: list[EntryPoint],
        text_cache: dict[Path, str],
        package_json: dict[str, Any],
    ) -> list[str]:
        types: list[str] = []
        framework_set = set(frameworks)
        entry_kinds = {entry.kind for entry in entry_points}
        text = "\n".join(text_cache.values()).lower()
        has_api = "API" in interfaces or architecture.api_present
        has_frontend = "web frontend" in interfaces or architecture.frontend_present
        if has_api and has_frontend:
            types.append("backend + frontend application")
        if "FastAPI" in framework_set:
            types.append("FastAPI API")
        if "Flask" in framework_set:
            types.append("Flask application")
        if "Django" in framework_set or "django" in entry_kinds:
            types.append("Django application")
        if "CLI" in interfaces:
            types.append("CLI tool")
        if architecture.notebooks_present and not has_api and not has_frontend:
            types.append("data-science/notebook project")
        top_dirs = set(self.metadata.get("top_level_directories") or [])
        if (any(name in framework_set for name in ("scikit-learn", "PyTorch", "TensorFlow")) and ("ml_training" in entry_kinds or {"models", "data"} & top_dirs)) or "train.py" in {entry.path for entry in entry_points}:
            types.append("ML training project")
        if "ml_inference" in entry_kinds or "predict(" in text:
            types.append("ML inference/service project")
        has_rag_pattern = (
            re.search(r"\bretriever\b", text)
            and re.search(r"\b(vectorstore|embedding|similarity_search)\b", text)
        ) or re.search(r"\b(openai|client)\.(embeddings|chat\.completions)", text)
        if any(name in framework_set for name in ("LangChain", "LlamaIndex")) or has_rag_pattern:
            types.append("RAG/LLM application")
        if self._console_scripts(self._read_pyproject()) and "CLI tool" not in types:
            types.append("Python library/package")
        if self.metadata.get("has_pyproject") and "Python library/package" not in types and self.metadata.get("source_roots"):
            types.append("Python library/package")
        if not types and self.metadata.get("python_files", 0):
            types.append("automation/script repository")
        if self.metadata.get("has_readme") and self.metadata.get("python_files", 0) and not architecture.ci_signals and not has_api and not has_frontend:
            types.append("student portfolio/demo project")
        return _dedupe_strings(types) or ["unknown/mixed project"]

    def _build_runnability(self, pyproject: dict[str, Any], package_json: dict[str, Any], entry_points: list[EntryPoint]) -> Runnability:
        dep_env = self.audit.get("dependency_environment") if isinstance(self.audit.get("dependency_environment"), dict) else {}
        evidence: list[EvidenceItem] = []
        install_commands: list[str] = []
        run_commands: list[str] = []
        test_commands: list[str] = []
        build_commands: list[str] = []

        install = dep_env.get("likely_install_command")
        if install:
            install_commands.append(str(install))
            evidence.append(EvidenceItem("dependency metadata", "likely install command inferred", str(install)))
        if package_json:
            install_commands.append("npm install")
            evidence.append(EvidenceItem(self._package_json_rel(), "frontend dependency metadata", None))

        for entry in entry_points:
            if entry.command:
                if entry.kind in {"frontend_script"} and "build" in entry.command:
                    build_commands.append(entry.command)
                elif entry.kind in {"frontend_script"} and "test" in entry.command:
                    test_commands.append(entry.command)
                else:
                    run_commands.append(entry.command)

        scripts = package_json.get("scripts") if isinstance(package_json.get("scripts"), dict) else {}
        if "build" in scripts and "npm run build" not in build_commands:
            build_commands.append("npm run build")
        if "test" in scripts and "npm run test" not in test_commands:
            test_commands.append("npm run test")
        if self.metadata.get("has_tests"):
            test_commands.append("python -m pytest")
            evidence.append(EvidenceItem("tests", "test files or tests directory detected", None))

        missing: list[str] = []
        if not install_commands:
            missing.append("dependency metadata")
        if not run_commands:
            missing.append("documented run command")
        if not test_commands:
            missing.append("test command")

        pytest_verified = any(
            item.get("tool") == "pytest" and item.get("status") == "completed"
            for item in self.audit.get("test_analysis", []) if isinstance(item, dict)
        )
        if pytest_verified:
            status = "verified"
        elif install_commands and run_commands and test_commands:
            status = "documented"
        elif install_commands or run_commands or test_commands:
            status = "inferred"
        else:
            status = "insufficient_evidence"
        return Runnability(
            install_commands=_dedupe_strings(install_commands),
            run_commands=_dedupe_strings(run_commands),
            test_commands=_dedupe_strings(test_commands),
            build_commands=_dedupe_strings(build_commands),
            status=status,
            confidence=self._confidence(evidence, high=3, medium=1),
            missing_requirements=missing,
            evidence=evidence[:10],
        )

    def _confidence(self, evidence: list[EvidenceItem], *, high: int, medium: int) -> str:
        if len(evidence) >= high:
            return "high"
        if len(evidence) >= medium:
            return "medium"
        return "low"


def build_executive_report(
    audit: dict[str, Any],
    understanding: ProjectUnderstanding,
    recommendations: list[StructuredRecommendation],
    *,
    profile_id: str,
) -> ExecutiveReport:
    profile = get_profile(profile_id)
    scoring = audit.get("scoring") if isinstance(audit.get("scoring"), dict) else {}
    diagnosis = audit.get("diagnosis") if isinstance(audit.get("diagnosis"), dict) else {}
    health = diagnosis.get("repository_health") if isinstance(diagnosis.get("repository_health"), dict) else {}
    evidence_conf = diagnosis.get("evidence_confidence") if isinstance(diagnosis.get("evidence_confidence"), dict) else {}
    verdict = str(health.get("label") or "unknown")
    observed_score = scoring.get("overall_score") if isinstance(scoring.get("overall_score"), int) else None
    identity = understanding.project_identity
    hard_flags = diagnosis.get("hard_flags") if isinstance(diagnosis.get("hard_flags"), list) else []
    limitations = diagnosis.get("limitations") if isinstance(diagnosis.get("limitations"), list) else []
    strongest = []
    if identity.frameworks:
        strongest.append("Detected frameworks: " + ", ".join(identity.frameworks[:4]))
    if understanding.runnability.install_commands:
        strongest.append("Install path inferred from dependency metadata.")
    if understanding.entry_points:
        strongest.append("Likely entry points detected.")
    if not strongest:
        strongest.append("Basic repository structure was scanned.")
    risks = [str(flag).replace("_", " ").lower() for flag in hard_flags[:3]]
    if not risks:
        finding_count = _total_findings(audit)
        if finding_count:
            risks.append(f"{finding_count} analyzer finding(s) require review")
    if not risks and limitations:
        risks.append("Evidence is limited by unavailable or skipped analyzers")
    if not risks:
        risks.append("No primary risk identified in observed evidence")
    top_repo_rec = next((rec for rec in recommendations if rec.recommendation_type == "repository_fix"), None)
    top_any_rec = recommendations[0] if recommendations else None
    biggest_gap = top_repo_rec.title if top_repo_rec else (top_any_rec.title if top_any_rec else "No major gap identified")
    next_step = top_repo_rec.recommended_steps[0] if top_repo_rec and top_repo_rec.recommended_steps else "Review evidence limitations and keep tests/docs current."
    evidence_gaps = [str(item) for item in limitations[:4]]
    if evidence_conf.get("summary") and not evidence_gaps:
        evidence_gaps.append(str(evidence_conf["summary"]))
    article = "an" if identity.project_type[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
    return ExecutiveReport(
        headline=f"{format_verdict(verdict)} {identity.project_type}",
        one_sentence_summary=f"DrRepo sees {article} {identity.project_type} with {verdict.replace('_', ' ')} observed health and {evidence_conf.get('label', 'unknown')} evidence confidence.",
        project_description=f"Primary language: {identity.primary_language}; layout: {identity.package_layout}; interfaces: {', '.join(identity.interfaces) if identity.interfaces else 'not clearly detected'}.",
        verdict=verdict,
        observed_score=observed_score,
        evidence_confidence=str(evidence_conf.get("label") or "unknown"),
        strongest_signals=strongest[:4],
        primary_risks=risks[:4],
        biggest_gap=biggest_gap,
        next_best_step=next_step,
        evidence_gaps=evidence_gaps,
        user_profile_context=str(profile.get("primary_user_goal", profile.get("display_name", profile_id))),
    )


def build_structured_recommendations(
    audit: dict[str, Any],
    understanding: ProjectUnderstanding,
    *,
    profile_id: str,
) -> list[StructuredRecommendation]:
    profile = get_profile(profile_id)
    recommendations: list[StructuredRecommendation] = []
    findings = _all_findings(audit)

    readme_codes = [f for f in findings if str(f.get("code", "")).startswith("README-")]
    if readme_codes:
        recommendations.append(_rec(
            "readme-documentation",
            "Document setup, testing, and project context",
            "documentation",
            "medium",
            "repository_fix",
            "Clear README evidence is a major trust signal for this profile.",
            [str(f.get("code")) for f in readme_codes[:6]],
            ["Add setup or installation instructions that match the detected dependency strategy.", "Document the test command and expected result.", "State the project license or link to it."],
            "The README explains how to install, run, test, and evaluate the project.",
            effort="medium",
        ))

    if any(f.get("tool") == "ruff" for f in findings):
        codes = sorted({str(f.get("code") or "ruff") for f in findings if f.get("tool") == "ruff"})
        recommendations.append(_rec(
            "ruff-quality",
            "Resolve grouped Ruff code-quality findings",
            "code_quality",
            "low",
            "repository_fix",
            "Lint findings reduce maintainability and make review noisier.",
            codes[:8],
            ["Run Ruff locally.", "Fix rule families that repeat across files first.", "Re-run DrRepo or Ruff to confirm the finding count drops."],
            "Ruff completes with no findings or only intentionally accepted exceptions.",
            effort="small",
        ))

    if any(f.get("tool") == "bandit" for f in findings):
        recommendations.append(_rec(
            "bandit-security",
            "Review Bandit security findings",
            "security",
            "high",
            "repository_fix",
            "Security findings can represent real risk and should stay visible even when other scores are strong.",
            [str(f.get("code") or f.get("message")) for f in findings if f.get("tool") == "bandit"][:6],
            ["Inspect each Bandit finding in context.", "Replace unsafe patterns or document a justified suppression.", "Re-run Bandit/DrRepo to confirm the risk is resolved."],
            "Bandit findings are fixed, justified, or suppressed with clear rationale.",
            effort="medium",
        ))

    test_findings = [f for f in findings if f.get("tool") == "pytest"]
    if test_findings:
        recommendations.append(_rec(
            "test-failures",
            "Fix test execution failures",
            "testing",
            "high",
            "repository_fix",
            "Failing or un-runnable tests block trust in the observed repository behavior.",
            [str(f.get("code") or f.get("message")) for f in test_findings[:4]],
            ["Run the detected pytest command locally.", "Fix import, dependency, fixture, or assertion failures.", "Re-run DrRepo in deep_local mode."],
            "Pytest completes with a passed outcome.",
            effort="medium",
        ))

    runnability = understanding.runnability
    if runnability.status in {"insufficient_evidence", "inferred"}:
        recommendations.append(_rec(
            "runnability",
            "Make the project run path explicit",
            "reproducibility",
            "medium",
            "repository_fix",
            "Users should not have to infer how to install, run, or test the project.",
            runnability.missing_requirements,
            ["Add or update dependency metadata.", "Document the primary run command.", "Document the test command or explain why tests are not applicable."],
            "A new user can install, run, and test the project from documented commands.",
            effort="medium",
        ))

    for entry in _audit_environment_issues(audit):
        recommendations.append(_rec(
            f"audit-env-{entry['tool']}",
            f"Improve DrRepo analyzer coverage for {entry['tool']}",
            "audit_environment",
            "low",
            "audit_environment",
            "This limits DrRepo confidence but is not automatically a repository defect.",
            [entry["reason"]],
            ["Install the optional DrRepo analysis extra if appropriate.", "Re-run the audit to improve evidence confidence."],
            f"{entry['tool']} is available or intentionally skipped with a known reason.",
            effort="small",
            optional_example='python -m pip install -e ".[analysis]"',
        ))

    if profile_id in {"production_service", "production_api"}:
        _boost(recommendations, {"security", "testing"}, -2)
    elif profile_id == "student_portfolio":
        _boost(recommendations, {"documentation", "reproducibility"}, -25)
    elif profile_id in {"learning_or_research_project", "ai_ml_project"}:
        _boost(recommendations, {"reproducibility", "documentation"}, -2)
    elif profile_id == "open_source_library":
        _boost(recommendations, {"documentation", "testing", "code_quality"}, -2)

    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
    recommendations = _dedupe_recommendations(recommendations)
    recommendations.sort(key=lambda rec: (rec.priority, severity_rank.get(rec.severity, 4), rec.title))
    for index, rec in enumerate(recommendations, start=1):
        rec.priority = index
    return recommendations


def _rec(
    rec_id: str,
    title: str,
    category: str,
    severity: str,
    recommendation_type: str,
    why: str,
    evidence: list[str],
    steps: list[str],
    success_check: str,
    *,
    effort: str,
    optional_example: str | None = None,
) -> StructuredRecommendation:
    base_priority = {"high": 10, "medium": 30, "low": 50}.get(severity, 40)
    return StructuredRecommendation(
        id=rec_id,
        title=title,
        category=category,
        priority=base_priority,
        severity=severity,
        confidence="medium" if evidence else "low",
        impact="high" if severity == "high" else "medium",
        effort=effort,
        recommendation_type=recommendation_type,
        why_it_matters=why,
        evidence=_dedupe_strings([item for item in evidence if item])[:8],
        related_findings=_dedupe_strings([item for item in evidence if item])[:8],
        recommended_steps=steps,
        optional_example=optional_example,
        success_check=success_check,
    )


def _boost(recommendations: list[StructuredRecommendation], categories: set[str], amount: int) -> None:
    for rec in recommendations:
        if rec.category in categories:
            rec.priority = max(1, rec.priority + amount)


def _dedupe_recommendations(recommendations: list[StructuredRecommendation]) -> list[StructuredRecommendation]:
    seen: set[str] = set()
    result: list[StructuredRecommendation] = []
    for rec in recommendations:
        if rec.id in seen:
            continue
        seen.add(rec.id)
        result.append(rec)
    return result


def _all_findings(audit: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for section in ("static_analysis", "test_analysis", "repository_analysis"):
        for analyzer in audit.get(section, []) or []:
            if not isinstance(analyzer, dict):
                continue
            tool = analyzer.get("tool")
            for finding in analyzer.get("findings", []) or []:
                if isinstance(finding, dict):
                    item = dict(finding)
                    item.setdefault("tool", tool)
                    findings.append(item)
    return findings


def _total_findings(audit: dict[str, Any]) -> int:
    return len(_all_findings(audit))


def _audit_environment_issues(audit: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for section in ("static_analysis", "test_analysis", "repository_analysis"):
        for analyzer in audit.get(section, []) or []:
            if not isinstance(analyzer, dict):
                continue
            status = analyzer.get("status")
            if status not in {"not_available", "skipped_by_config", "failed_to_run", "partial"}:
                continue
            tool = str(analyzer.get("tool") or "unknown")
            reason = analyzer.get("unavailable_reason") or analyzer.get("skipped_reason")
            errors = analyzer.get("errors") if isinstance(analyzer.get("errors"), list) else []
            if not reason and errors:
                reason = str(errors[0])
            issues.append({"tool": tool, "reason": str(reason or status)})
    return issues


def _dedupe_entry_points(entries: list[EntryPoint]) -> list[EntryPoint]:
    seen: set[tuple[str, str, str | None, str | None]] = set()
    result: list[EntryPoint] = []
    for entry in entries:
        key = (entry.kind, entry.path, entry.symbol, entry.command)
        if key in seen:
            continue
        seen.add(key)
        result.append(entry)
    return result[:20]


def _dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = str(item).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _has_api_signal(text: str) -> bool:
    return bool(
        re.search(r"\bfrom\s+fastapi\b", text)
        and re.search(r"\w+\s*=\s*FastAPI\s*\(", text)
        or re.search(r"\bfrom\s+flask\b", text)
        and re.search(r"\w+\s*=\s*Flask\s*\(", text)
        or "DJANGO_SETTINGS_MODULE" in text
        or "django.core" in text
    )


def _has_strong_ml_signal(joined_text: str, top_dirs: set[str]) -> bool:
    if {"models", "data", "notebooks"} & top_dirs and any(token in joined_text for token in ("sklearn", "torch", "tensorflow", "fit(", "predict(")):
        return True
    return bool(re.search(r"\b(train|fit|predict|inference)\s*\(", joined_text) and any(token in joined_text for token in ("sklearn", "torch", "tensorflow")))


def format_verdict(verdict: str) -> str:
    labels = {
        "healthy": "Healthy",
        "needs_attention": "Needs attention",
        "at_risk": "At risk",
    }
    return labels.get(verdict, verdict.replace("_", " ").title())
