from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from drrepo.readiness.models import (
    DevOpsReadinessAssessment,
    DimensionAssessment,
    ReadinessEvidence,
    ReadinessFinding,
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
SIGNAL_EXCLUDED_DIRS = {
    "tests",
    "test",
    "docs",
    "examples",
    "fixtures",
}

PRODUCTION_TYPES = {"FastAPI API", "Flask application", "Django application", "backend + frontend application", "ML inference/service project"}
LIBRARY_TYPES = {"Python library/package", "CLI tool"}


def build_devops_readiness(audit: dict[str, Any], *, profile_id: str = "student_portfolio") -> dict[str, Any]:
    root = Path(str(audit.get("path", ".")))
    builder = DevOpsReadinessBuilder(root, audit, profile_id=profile_id)
    assessment = builder.build()
    return to_plain_dict(assessment)


class DevOpsReadinessBuilder:
    def __init__(self, root: Path, audit: dict[str, Any], *, profile_id: str):
        self.root = root
        self.audit = audit
        self.profile_id = profile_id
        self.understanding = audit.get("project_understanding") if isinstance(audit.get("project_understanding"), dict) else {}
        self.identity = self.understanding.get("project_identity") if isinstance(self.understanding.get("project_identity"), dict) else {}
        self.architecture = self.understanding.get("architecture_summary") if isinstance(self.understanding.get("architecture_summary"), dict) else {}
        self.runnability = self.understanding.get("runnability") if isinstance(self.understanding.get("runnability"), dict) else {}
        self.metadata = audit.get("metadata") if isinstance(audit.get("metadata"), dict) else {}

    def build(self) -> DevOpsReadinessAssessment:
        dimensions = [
            self._ci_cd(),
            self._containerization(),
            self._deployment(),
            self._configuration_security(),
            self._observability(),
            self._release_hygiene(),
            self._reproducibility(),
        ]
        applicable = [dim for dim in dimensions if dim.applicability != "not_applicable"]
        scored = [dim for dim in applicable if dim.score is not None]
        observed_score = round(sum(dim.score or 0 for dim in scored) / len(scored)) if scored else None
        blockers = [finding for dim in dimensions for finding in dim.blockers]
        risks = [finding for dim in dimensions for finding in dim.findings if finding not in blockers]
        evidence_gaps = [gap for dim in dimensions for gap in dim.unverified_checks]
        strengths = _dedupe([strength for dim in dimensions for strength in dim.strengths])[:8]
        confidence = self._overall_confidence(dimensions)
        verdict = self._verdict(observed_score, blockers, applicable, confidence)
        next_best_step = self._next_best_step(blockers, risks, evidence_gaps)
        recommendations = self._recommendations(blockers, risks, evidence_gaps)
        return DevOpsReadinessAssessment(
            applicability="applicable" if applicable else "not_applicable",
            verdict=verdict,
            observed_score=observed_score,
            evidence_confidence=confidence,
            dimensions=dimensions,
            strengths=strengths,
            blockers=blockers,
            risks=risks[:12],
            evidence_gaps=_dedupe(evidence_gaps)[:12],
            next_best_step=next_best_step,
            recommendations=recommendations,
        )

    def _project_types(self) -> set[str]:
        return {str(self.identity.get("project_type", "")), *[str(item) for item in self.identity.get("secondary_project_types", []) or []]}

    def _is_production_app(self) -> bool:
        return bool(self._project_types() & PRODUCTION_TYPES) or self.profile_id in {"production_service", "production_api"}

    def _is_library_or_cli(self) -> bool:
        return bool(self._project_types() & LIBRARY_TYPES)

    def _is_frontend(self) -> bool:
        return bool(self.architecture.get("frontend_present")) or (self.root / "package.json").exists()

    def _is_ml(self) -> bool:
        return bool(self.architecture.get("ml_present")) or self.profile_id == "ai_ml_project" or any("ML" in item or "RAG" in item for item in self._project_types())

    def _test_result(self, tool: str) -> dict[str, Any] | None:
        results = self.audit.get("test_analysis") if isinstance(self.audit.get("test_analysis"), list) else []
        return next((item for item in results if isinstance(item, dict) and item.get("tool") == tool), None)

    def _rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root)).replace("\\", "/")
        except Exception:
            return str(path)

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    def _ignored(self, path: Path) -> bool:
        try:
            rel = path.relative_to(self.root)
        except Exception:
            return True
        if len(rel.parts) >= 2 and rel.parts[0] == "drrepo" and rel.parts[1] in {"analyzers", "intelligence", "readiness"}:
            return True
        return any(part in IGNORED_DIRS or part in SIGNAL_EXCLUDED_DIRS for part in rel.parts)

    def _files(self, pattern: str) -> list[Path]:
        return sorted(path for path in self.root.rglob(pattern) if path.is_file() and not self._ignored(path))

    def _evidence(self, path: str, reason: str, detail: str | None = None) -> ReadinessEvidence:
        return ReadinessEvidence(path=path, reason=reason, detail=detail)

    def _finding(
        self,
        finding_id: str,
        title: str,
        description: str,
        category: str,
        severity: str,
        evidence: list[ReadinessEvidence],
        suggested_fix: str,
        success_check: str,
        *,
        confidence: str = "medium",
        why: str = "",
    ) -> ReadinessFinding:
        return ReadinessFinding(
            id=finding_id,
            title=title,
            description=description,
            category=category,
            severity=severity,
            confidence=confidence,
            evidence=evidence,
            affected_files=_dedupe([item.path for item in evidence]),
            why_it_matters=why or description,
            suggested_fix=suggested_fix,
            success_check=success_check,
        )

    def _dimension(
        self,
        dim_id: str,
        title: str,
        applicability: str,
        evidence: list[ReadinessEvidence],
        strengths: list[str],
        findings: list[ReadinessFinding],
        blockers: list[ReadinessFinding],
        unverified: list[str],
        summary: str,
    ) -> DimensionAssessment:
        if applicability == "not_applicable":
            return DimensionAssessment(dim_id, title, applicability, None, "not_applicable", "high", summary, strengths, findings, blockers, evidence, unverified)
        if not evidence and not findings and not blockers:
            return DimensionAssessment(dim_id, title, applicability, None, "insufficient_evidence", "low", summary, strengths, findings, blockers, evidence, unverified)
        penalty = sum(_severity_penalty(f.severity) for f in findings) + sum(_severity_penalty(f.severity) for f in blockers)
        score = max(0, min(100, 100 - penalty - (8 * len(unverified))))
        if blockers:
            score = min(score, 59)
            status = "blocked"
        elif findings:
            status = "needs_work"
        elif unverified:
            status = "partially_assessed"
        else:
            status = "ready"
        confidence = "high" if len(evidence) >= 3 else "medium" if evidence else "low"
        return DimensionAssessment(dim_id, title, applicability, score, status, confidence, summary, strengths, findings, blockers, evidence, unverified)

    def _ci_cd(self) -> DimensionAssessment:
        applicable = "applicable"
        workflows = sorted((self.root / ".github" / "workflows").glob("*.yml")) + sorted((self.root / ".github" / "workflows").glob("*.yaml"))
        alt = [self.root / ".gitlab-ci.yml", self.root / "azure-pipelines.yml", self.root / "Jenkinsfile"]
        ci_files = [path for path in workflows + alt if path.exists()]
        evidence: list[ReadinessEvidence] = []
        strengths: list[str] = []
        findings: list[ReadinessFinding] = []
        blockers: list[ReadinessFinding] = []
        unverified: list[str] = []
        if not ci_files:
            target = blockers if self._is_production_app() else findings
            target.append(self._finding("ci.missing", "Add automated CI validation", "No CI workflow file was found.", "ci_cd", "high" if self._is_production_app() else "medium", [], "Add a CI workflow that installs dependencies and runs lint, security checks, tests, and builds where applicable.", "Pull requests run CI before merge."))
            return self._dimension("ci_cd", "CI/CD", applicable, evidence, strengths, findings, blockers, ["workflow presence"], "No CI configuration was detected.")
        text = "\n".join(self._read_text(path) for path in ci_files).lower()
        rels = [self._rel(path) for path in ci_files]
        evidence.append(self._evidence(", ".join(rels), "CI configuration file detected"))
        checks = {
            "pull_request trigger": "pull_request" in text,
            "push trigger": re.search(r"\bpush\s*:", text) is not None or "push" in text,
            "checkout step": "actions/checkout" in text,
            "python setup": "setup-python" in text,
            "node setup": "setup-node" in text,
            "dependency install": any(token in text for token in ("pip install", "poetry install", "uv sync", "npm ci", "npm install")),
            "lint step": any(token in text for token in ("ruff", "flake8", "eslint")),
            "security scan": any(token in text for token in ("bandit", "pip-audit", "safety")),
            "test step": any(token in text for token in ("pytest", "npm test", "pnpm test")),
            "coverage step": "coverage" in text,
            "frontend build": any(token in text for token in ("npm run build", "pnpm build", "vite build")),
            "permissions declaration": "permissions:" in text,
            "timeout": "timeout-minutes" in text,
            "concurrency": "concurrency:" in text,
            "artifact upload": "upload-artifact" in text,
            "matrix testing": "matrix:" in text,
        }
        for label, present in checks.items():
            if present:
                strengths.append(f"CI includes {label}.")
                evidence.append(self._evidence(", ".join(rels), label))
        if not checks["test step"] and not checks["frontend build"]:
            blockers.append(self._finding("ci.no-validation", "CI does not run tests or builds", "A CI file exists, but no test or build command was detected.", "ci_cd", "high", evidence[:1], "Add pytest and/or frontend build steps to the workflow.", "CI fails when tests or builds fail."))
        if self._is_frontend() and not checks["frontend build"]:
            findings.append(self._finding("ci.no-frontend-build", "Add frontend build validation to CI", "Frontend files exist but CI does not appear to run a production build.", "ci_cd", "medium", evidence[:1], "Run the frontend build command in CI.", "CI runs the frontend production build."))
        if self.metadata.get("has_tests") and not checks["test step"]:
            findings.append(self._finding("ci.no-tests", "Run tests in CI", "Tests exist but CI does not appear to run them.", "ci_cd", "high", evidence[:1], "Add a pytest step after dependency installation.", "CI runs pytest on pull requests."))
        if "permissions: write-all" in text or re.search(r"contents:\s*write", text):
            findings.append(self._finding("ci.broad-permissions", "Review broad workflow permissions", "Workflow permissions appear broader than necessary.", "ci_cd", "medium", evidence[:1], "Use least-privilege workflow permissions.", "Workflow permissions are explicitly scoped."))
        if re.search(r"(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{12,}", text):
            blockers.append(self._finding("ci.plaintext-secret", "Remove plaintext secret-like value from workflow", "A workflow appears to contain a hardcoded secret-like value.", "ci_cd", "critical", evidence[:1], "Move the value into repository secrets and reference it through secrets.*.", "Workflow files contain no plaintext credentials."))
        for label, present in checks.items():
            if not present and label in {"security scan", "coverage step", "timeout", "concurrency", "artifact upload", "matrix testing"}:
                unverified.append(label)
        return self._dimension("ci_cd", "CI/CD", applicable, evidence, strengths, findings, blockers, unverified, "Static CI workflow configuration was inspected.")

    def _containerization(self) -> DimensionAssessment:
        relevant = self._is_production_app() or self.profile_id == "production_api"
        dockerfiles = [path for path in self.root.glob("Dockerfile*") if path.is_file()]
        compose_files = [self.root / name for name in ("compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml") if (self.root / name).exists()]
        if not relevant and not dockerfiles and not compose_files:
            return self._dimension("containerization", "Containerization", "not_applicable", [], [], [], [], [], "Containerization is optional for this project type.")
        evidence: list[ReadinessEvidence] = []
        strengths: list[str] = []
        findings: list[ReadinessFinding] = []
        blockers: list[ReadinessFinding] = []
        unverified: list[str] = []
        if not dockerfiles:
            findings.append(self._finding("container.missing", "Add container packaging if this will be deployed", "No Dockerfile was found for an applicable deployable service.", "containerization", "medium", [], "Add a Dockerfile or document why container deployment is not used.", "The service has a reviewed container or an explicit non-container deployment path."))
            return self._dimension("containerization", "Containerization", "applicable", evidence, strengths, findings, blockers, ["Dockerfile"], "Containerization is applicable but no Dockerfile was detected.")
        for dockerfile in dockerfiles:
            rel = self._rel(dockerfile)
            text = self._read_text(dockerfile)
            lower = text.lower()
            evidence.append(self._evidence(rel, "Dockerfile detected"))
            if re.search(r"^from\s+\S+:\S+", lower, re.M):
                strengths.append("Base image includes an explicit tag.")
            else:
                findings.append(self._finding("container.unpinned-base", "Pin the container base image tag", "The Dockerfile base image lacks an explicit tag.", "containerization", "medium", [self._evidence(rel, "FROM instruction")], "Use an explicit stable base image tag.", "Dockerfile FROM lines use explicit tags."))
            if re.search(r"^user\s+", lower, re.M):
                strengths.append("Container switches to a non-default user.")
            else:
                findings.append(self._finding("container.root-user", "Run the container as a non-root user", "No USER instruction was detected.", "containerization", "medium", [self._evidence(rel, "missing USER")], "Create and switch to an unprivileged runtime user.", "Dockerfile includes a non-root USER instruction."))
            if re.search(r"^workdir\s+", lower, re.M):
                strengths.append("Dockerfile sets a working directory.")
            else:
                unverified.append("WORKDIR")
            if "healthcheck" in lower:
                strengths.append("Dockerfile declares a healthcheck.")
            elif self._is_production_app():
                findings.append(self._finding("container.no-healthcheck", "Add a container healthcheck", "No Docker HEALTHCHECK was detected for a deployable service.", "containerization", "low", [self._evidence(rel, "missing HEALTHCHECK")], "Add a lightweight healthcheck command for the service.", "Container healthcheck exercises the service health endpoint."))
            if re.search(r"copy\s+.*\.env", lower) or ".env" in lower:
                blockers.append(self._finding("container.copies-env", "Do not copy .env files into the image", "The Dockerfile appears to copy or reference .env content.", "containerization", "critical", [self._evidence(rel, ".env reference")], "Pass secrets through runtime environment variables, not image layers.", "Docker build context excludes .env files."))
            if "copy . ." in lower and not (self.root / ".dockerignore").exists():
                findings.append(self._finding("container.broad-copy", "Add .dockerignore for broad COPY", "Dockerfile uses broad COPY but no .dockerignore was found.", "containerization", "medium", [self._evidence(rel, "COPY . .")], "Add .dockerignore for caches, venvs, .env files, node_modules, and build artifacts.", ".dockerignore excludes generated and secret files."))
        if (self.root / ".dockerignore").exists():
            strengths.append(".dockerignore is present.")
            evidence.append(self._evidence(".dockerignore", "Docker build exclusions configured"))
        for compose in compose_files:
            rel = self._rel(compose)
            text = self._read_text(compose).lower()
            evidence.append(self._evidence(rel, "Compose file detected"))
            if "privileged: true" in text or "/var/run/docker.sock" in text or "network_mode: host" in text:
                blockers.append(self._finding("compose.dangerous-options", "Review dangerous compose runtime options", "Compose uses privileged mode, Docker socket mount, or host networking.", "containerization", "high", [self._evidence(rel, "dangerous compose option")], "Remove privileged/host-level runtime options unless explicitly required and documented.", "Compose does not grant unnecessary host privileges."))
        return self._dimension("containerization", "Containerization", "applicable", evidence, strengths, findings, blockers, unverified, "Container and compose files were statically inspected.")

    def _deployment(self) -> DimensionAssessment:
        relevant = self._is_production_app() or self._is_frontend()
        deploy_files = [
            "Procfile", "render.yaml", "railway.json", "fly.toml", "vercel.json", "netlify.toml",
            "app.yaml", "serverless.yml",
        ]
        found = [self.root / name for name in deploy_files if (self.root / name).exists()]
        found += self._files("*.tf")
        found += [path for path in self._files("*.yaml") if any(part in self._rel(path).lower() for part in ("k8s", "kubernetes", "helm", "deploy"))]
        if not relevant and not found:
            return self._dimension("deployment", "Deployment", "not_applicable", [], [], [], [], [], "Deployment configuration is not required for this project type.")
        evidence: list[ReadinessEvidence] = []
        strengths: list[str] = []
        findings: list[ReadinessFinding] = []
        blockers: list[ReadinessFinding] = []
        unverified: list[str] = []
        if found:
            for path in found:
                evidence.append(self._evidence(self._rel(path), "deployment configuration detected"))
            strengths.append("Deployment configuration is present.")
        elif relevant:
            findings.append(self._finding("deploy.missing", "Document or add deployment configuration", "No deployment configuration was detected for an applicable service/app.", "deployment", "medium", [], "Add platform configuration or document the intended deployment path.", "The repository includes a documented deploy target or deployment config."))
        deployment_config_text = " ".join(self._read_text(path) for path in found).lower()
        run_commands = [
            str(cmd)
            for cmd in self.runnability.get("run_commands", []) or []
            if str(cmd).strip().lower() not in {"npm run dev", "pnpm dev", "yarn dev"}
        ]
        run_text = " ".join(run_commands).lower() + " " + deployment_config_text
        if self._is_production_app() and not any(token in run_text for token in ("gunicorn", "uvicorn", "hypercorn", "waitress", "daphne")):
            findings.append(self._finding("deploy.no-production-server", "Clarify the production server command", "No production Python server command was detected.", "deployment", "medium", evidence[:1], "Document or configure the production server command.", "Deployment uses a production server command rather than an ambiguous dev command."))
        if any(token in run_text for token in ("flask run", "uvicorn --reload", "django runserver")) or any(token in deployment_config_text for token in ("npm run dev", "vite --host")):
            blockers.append(self._finding("deploy.dev-server", "Do not use development server commands for production", "A deployment/run command appears to use a development server.", "deployment", "high", evidence[:1], "Replace development server commands with production server/build commands.", "Deployment command does not use reload/dev server modes."))
        if self._is_frontend() and not any(cmd for cmd in self.runnability.get("build_commands", []) or []):
            findings.append(self._finding("deploy.no-frontend-build", "Document the frontend production build", "Frontend code exists but no build command was inferred.", "deployment", "medium", evidence[:1], "Add a package build script and include it in deployment/CI.", "Frontend deployment builds production assets."))
        if self._is_production_app() and not self._has_health_endpoint():
            findings.append(self._finding("deploy.no-health-endpoint", "Add a health or readiness endpoint", "No obvious health/readiness endpoint was detected.", "deployment", "medium", [], "Add a lightweight /health or /ready endpoint for deployment checks.", "Service exposes a documented health/readiness endpoint."))
        if not found:
            unverified.append("deployment target")
        return self._dimension("deployment", "Deployment", "applicable", evidence, strengths, findings, blockers, unverified, "Deployment files and run commands were statically inspected.")

    def _configuration_security(self) -> DimensionAssessment:
        evidence: list[ReadinessEvidence] = []
        strengths: list[str] = []
        findings: list[ReadinessFinding] = []
        blockers: list[ReadinessFinding] = []
        unverified: list[str] = []
        env_examples = [path for path in self.root.glob(".env*") if path.name in {".env.example", ".env.sample", ".env.template"}]
        committed_env = [path for path in self.root.glob(".env*") if path.name == ".env"]
        gitignore = self.root / ".gitignore"
        gitignore_text = self._read_text(gitignore) if gitignore.exists() else ""
        env_ignored = bool(re.search(r"(?m)^\s*\.env(?:\s|$)", gitignore_text))
        if env_examples:
            strengths.append("Environment example file is present.")
            evidence.extend(self._evidence(self._rel(path), "environment example") for path in env_examples)
        elif self._is_production_app() or self._is_ml():
            findings.append(self._finding("config.no-env-example", "Document required environment variables", "No .env.example-style file was detected.", "configuration_security", "medium", [], "Add an example env file with names only, never real secret values.", "Required environment variables are documented without secrets."))
        for path in committed_env:
            evidence.append(self._evidence(self._rel(path), "local .env file detected"))
            if env_ignored:
                strengths.append("Local .env file is ignored by git.")
                continue
            text = self._read_text(path)
            if _contains_secret_like_value(text):
                blockers.append(self._finding("config.committed-env-secret", "Remove committed .env credentials", "A committed .env file appears to contain credential-like values.", "configuration_security", "critical", [self._evidence(self._rel(path), "secret-like .env value")], "Remove the file from version control and rotate any real credentials.", "No committed .env file contains credentials."))
            else:
                findings.append(self._finding("config.committed-env", "Avoid committing .env files", "A .env file is committed even if no obvious secret was detected.", "configuration_security", "medium", [self._evidence(self._rel(path), "committed .env file")], "Commit only .env.example and ignore .env.", ".env is ignored; .env.example documents required names."))
        for path in self._files("*.py")[:250]:
            text = self._read_text(path)
            rel = self._rel(path)
            if re.search(r"debug\s*=\s*true", text, re.I):
                blockers.append(self._finding("config.debug-true", "Disable production debug mode", "A source file appears to enable debug mode.", "configuration_security", "high", [self._evidence(rel, "debug=True")], "Gate debug mode behind environment-specific configuration.", "Production config does not hardcode debug mode."))
            if _contains_secret_like_value(text):
                blockers.append(self._finding("config.hardcoded-secret", "Remove hardcoded credential-like value", "A source file appears to contain a hardcoded credential-like value. The value is redacted.", "configuration_security", "critical", [self._evidence(rel, "secret-like assignment")], "Move credentials into secret storage or environment variables and rotate real values.", "No source file contains hardcoded credentials."))
            if re.search(r"allow_origins\s*=\s*\[[^\]]*['\"]\*['\"]", text, re.I) and "allow_credentials=True" in text:
                blockers.append(self._finding("config.wildcard-cors", "Avoid wildcard credentialed CORS", "A CORS configuration appears to allow wildcard origins with credentials.", "configuration_security", "high", [self._evidence(rel, "wildcard credentialed CORS")], "Restrict origins when credentials are enabled.", "Credentialed CORS uses explicit allowed origins."))
        if env_ignored:
            strengths.append(".gitignore excludes environment files.")
            evidence.append(self._evidence(".gitignore", ".env ignored"))
        else:
            unverified.append(".env ignored")
        return self._dimension("configuration_security", "Configuration and Secrets", "applicable", evidence, strengths, findings, blockers, unverified, "Configuration files and source were scanned for conservative secret/debug signals.")

    def _observability(self) -> DimensionAssessment:
        if self._is_library_or_cli() and not self._is_production_app():
            return self._dimension("observability", "Observability and Operations", "not_applicable", [], [], [], [], [], "Operational observability is not required for this project type.")
        applicability = "applicable"
        evidence: list[ReadinessEvidence] = []
        strengths: list[str] = []
        findings: list[ReadinessFinding] = []
        blockers: list[ReadinessFinding] = []
        unverified: list[str] = []
        joined = ""
        for path in self._files("*.py")[:250]:
            text = self._read_text(path)
            joined += "\n" + text.lower()
            rel = self._rel(path)
            if "import logging" in text or "logging." in text:
                evidence.append(self._evidence(rel, "logging usage"))
        if evidence:
            strengths.append("Python logging usage detected.")
        elif self._is_production_app():
            findings.append(self._finding("obs.no-logging", "Add explicit application logging", "No standard logging usage was detected.", "observability", "medium", [], "Add structured or standard logging around startup, requests, and failures.", "Operational events are logged with useful context."))
        if self._has_health_endpoint():
            strengths.append("Health/readiness endpoint signal detected.")
            evidence.append(self._evidence("source", "health/readiness route detected"))
        elif self._is_production_app():
            findings.append(self._finding("obs.no-health", "Expose a health/readiness endpoint", "No health/readiness endpoint was detected.", "observability", "medium", [], "Add /health or /ready and use it in deploy/container checks.", "Health endpoint reports process readiness."))
        for token, label in (("prometheus", "metrics"), ("opentelemetry", "tracing"), ("sentry_sdk", "error tracking"), ("request_id", "request correlation"), ("timeout", "timeout handling"), ("tenacity", "retry/backoff")):
            if token in joined:
                strengths.append(f"{label.title()} signal detected.")
                evidence.append(self._evidence("source", label, token))
            else:
                if self._is_production_app() and label in {"metrics", "tracing", "error tracking", "request correlation"}:
                    unverified.append(label)
        return self._dimension("observability", "Observability and Operations", applicability, evidence, strengths, findings, blockers, unverified, "Operational source-code signals were inspected without importing modules.")

    def _release_hygiene(self) -> DimensionAssessment:
        evidence: list[ReadinessEvidence] = []
        strengths: list[str] = []
        findings: list[ReadinessFinding] = []
        blockers: list[ReadinessFinding] = []
        unverified: list[str] = []
        pyproject = self.root / "pyproject.toml"
        if pyproject.exists():
            text = self._read_text(pyproject)
            evidence.append(self._evidence("pyproject.toml", "package metadata"))
            if re.search(r"version\s*=", text):
                strengths.append("Version metadata is present.")
            else:
                findings.append(self._finding("release.no-version", "Add explicit version metadata", "Package metadata exists but no version field was detected.", "release_hygiene", "low", [self._evidence("pyproject.toml", "missing version")], "Add version metadata or dynamic version configuration.", "Package metadata exposes a version."))
            if re.search(r"requires-python\s*=", text):
                strengths.append("Python version constraint is declared.")
            else:
                unverified.append("Python version constraint")
        elif self._is_library_or_cli():
            findings.append(self._finding("release.no-package-metadata", "Add package metadata", "Library/CLI repositories should declare package metadata.", "release_hygiene", "medium", [], "Add pyproject.toml with project metadata.", "Package metadata declares name, version, dependencies, and Python support."))
        if any((self.root / name).exists() for name in ("LICENSE", "LICENSE.md", "COPYING")):
            strengths.append("License file is present.")
            evidence.append(self._evidence("LICENSE", "license file"))
        elif self._is_library_or_cli() or self.profile_id == "student_portfolio":
            findings.append(self._finding("release.no-license", "Add or reference a license", "No license file was detected.", "release_hygiene", "medium", [], "Add a license file or document the license status.", "Repository includes a clear license."))
        if any((self.root / name).exists() for name in ("CHANGELOG.md", "CHANGELOG.rst", "HISTORY.md")):
            strengths.append("Changelog is present.")
            evidence.append(self._evidence("CHANGELOG", "changelog file"))
        else:
            unverified.append("changelog")
        if (self.root / ".github" / "dependabot.yml").exists() or (self.root / "renovate.json").exists():
            strengths.append("Dependency update automation is configured.")
            evidence.append(self._evidence("dependency bot config", "update automation"))
        else:
            unverified.append("dependency update automation")
        if (self.root / ".pre-commit-config.yaml").exists():
            strengths.append("Pre-commit checks are configured.")
            evidence.append(self._evidence(".pre-commit-config.yaml", "pre-commit config"))
        return self._dimension("release_hygiene", "Release Hygiene", "applicable", evidence, strengths, findings, blockers, unverified, "Release metadata and maintenance automation were inspected.")

    def _reproducibility(self) -> DimensionAssessment:
        evidence: list[ReadinessEvidence] = []
        strengths: list[str] = []
        findings: list[ReadinessFinding] = []
        blockers: list[ReadinessFinding] = []
        unverified: list[str] = []
        dep = self.audit.get("dependency_environment") if isinstance(self.audit.get("dependency_environment"), dict) else {}
        if dep.get("dependency_metadata_exists"):
            strengths.append("Dependency metadata is present.")
            evidence.append(self._evidence(", ".join(dep.get("dependency_files") or []), "dependency metadata"))
        else:
            findings.append(self._finding("repro.no-dependencies", "Declare project dependencies", "No dependency metadata was detected.", "reproducibility", "high", [], "Add pyproject.toml, requirements.txt, or equivalent environment metadata.", "A fresh checkout can install dependencies from committed metadata."))
        if dep.get("lock_file_exists") or (self.root / "package-lock.json").exists() or (self.root / "pnpm-lock.yaml").exists() or (self.root / "yarn.lock").exists():
            strengths.append("A dependency lock file is present.")
            evidence.append(self._evidence("lock file", "dependency locking"))
        elif self._is_production_app() or self._is_frontend() or self._is_ml():
            findings.append(self._finding("repro.no-lock", "Add dependency locking for reproducible installs", "No lock file was detected for an applicable project.", "reproducibility", "medium", [], "Commit an appropriate lock file for the selected package manager.", "Dependency resolution is reproducible from a lock file."))
        if self._is_ml():
            if any((self.root / name).exists() for name in ("environment.yml", "requirements.txt", "pyproject.toml")):
                strengths.append("ML environment metadata is present.")
            else:
                findings.append(self._finding("repro.ml-env", "Document the ML runtime environment", "ML signals exist but no environment metadata was detected.", "reproducibility", "high", [], "Document Python/package versions and hardware assumptions.", "Training/inference environment can be recreated."))
            if not any((self.root / name).exists() for name in ("data", "models", "configs", "config")):
                unverified.append("dataset/model artifact handling")
        if self.runnability.get("install_commands"):
            evidence.append(self._evidence("project understanding", "install command inferred", ", ".join(self.runnability.get("install_commands") or [])))
        else:
            unverified.append("install command")
        if self.runnability.get("test_commands"):
            evidence.append(self._evidence("project understanding", "test command inferred", ", ".join(self.runnability.get("test_commands") or [])))
        else:
            unverified.append("test command")
        pytest_result = self._test_result("pytest")
        coverage_result = self._test_result("coverage")
        if pytest_result and pytest_result.get("execution_mode") == "deep_isolated":
            summary = pytest_result.get("summary") if isinstance(pytest_result.get("summary"), dict) else {}
            outcome = str(summary.get("outcome", "unknown"))
            if pytest_result.get("status") == "completed" and outcome == "passed":
                strengths.append("Tests passed inside the isolated Docker runner.")
                evidence.append(self._evidence("isolated pytest", "tests verified in Docker", outcome))
            elif outcome == "setup_failed":
                unverified.append("isolated dependency setup")
            elif outcome == "docker_unavailable":
                unverified.append("Docker isolated runner availability")
            else:
                evidence.append(self._evidence("isolated pytest", "isolated test evidence", outcome))
        if coverage_result and coverage_result.get("execution_mode") == "deep_isolated":
            summary = coverage_result.get("summary") if isinstance(coverage_result.get("summary"), dict) else {}
            if coverage_result.get("status") == "completed":
                strengths.append("Coverage was measured inside the isolated Docker runner.")
                evidence.append(self._evidence("isolated coverage", "coverage verified in Docker", str(summary.get("coverage_percent"))))
            elif summary.get("outcome") in {"setup_failed", "docker_unavailable", "no_data"}:
                unverified.append(f"isolated coverage {summary.get('outcome')}")
        return self._dimension("reproducibility", "Reproducibility", "applicable", evidence, strengths, findings, blockers, unverified, "Dependency and command metadata were inspected for reproducibility.")

    def _has_health_endpoint(self) -> bool:
        for path in self._files("*.py")[:250]:
            text = self._read_text(path).lower()
            if any(route in text for route in ('"/health"', "'/health'", '"/ready"', "'/ready'", '"/readiness"', "'/readiness'")):
                return True
        return False

    def _overall_confidence(self, dimensions: list[DimensionAssessment]) -> str:
        applicable = [dim for dim in dimensions if dim.applicability != "not_applicable"]
        if not applicable:
            return "limited"
        highish = sum(1 for dim in applicable if dim.confidence in {"high", "medium"} and dim.status != "insufficient_evidence")
        if highish == len(applicable):
            return "high"
        if highish * 2 >= len(applicable):
            return "medium"
        return "limited"

    def _verdict(self, score: int | None, blockers: list[ReadinessFinding], applicable: list[DimensionAssessment], confidence: str) -> str:
        if not applicable:
            return "not_applicable"
        if score is None:
            return "insufficient_evidence"
        if any(f.severity == "critical" for f in blockers):
            return "blocked"
        if blockers:
            return "blocked" if score < 70 else "needs_work"
        if score >= 90 and confidence != "limited":
            return "release_ready"
        if score >= 75:
            return "nearly_ready"
        return "needs_work"

    def _next_best_step(self, blockers: list[ReadinessFinding], risks: list[ReadinessFinding], gaps: list[str]) -> str:
        if blockers:
            return blockers[0].suggested_fix
        if risks:
            return risks[0].suggested_fix
        if gaps:
            return f"Verify or document: {gaps[0]}."
        return "Keep release checks current as the repository evolves."

    def _recommendations(self, blockers: list[ReadinessFinding], risks: list[ReadinessFinding], gaps: list[str]) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        for index, finding in enumerate([*blockers, *risks][:8], start=1):
            rec_type = "release_blocker" if finding in blockers else "security_review" if finding.category == "configuration_security" else "repository_fix"
            recs.append({
                "id": f"devops-{finding.id}",
                "title": finding.title,
                "category": finding.category,
                "priority": index,
                "severity": finding.severity,
                "confidence": finding.confidence,
                "impact": "high" if finding.severity in {"critical", "high"} else "medium",
                "effort": "medium",
                "recommendation_type": rec_type,
                "why_it_matters": finding.why_it_matters,
                "evidence": [f"{item.path}: {item.reason}" for item in finding.evidence],
                "related_findings": [finding.id],
                "recommended_steps": _steps_for(finding),
                "optional_example": None,
                "success_check": finding.success_check,
            })
        if not recs and gaps:
            recs.append({
                "id": "devops-verify-gaps",
                "title": "Document remaining release evidence",
                "category": "release_readiness",
                "priority": 1,
                "severity": "low",
                "confidence": "medium",
                "impact": "medium",
                "effort": "small",
                "recommendation_type": "verification_step",
                "why_it_matters": "Unverified release evidence lowers confidence even when no blocker is present.",
                "evidence": gaps[:5],
                "related_findings": [],
                "recommended_steps": [f"Document or configure {gap}." for gap in gaps[:3]],
                "optional_example": None,
                "success_check": "Release readiness evidence gaps are explicitly documented or configured.",
            })
        return recs


def _steps_for(finding: ReadinessFinding) -> list[str]:
    if finding.id == "ci.missing":
        return [
            "Add .github/workflows/ci.yml or equivalent CI configuration.",
            "Trigger it on pull_request and pushes to the primary branch.",
            "Install dependencies using the repository's documented command.",
            "Run lint/security checks, tests, and builds that apply to this project.",
        ]
    if finding.id.startswith("config."):
        return ["Remove the unsafe configuration from source control.", "Document safe environment-variable names only.", "Rotate any real credentials if applicable."]
    if finding.id.startswith("container."):
        return ["Update the Dockerfile or .dockerignore.", "Keep secrets out of image layers.", "Re-run DrRepo to confirm the static check passes."]
    return [finding.suggested_fix, "Re-run DrRepo to confirm the readiness finding is resolved."]


def _severity_penalty(severity: str) -> int:
    return {"critical": 45, "high": 30, "medium": 18, "low": 8}.get(severity, 10)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        value = str(item).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _contains_secret_like_value(text: str) -> bool:
    patterns = [
        r"(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}",
        r"sk-[A-Za-z0-9]{20,}",
        r"ghp_[A-Za-z0-9]{20,}",
        r"AKIA[0-9A-Z]{16}",
    ]
    lowered = text.lower()
    if "example" in lowered or "placeholder" in lowered or "your_" in lowered:
        return False
    return any(re.search(pattern, text, re.I) for pattern in patterns)
