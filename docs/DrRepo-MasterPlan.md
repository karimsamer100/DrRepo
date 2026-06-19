# DrRepo — Architecture

> **Status:** Architecture baseline, v0.3  
> This document defines component boundaries and data flow. It is a design guide, not a claim that every component already exists.

---

## 1. Architecture goals

DrRepo must be designed so that:

1. the same audit engine can power CLI, GitHub URL audit, web API, and PR review;
2. deterministic evidence remains traceable and separate from model/LLM reasoning;
3. ML features are stable, versioned, and reproducible;
4. the web architecture does not require unsafe execution of untrusted code;
5. a future dashboard can consume stored audit reports without reimplementing the analyzer;
6. the project can grow phase by phase without a rewrite.

---

## 2. Context diagram

```mermaid
flowchart LR
    U1[Developer using CLI] --> C[DrRepo Core]
    U2[Public GitHub Repository] --> C
    U3[Future Web User] --> W[Web UI / API]
    W --> C
    G[GitHub Actions PR Workflow] --> P[Change Impact Adapter]
    P --> C

    C --> T[Analysis Tools]
    C --> M[ML Models]
    C --> L[LLM Remediation Provider]
    C --> R[Reports]
    C --> S[Storage Later]
```

### Boundary rule

`DrRepo Core` must not depend on CLI formatting, HTML templates, GitHub Actions YAML, or a specific LLM vendor. Those are adapters around a reusable service layer.

---

## 3. Core pipeline

```mermaid
flowchart TD
    A[Audit Request] --> B[Input Resolver]
    B --> C[Workspace Manager]
    C --> D[Repository Scanner]
    D --> E[Audit Plan]

    E --> F1[Test & Coverage Runner]
    E --> F2[Static Analyzer Runners]
    E --> F3[README Auditor]
    E --> F4[Structure Auditor]

    F1 --> G[Normalized Evidence]
    F2 --> G
    F3 --> G
    F4 --> G

    G --> H[Feature Builder]
    G --> I[Rule Score Engine]
    H --> J[Repository Readiness Classifier]
    H --> K[Portfolio Readiness Classifier]

    I --> L[Hybrid Diagnosis Engine]
    J --> L
    K --> L

    L --> M[LLM Remediation Advisor - Optional]
    M --> N[Report Builder]
    N --> O[Terminal Summary]
    N --> P[Markdown Report]
    N --> Q[JSON Report]
    N --> R[API / GitHub Adapter Later]
```

---

## 4. Request and input architecture

## 4.1 Unified audit request

All interfaces should create an internal `AuditRequest` rather than calling tool runners directly.

Conceptual fields:

```python
@dataclass
class AuditRequest:
    source_type: Literal[
        "local_path", "github_url", "zip_upload", "single_file", "code_text", "pull_request"
    ]
    source_value: str | Path
    mode: Literal["repository", "portfolio", "quick_review", "pull_request"]
    profile: str = "general_python"
    config_path: Path | None = None
    run_id: str | None = None
```

This is a conceptual shape only. The final project may use Pydantic models instead.

## 4.2 Input resolver responsibilities

| Input | Resolver behavior | Notes |
|---|---|---|
| Local path | Validate directory, normalize path, identify repo root | MVP |
| Public GitHub URL | Validate URL, clone/download to temp workspace, clean up | Later |
| ZIP upload | Validate archive, extract safely, detect root | Web phase |
| File upload | Build a quick-review workspace | Web phase |
| Code text | Build an in-memory/scoped workspace | Web phase |
| PR context | Resolve base/head refs and diff | PR phase |

## 4.3 Private repository boundary

Private GitHub repositories are **not initially supported through URLs**. The project will not store GitHub tokens or implement OAuth in the early scope.

Supported alternatives in the initial product direction:

- local CLI audit;
- later ZIP upload handled under web safety constraints.

---

## 5. Workspace and execution safety

## 5.1 Local CLI mode

The local CLI may run configured checks because the user controls the repository and environment. Even here, commands must be explicit, logged, time-limited where possible, and error-aware.

## 5.2 Public GitHub URL mode

Cloned repositories should use a temporary workspace:

```text
create temporary directory
→ clone with limits
→ analyze
→ preserve only intended report/raw evidence
→ remove workspace
```

## 5.3 Web upload mode — future security boundary

A web server must treat uploaded code as untrusted.

### Initial web-safe approach

- static inspection first;
- no arbitrary `pytest`, install script, shell script, or project entry point execution by default;
- archive size and file-count limits;
- path traversal protection during extraction;
- temporary workspace cleanup;
- secrets redaction/ignore rules where feasible.

### Advanced future approach

Run selected commands only inside isolated containers or sandboxes with:

- restricted filesystem;
- no privileged execution;
- limited CPU and memory;
- short timeout;
- restricted network;
- command allowlist;
- cleanup and audit logging.

The web app is a product feature, but safety design is a mandatory prerequisite for executing untrusted repository tests.

---

## 6. Evidence layer

## 6.1 Normalized evidence contract

Every analyzer should return structured, normalized output. The rest of DrRepo must not parse human tool text repeatedly.

Conceptual envelope:

```json
{
  "tool": "ruff",
  "status": "completed",
  "started_at": "...",
  "duration_ms": 310,
  "summary": {
    "issue_count": 5
  },
  "findings": [],
  "raw_artifact_path": "...",
  "errors": []
}
```

### Required status distinctions

```text
completed
not_available
not_applicable
skipped_by_config
failed_to_run
partial
```

This prevents false conclusions such as treating “coverage could not run” as “coverage is 0%.”

## 6.2 Tool adapters

Initial adapters:

| Tool | Purpose | Planned output |
|---|---|---|
| Ruff | lint/code-quality signals | issue count, categories, locations |
| Bandit | Python security findings | severity, confidence, locations |
| Radon | complexity/maintainability signals | complexity statistics, functions |
| Pytest | test discovery and status | passed/failed/skipped/errors |
| coverage.py | coverage measurement | percent, availability, report |

Potential later adapters: mypy, Semgrep, pip-audit, profile-specific tools, IaC linters.

## 6.3 Repository metadata evidence

The repository scanner creates metadata including:

- file/folder tree summary;
- Python source count;
- tests presence;
- README and docs presence;
- dependency/configuration files;
- environment files;
- Docker/CI signals;
- likely application type;
- ignored/generated file signals.

## 6.4 README and structure evidence

README and structure modules should emit findings with identifiers, not only a score:

```text
README-SETUP-MISSING
README-USAGE-MISSING
STRUCTURE-TESTS-MISSING
STRUCTURE-ENV-EXAMPLE-MISSING
```

This makes reports, rules, ML features, and LLM explanations refer to the same evidence.

---

## 7. Feature-engineering layer

## 7.1 Purpose

The feature builder transforms normalized evidence into a stable tabular feature schema for both ML models.

It must be independent from the CLI/UI and versioned over time.

## 7.2 Proposed feature groups

| Group | Examples |
|---|---|
| Repository size | file count, source file count, LOC, module count |
| Testing | tests present, test status, test count, coverage, coverage availability |
| Code quality | lint counts, issue density, selected categories |
| Security | Bandit counts by severity, secret flags, unsafe patterns |
| Maintainability | complexity mean/max, high-complexity count, large file count |
| Structure | src/tests/docs existence, dependency file, gitignore, env example |
| Documentation | README section flags, setup/usage/architecture/results indicators |
| Presentation | demo/screenshot, license, author/contact, portfolio metadata |

## 7.3 Feature schema rules

- Define a feature schema version, for example `v1`.
- Validate that required fields exist before inference.
- Preserve unknown values rather than silently converting them to zero.
- Keep raw evidence references available for explainability.
- Avoid features that leak the final label.

---

## 8. Rules, ML, and LLM orchestration

## 8.1 Rule score engine

The rule score engine computes transparent category scores from evidence. It is expected to be the first working diagnosis layer.

Inputs: normalized evidence + configuration.  
Outputs: category scores, deduction reasons, hard flags, missing-data notes.

## 8.2 Repository readiness classifier

Inputs: feature schema vector.  
Output: predicted readiness class + probability/confidence + model version.

The model does **not** replace hard evidence. A project with a critical security flag must visibly show that flag even if the model predicts a favorable class.

## 8.3 Portfolio readiness classifier

Inputs: feature schema vector, emphasizing presentation and reproducibility features.  
Output: predicted portfolio class + probability/confidence + model version.

## 8.4 LLM remediation advisor

Inputs: bounded evidence bundle, top findings, scores, model predictions, audit profile.  
Output: validated remediation plan and explanation.

The LLM must not be given unrestricted access to a private repository or secrets. Future provider calls require explicit context selection/redaction policy.

## 8.5 Hybrid diagnosis engine

Conceptual output:

```json
{
  "repository_health": {
    "rule_score": 68,
    "diagnosis": "needs_improvement",
    "model_prediction": "needs_improvement",
    "model_confidence": 0.74
  },
  "portfolio_readiness": {
    "rule_score": 58,
    "prediction": "almost_ready",
    "model_confidence": 0.66
  },
  "hard_flags": ["TESTS_FAILING"],
  "top_findings": [],
  "evidence_coverage": [],
  "limitations": []
}
```

When rules and model disagree, the report should disclose that disagreement rather than hide it.

---

## 9. Report architecture

## 9.1 Report formats

| Format | Purpose |
|---|---|
| Terminal | Fast feedback during CLI use |
| JSON | Machine-readable artifact, API integration, dataset builder |
| Markdown | Human-readable GitHub/report artifact |
| HTML/PDF | Future downloadable web reports |

## 9.2 Report sections

1. audit scope and input type;
2. executive summary;
3. evidence availability and limitations;
4. health and portfolio scores;
5. model predictions and model metadata;
6. key findings with evidence;
7. prioritized remediation plan;
8. raw-tool summary / appendix;
9. rerun instructions and configuration reference.

---

## 10. Interface adapters

## 10.1 CLI adapter — MVP

Representative commands:

```bash
drrepo audit ./my-project
drrepo portfolio ./my-project
```

The CLI formats an `AuditRequest`, calls the core service, and renders report output. It should not embed audit algorithms.

## 10.2 GitHub URL adapter — later

```bash
drrepo audit https://github.com/owner/repository
```

Uses the same audit service after cloning into a controlled temporary workspace.

## 10.3 FastAPI adapter — future

Possible conceptual endpoints:

```text
POST /api/audits
GET  /api/audits/{audit_id}
GET  /api/audits/{audit_id}/report
GET  /api/audits/{audit_id}/status
POST /api/reviews/code
POST /api/pr-reviews
```

The actual API should be designed after the core report model stabilizes.

## 10.4 GitHub Actions / PR adapter — later

PR mode should create an audit request containing:

- base/head refs;
- changed files;
- diff summary;
- repository baseline report where available;
- CI configuration;
- policy thresholds.

The adapter then turns the diagnosis into a check status, artifact, and optionally a PR comment.

---

## 11. Storage and dashboard — later

Initial CLI audits can write reports to disk. When history matters, add storage:

- SQLite first;
- audit run metadata;
- report paths/normalized summaries;
- score history;
- model version used;
- before/after comparison;
- later PostgreSQL only if necessary.

A dashboard can then show:

- audit history;
- score trends;
- common issue categories;
- improvement deltas;
- model prediction distribution;
- analysis duration/error rates.

---

## 12. Deployment and observability direction

### Docker

Docker is planned for reproducible packaging and, later, controlled execution environments.

### GitHub Actions

GitHub Actions will initially validate DrRepo itself and later host PR Change Impact Review workflows.

### Monitoring — deferred

Potential metrics:

- audit duration;
- tool failure rate;
- input type distribution;
- report generation failures;
- model prediction distribution;
- web queue duration;
- sandbox failures.

Prometheus/Grafana are optional late-stage polish, not an early milestone.

---

## 13. Architecture decisions still open

| Topic | Current direction | Decision trigger |
|---|---|---|
| CLI framework | Typer proposed | Decide during project setup |
| Config format | `.drrepo.yml` proposed | Decide before scoring/config implementation |
| Web UI | Streamlit/simple templates/React unknown | Decide after FastAPI/report API exists |
| LLM provider | provider interface, specific vendor open | Decide at LLM phase based on budget/quality/privacy |
| Execution sandbox | static-only web first | Decide when enabling uploaded test execution |
| Model label definitions | proposed labels | Freeze after rubric/data exploration |
| Storage schema | SQLite first | Decide when report history/dashboard begins |

---

## 14. Architecture success criteria

The architecture is successful when:

- CLI and future API can share the same `AuditRequest → AuditResult` service contract;
- adding GitHub URL support does not rewrite analyzers;
- reports can be generated from stored normalized evidence;
- ML inference consumes a validated, versioned feature schema;
- the LLM can be disabled without breaking the audit;
- unsafe web execution is clearly separated from local CLI execution;
- PR mode reuses repository evidence rather than becoming a parallel product.


# DrRepo — Comprehensive Project Blueprint

> **Status:** Living planning document, v0.3  
> **Project name:** DrRepo  
> **Project type:** Applied AI + Machine Learning + MLOps + DevOps + Software Engineering portfolio project  
> **Primary product mode:** Repository Audit  
> **Secondary product mode:** Pull Request / Change Impact Review  
> **Initial language target:** Python  
> **Last planning update:** June 2026

---

## Document status and conventions

This is the master planning document. It is deliberately broader than the MVP and should evolve as implementation teaches us what is practical.

Each item should use one of these labels:

| Label | Meaning |
|---|---|
| **Confirmed** | Explicitly agreed and should guide current design. |
| **Proposed** | Strong current direction; may change after implementation or research. |
| **Deferred** | Valuable, but intentionally not built in the current phase. |
| **Open Question** | Requires a later decision or experiment. |
| **Rejected for now** | Intentionally excluded to avoid scope creep. |

---

# 1. Project identity

## 1.1 One-line description

**DrRepo is an evidence-driven repository health, readiness, and remediation platform that audits Python projects, predicts repository and portfolio readiness, and turns findings into prioritized improvement plans.**

## 1.2 Product promise

DrRepo should answer five practical questions:

1. **What is wrong or incomplete in this repository?**
2. **What evidence supports that finding?**
3. **How serious or important is it?**
4. **What should the developer fix first?**
5. **Did the repository improve after the fixes?**

## 1.3 Why this is not a generic AI code-review wrapper

A general AI assistant can read code and offer opinions. DrRepo must deliver a repeatable engineering workflow:

| Generic code-chat workflow | DrRepo workflow |
|---|---|
| User pastes code and asks for an opinion | System inspects an entire repository or scoped input. |
| Suggestions can be vague and inconsistent | Findings are grounded in tools, rules, traces, and explicit evidence. |
| No stable quality baseline | Multi-dimensional scores create a baseline and enable before/after comparison. |
| No execution or tool integration | The platform runs or interprets tests, coverage, linters, security tools, and repository checks where safe. |
| No project-specific prioritization | Findings are converted into a remediation backlog ordered by severity, impact, confidence, and effort. |
| AI is the entire product | AI is one layer inside a hybrid system of deterministic checks, ML models, and remediation reasoning. |

The project should be judged by the quality of its **pipeline, evidence model, feature engineering, ML lifecycle, CI integration, safety boundaries, and explainability**—not by the fact that it calls an LLM.

---

# 2. Problem statement

Developers, students, and small teams often have repositories that “work” but are not ready to be maintained, shared, reviewed, deployed, or presented professionally.

Common gaps include:

- no tests or unverified tests;
- incomplete or failing coverage;
- lint, security, complexity, and maintainability issues;
- unclear repository layout;
- weak README and setup instructions;
- missing reproducibility files such as `requirements.txt`, `.env.example`, or `.gitignore`;
- poor portfolio presentation despite technically useful work;
- no structured way to decide what to fix first;
- pull requests reviewed only by pass/fail tests, without baseline-aware quality signals.

DrRepo does not try to replace senior engineers. It provides an **evidence-based first diagnosis** and a structured improvement path.

---

# 3. Product scope

## 3.1 Confirmed core modes

### A. Repository Audit Mode — **Confirmed / primary**

A full audit of a Python repository.

Supported product inputs across the complete vision:

- local directory path;
- public GitHub repository URL;
- ZIP project upload in the future web app;
- optional browser directory selection later;
- file upload or pasted code for smaller, lower-fidelity reviews.

A full repository audit may produce:

- Repository Health / Readiness score;
- Code Quality score;
- Testing and Coverage score;
- Security score;
- Maintainability score;
- Documentation score;
- Repository Structure score;
- Portfolio Readiness score;
- ML classifier predictions and confidence;
- a prioritized remediation plan.

### B. Portfolio Readiness Mode — **Confirmed / primary**

A repository-level assessment focused on whether the project is professionally presentable for GitHub, a CV, internships, LinkedIn, or interviews.

It is not cosmetic only. It combines project presentation with reproducibility and engineering credibility.

### C. Quick File / Pasted Code Review — **Confirmed product direction; deferred implementation**

When the system sees only a file or code snippet, it must provide a scoped code review and be explicit that it cannot claim a repository-wide health score.

Example output:

```text
Scope: Single-file review
Available signals: lint, complexity, security patterns, code explanation
Unavailable signals: repository structure, test suite, documentation, dependency configuration
```

### D. Pull Request / Change Impact Review — **Confirmed / secondary**

This feature uses the same audit foundation, but focuses on what a change introduced or degraded:

- test failures or coverage regression;
- new lint/security findings;
- complexity increase;
- changed sensitive modules;
- missing tests for changed behavior;
- impact on repository baseline.

It will become a GitHub Actions quality gate after the audit engine is stable. It is **not** the first implementation focus.

---

## 3.2 Input and privacy scope

| Input path | Intended support | Status |
|---|---|---|
| Local repository | CLI audits a path supplied by the developer | First implementation |
| Public GitHub URL | Clone/download to temporary workspace | Planned after local audit |
| Private GitHub URL | Requires OAuth/app tokens, permissions, secret handling | Deferred |
| Project ZIP | Future web input | Deferred |
| Browser folder selection | Optional convenience UI | Deferred |
| Single file / pasted code | Future quick-review input | Deferred |

**Confirmed privacy decision:** private GitHub repositories are not part of the initial product scope. A user can audit a private project locally or upload an archive in a later web flow.

---

# 4. User personas

## 4.1 Primary: developers and small teams — **Confirmed**

The primary audience is developers and small teams that want a practical codebase diagnosis, repeatable quality checks, and a clear improvement plan.

## 4.2 Secondary: students and junior developers — **Confirmed**

DrRepo is especially useful for portfolio projects, but it should not be framed as a “student-only” toy. Student-oriented portfolio checks are a differentiating product mode, not the entire identity.

## 4.3 Future: reviewers, team leads, and DevOps engineers — **Supported by later modes**

The PR and CI mode gives the project a clear team/DevOps narrative without forcing it to be the initial user experience.

---

# 5. Differentiators

## 5.1 Evidence-first findings — **Confirmed**

Every important finding should contain as much evidence as available:

```text
Finding: Hardcoded secret pattern detected
Evidence: Security scanner + local pattern match
Location: config.py:14
Severity: High
Impact: Credentials may be exposed in a public repository
Suggested remediation: Move the value to an environment variable and add .env.example
```

## 5.2 Multi-dimensional health profile — **Confirmed**

The product should avoid hiding everything inside a single opaque score.

Proposed dimensions:

| Dimension | Main evidence |
|---|---|
| Code Quality | Ruff findings, naming/style signals, code smells where measurable |
| Testing | test discovery, test result, coverage, organization |
| Security | Bandit, secret patterns, unsafe operations, configuration signals |
| Maintainability | complexity, large functions/files, modularity signals |
| Documentation | README completeness, usage/setup clarity, docs signals |
| Structure | repository organization, dependency and environment files |
| Portfolio Readiness | presentation + reproducibility + engineering credibility |

## 5.3 Prioritized remediation plan — **Confirmed**

DrRepo should convert a list of findings into a practical backlog:

```text
Fix now      — security or reliability blockers
Fix next     — high-impact readiness problems
Improve later— maintainability and documentation upgrades
Nice to have — polish and presentation enhancements
```

A proposed prioritization formula is:

```text
priority = severity × impact × confidence × fixability
```

**Open Question:** the exact numeric formula and weighting should be validated after sample reports exist. The first implementation may use a deterministic priority matrix instead.

## 5.4 Audit profiles — **Proposed, high value**

An audit profile enables context-sensitive checks. Possible profiles:

- General Python Repository;
- Python CLI Tool;
- FastAPI Backend;
- Machine Learning Project;
- Data Science Project;
- Portfolio Project.

This can differentiate DrRepo from a generic linter, but must not delay the baseline audit. The first implementation may ship with one general Python profile and one portfolio emphasis profile.

## 5.5 Before/after comparison — **Proposed**

When reports are stored, DrRepo can compare audit runs:

```text
Repository Health: 61 → 80 (+19)
Testing:           42 → 71 (+29)
Documentation:     55 → 82 (+27)
```

This becomes an important dashboard and interview feature later.

---

# 6. Hybrid intelligence design

## 6.1 System principle — **Confirmed**

DrRepo will use a hybrid decision system:

```text
Deterministic evidence
+ transparent rules and scores
+ ML readiness predictions
+ LLM remediation reasoning
= explainable final diagnosis
```

No single layer should silently decide the full result.

## 6.2 Role boundaries — **Confirmed**

| Layer | Responsibility | Must not do alone |
|---|---|---|
| Tests and coverage | Demonstrate executable behavior and coverage evidence | Claim broad repository readiness |
| Static analysis | Identify factual lint/security/complexity signals | Write a remediation plan without context |
| Repository rules | Produce repeatable checks and category scores | Pretend to learn patterns from data |
| ML models | Learn broader readiness patterns from labeled examples | Override critical deterministic failures without explanation |
| LLM | Explain, synthesize, prioritize, and recommend | Be the only source of truth or sole blocker |
| Final diagnosis engine | Combine layers and preserve evidence | Hide conflicting signals |

## 6.3 Hard rules and model influence — **Proposed**

For repository audits, hard rules should be used carefully. A failing test should be prominent and heavily affect readiness, but an audit report should usually diagnose rather than “block” a repository.

For later PR quality gates, configurable hard rules may cause a failure status, such as:

- critical security finding;
- configured test failure policy;
- coverage regression beyond a configured threshold;
- analysis failure when the policy treats missing evidence as a failure.

The ML classifier should influence the final diagnosis and priority, but should not override a critical evidence-based issue.

---

# 7. Machine-learning design

## 7.1 Model 1: Repository Health / Readiness Classifier — **Confirmed final-product component**

### Purpose

Predict a broad repository readiness state based on engineered audit features.

### Proposed label space — **Open Question**

```text
needs_major_improvement
needs_improvement
repository_ready
```

The names are intentionally action-oriented. Final labels and class balance must be decided after the labeling rubric and dataset distribution are known.

### Candidate features

- source-file count, module count, line count;
- test directory presence and test count;
- test pass/fail/unknown status;
- coverage percentage and availability;
- Ruff issue counts by severity/category where available;
- Bandit/security issue counts;
- hardcoded-secret patterns;
- complexity statistics and high-complexity functions;
- dependency configuration presence;
- `.gitignore` and `.env.example` presence;
- README completeness score;
- repository structure score;
- documentation signals.

### Candidate models

1. Logistic Regression baseline;
2. Random Forest baseline;
3. Gradient Boosting / XGBoost only if justified by experiment results;
4. calibration or probability evaluation when the class output is presented as confidence.

## 7.2 Model 2: Portfolio Readiness Classifier — **Confirmed final-product component**

### Purpose

Predict whether a repository is ready to be publicly displayed as a portfolio project.

### Proposed label space — **Open Question**

```text
not_portfolio_ready
almost_ready
portfolio_ready
```

### Candidate features

- README section coverage;
- project description and problem statement evidence;
- installation and usage instructions;
- examples, demo, screenshots/GIF indicators;
- architecture, results, metrics, limitations, future-work sections;
- test and coverage signals;
- reproducibility/configuration files;
- project structure and documentation signals;
- license and metadata presence;
- profile-specific signals for ML/FastAPI/CLI projects later.

## 7.3 Dataset plan — **Confirmed direction; exact implementation deferred**

The data plan will likely be a hybrid of:

1. **manual labeling** using a written repository and portfolio rubric;
2. **selected public Python repositories** collected under transparent inclusion criteria;
3. **synthetic repositories** with deliberate good/bad patterns for tests, edge cases, and controlled experiments;
4. **audit history** later, only where labels are trustworthy and privacy rules allow it.

### Dataset quality rules — **Confirmed principles**

- Keep a versioned labeling rubric.
- Store the source/collection method and labeler for each training sample where feasible.
- Split train/validation/test by repository, not by repeated audit of the same repository.
- Avoid using a rule-derived score as the only label when the same rule inputs are features; that creates target leakage and produces a model that merely imitates the rubric.
- Compare the model against a simple deterministic baseline.
- Clearly document limitations, imbalance, and data provenance.

## 7.4 MLOps lifecycle — **Confirmed final-product direction**

```mermaid
flowchart LR
    A[Audits + Labels] --> B[Dataset Builder]
    B --> C[Feature Schema]
    C --> D[Train / Validate / Test]
    D --> E[MLflow Tracking]
    E --> F[Best Candidate Model]
    F --> G[Prediction Service / CLI Inference]
    G --> H[New Audit Outcomes]
    H --> I[Monitoring and Dataset Review]
    I --> B
```

MLOps practices to demonstrate:

- dataset versioning or documented snapshot strategy;
- fixed feature schema;
- reproducible training configuration and random seeds;
- experiment tracking with MLflow;
- model artifact/version handling;
- baseline vs candidate comparison;
- metrics including precision, recall, F1, confusion matrix, and calibration/confidence review where relevant;
- inference contract and model fallback;
- later monitoring of feature/prediction distributions and newly labeled outcomes.

---

# 8. LLM remediation design

## 8.1 Role — **Confirmed**

The LLM is a **remediation advisor**, not the only judge.

It should:

- turn structured evidence into plain-language explanations;
- connect related findings;
- explain why an issue matters;
- generate a prioritized fix plan;
- suggest test cases and README sections;
- later propose optional patches, never silently apply them.

## 8.2 Input contract — **Proposed**

The LLM should receive curated, bounded context rather than an entire repository blindly:

- report summary and category scores;
- top evidence-backed findings;
- relevant code snippets only;
- README excerpt or missing-section map;
- audit profile;
- user preference or desired output format.

## 8.3 Output contract — **Confirmed design principle**

Use structured JSON validated by a Pydantic schema. Invalid LLM output must not crash the audit pipeline.

Example conceptual structure:

```json
{
  "summary": "...",
  "priorities": [
    {
      "priority": "high",
      "finding_ids": ["SEC-001", "TEST-003"],
      "why_it_matters": "...",
      "recommended_actions": ["..."],
      "suggested_tests": ["..."]
    }
  ],
  "limitations": ["..."],
  "confidence_notes": ["..."]
}
```

## 8.4 Provider design — **Proposed**

Use a provider interface, beginning with a mock reviewer. Direct APIs are preferred initially over LangChain.

Possible providers later:

- OpenRouter;
- direct vendor APIs;
- Ollama/local models for privacy-oriented experiments.

LangChain/LangGraph are deferred unless a concrete multi-step, tool-using problem justifies them.

---

# 9. Deterministic audit components

## 9.1 Repository scanner — **MVP**

Discovers relevant files and folders:

- source folders and Python files;
- tests;
- README/docs;
- dependency/configuration files;
- `.gitignore`, `.env`, `.env.example`;
- Docker and CI files as signals;
- likely entry points.

## 9.2 Test and coverage runner — **MVP for local repositories**

- detect likely tests;
- run `pytest` when configured and safe in local mode;
- obtain coverage when available;
- distinguish “not found,” “not runnable,” “failed,” and “passed” rather than treating all missing evidence as the same.

## 9.3 Static analysis — **MVP**

Initial tools:

- Ruff;
- Bandit;
- Radon.

Possible later additions:

- Mypy;
- Semgrep;
- pip-audit / dependency vulnerability checks;
- profile-specific linters and IaC checks.

## 9.4 README auditor — **MVP / rule-based first**

Checks may include:

- title and concise project description;
- problem statement and features;
- install/setup instructions;
- usage example;
- tech stack;
- configuration/environment guidance;
- architecture explanation;
- results/metrics when relevant;
- demo/screenshots indicators;
- limitations/future work;
- author/contact/license sections.

## 9.5 Structure auditor — **MVP / rule-based first**

Checks for understandable organization and reproducibility signals:

- source/test/docs separation where appropriate;
- dependency file;
- configuration convention;
- `.gitignore`;
- environment template where relevant;
- generated/cache artifacts committed unintentionally;
- a clear entry point;
- explanation of notebooks/scripts where necessary.

---

# 10. Scoring and diagnosis

## 10.1 Repository Health Score — **Proposed initial weights**

| Dimension | Proposed weight |
|---|---:|
| Code Quality | 20 |
| Testing | 20 |
| Security | 20 |
| Documentation | 15 |
| Repository Structure | 15 |
| Maintainability | 10 |

These weights are a starting point, not a final scientific truth. They should be configurable and documented.

## 10.2 Portfolio Readiness Score — **Proposed initial weights**

| Dimension | Proposed weight |
|---|---:|
| README and narrative | 30 |
| Setup and reproducibility | 20 |
| Structure and engineering signals | 15 |
| Tests and quality evidence | 15 |
| Demo / results / presentation | 10 |
| Professional polish | 10 |

## 10.3 Score use — **Confirmed principle**

Scores must be accompanied by:

- raw evidence;
- missing/unknown signals;
- assumptions;
- a textual diagnosis;
- prioritized recommendations.

A score is an aid to decision-making, not a guarantee of quality.

## 10.4 Diagnosis labels — **Proposed**

Repository audit:

```text
healthy
needs_attention
needs_improvement
needs_major_improvement
```

Portfolio audit:

```text
not_portfolio_ready
almost_ready
portfolio_ready
```

PR mode later:

```text
mergeable
needs_work
blocked
```

---

# 11. Architecture direction

## 11.1 Logical flow

```mermaid
flowchart TD
    A[Input: local path / public GitHub URL / upload later] --> B[Input Resolver]
    B --> C[Workspace Manager]
    C --> D[Repository Scanner]

    D --> E1[Test & Coverage Runner]
    D --> E2[Static Tool Runners]
    D --> E3[README Auditor]
    D --> E4[Structure Auditor]

    E1 --> F[Normalized Audit Evidence]
    E2 --> F
    E3 --> F
    E4 --> F

    F --> G[Feature Builder]
    F --> H[Rule-based Score Engine]
    G --> I[Repository Readiness Model]
    G --> J[Portfolio Readiness Model]

    H --> K[Hybrid Diagnosis Engine]
    I --> K
    J --> K

    K --> L[LLM Remediation Advisor]
    L --> M[Report Generator]
    M --> N[Terminal / JSON / Markdown / API response]
```

## 11.2 Design rule: one core engine, multiple interfaces — **Confirmed**

The analyzer should be reusable across:

- CLI;
- GitHub URL audit;
- future FastAPI web backend;
- GitHub Actions PR mode;
- tests and sample repositories.

The CLI should call the same service layer that a web API will call later. UI/transport logic must not contain the audit logic.

## 11.3 Web safety boundary — **Confirmed architecture concern**

A web server must not blindly execute arbitrary user code.

Initial web analysis should prioritize static inspection. Any execution of untrusted tests/scripts requires a hardened isolation plan such as a constrained container with:

- no host filesystem access;
- limited CPU/memory;
- timeout;
- restricted network;
- temporary workspace cleanup;
- explicit command allowlist;
- safe handling of archives and path traversal.

This is not required for the CLI MVP, where the user controls the repository and machine, but it must shape future web architecture.

---

# 12. Technology decisions

| Area | Choice | Status | Notes |
|---|---|---|---|
| Implementation language | Python | Confirmed | First language supported by audit engine. |
| CLI | Typer | Proposed | `argparse` remains a fallback if minimizing dependencies wins. |
| Test runner | Pytest | Confirmed | Local execution first. |
| Coverage | coverage.py | Confirmed | Parse explicit availability/error states. |
| Lint | Ruff | Confirmed | Prefer structured output. |
| Security | Bandit | Confirmed | Supplement with simple local patterns later. |
| Complexity | Radon | Confirmed | Used for maintainability signals. |
| API | FastAPI | Confirmed direction | Implement after core service boundary is stable. |
| Reports | Markdown + JSON + terminal summary | Confirmed | HTML/PDF later. |
| ML | scikit-learn | Confirmed first choice | Simple baselines before heavier models. |
| Experiment tracking | MLflow | Confirmed final-model phase | Not required in the earliest MVP. |
| Storage | SQLite | Proposed initial storage | Needed when history/dashboard starts. |
| CI | GitHub Actions | Confirmed | PR integration later. |
| Containers | Docker | Confirmed direction | Packaging + later web execution isolation. |
| LLM provider | Configurable interface | Confirmed design | Specific hosted/local provider remains open. |
| Web UI | simple UI / Streamlit / templates | Open Question | Choose after engine/API exists. |

---

# 13. Scope by delivery stage

## MVP 1 — Local Repository Audit — **Confirmed**

```text
Local Python repository
→ scan
→ deterministic audit
→ rule-based scoring
→ Markdown/JSON/terminal report
```

Included:

- local path input;
- repository scanner;
- Ruff, Bandit, Radon;
- test discovery, pytest/coverage where feasible;
- README and structure checks;
- transparent category scores;
- diagnosis and prioritized rule-based plan;
- unit tests for parsers/scoring;
- good/bad sample repositories.

Excluded:

- web app;
- GitHub URL cloning;
- LLM;
- trained models;
- MLflow;
- PR automation;
- private GitHub support;
- dashboard;
- multi-language support.

## Final portfolio vision — **Confirmed direction, not MVP scope**

- all repository input modes;
- both ML classifiers;
- MLflow and reproducible model pipeline;
- LLM remediation advisor;
- GitHub URL audit;
- PR change-impact review and GitHub Actions;
- web app and report history;
- Dockerized packaging and optional monitoring.

---

# 14. Roadmap summary

| Phase | Outcome |
|---|---|
| 0 | Documentation, repository setup, interfaces and sample fixtures |
| 1 | CLI and local repository scanner |
| 2 | Deterministic tool runners and normalized evidence |
| 3 | README/structure/portfolio rules, scores, diagnosis, reports |
| 4 | Public GitHub URL audit |
| 5 | Dataset rubric, collection pipeline, feature engineering |
| 6 | Repository and portfolio classifiers with MLflow |
| 7 | LLM remediation advisor |
| 8 | PR Change Impact Review and GitHub Actions |
| 9 | Web app, uploads, history, and dashboard |
| 10 | Docker, hardening, observability, final presentation |

Detailed milestones are in [`ROADMAP.md`](ROADMAP.md).

---

# 15. Proposed repository layout

```text
drrepo/
├── drrepo/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── models.py
│   ├── input/
│   │   ├── resolver.py
│   │   ├── git.py
│   │   └── workspace.py
│   ├── scanner/
│   │   ├── repository_scanner.py
│   │   ├── file_discovery.py
│   │   └── metadata.py
│   ├── analyzers/
│   │   ├── base.py
│   │   ├── ruff_runner.py
│   │   ├── bandit_runner.py
│   │   ├── radon_runner.py
│   │   ├── pytest_runner.py
│   │   ├── coverage_runner.py
│   │   └── parsers.py
│   ├── audits/
│   │   ├── readme_auditor.py
│   │   ├── structure_auditor.py
│   │   ├── portfolio_auditor.py
│   │   └── security_patterns.py
│   ├── features/
│   │   ├── schema.py
│   │   ├── builder.py
│   │   └── validation.py
│   ├── scoring/
│   │   ├── repository_score.py
│   │   ├── portfolio_score.py
│   │   └── rules.py
│   ├── diagnosis/
│   │   ├── engine.py
│   │   ├── priority.py
│   │   └── recommendations.py
│   ├── ml/
│   │   ├── dataset.py
│   │   ├── labels.py
│   │   ├── train.py
│   │   ├── evaluate.py
│   │   ├── predict.py
│   │   └── registry.py
│   ├── llm/
│   │   ├── base.py
│   │   ├── mock_reviewer.py
│   │   ├── provider.py
│   │   ├── prompts.py
│   │   └── schemas.py
│   ├── reports/
│   │   ├── markdown_report.py
│   │   ├── json_report.py
│   │   └── terminal_summary.py
│   ├── github/
│   │   ├── diff.py
│   │   ├── actions.py
│   │   └── comments.py
│   ├── api/
│   │   ├── main.py
│   │   ├── routes.py
│   │   └── schemas.py
│   └── storage/
│       ├── database.py
│       └── repositories.py
├── docs/
├── examples/
│   ├── sample_good_repo/
│   ├── sample_bad_repo/
│   └── sample_portfolio_repo/
├── tests/
├── reports/
├── .github/workflows/
├── pyproject.toml
├── .drrepo.yml
├── Dockerfile
├── README.md
└── LICENSE
```

This is a **target layout**, not a requirement to create every folder on day one. Create modules only when a phase needs them.

---

# 16. Configuration direction

A proposed `.drrepo.yml` design:

```yaml
analysis:
  language: python
  run_tests: true
  run_coverage: true
  run_lint: true
  run_security: true
  run_complexity: true
  run_readme_audit: true
  run_structure_audit: true
  run_llm_remediation: false

thresholds:
  repository_minimum_score: 60
  portfolio_minimum_score: 70
  coverage_minimum_percentage: 60

security:
  flag_env_files: true
  block_on_critical_in_pr_mode: true

llm:
  provider: mock
  model: none
  max_context_files: 20

output:
  markdown: true
  json: true
  terminal_summary: true
```

**Open Question:** YAML versus a `pyproject.toml` section. Start with one simple configuration path and avoid supporting both too early.

---

# 17. Risks and mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| Scope explosion | The project spans audit, ML, LLM, web, CI, MLOps, and DevOps. | Enforce phased delivery and acceptance criteria. |
| Weak ML data | A classifier trained on poor labels is not credible. | Hybrid data plan, rubric, baseline comparison, limitation reporting. |
| Target leakage | Model appears accurate because it learns a rule used to make the label. | Independent labels where feasible; audit feature/label review; holdout by repository. |
| LLM inconsistency | LLM may hallucinate or output invalid structure. | Evidence-first prompts, structured schema, validation, fallback. |
| Untrusted code execution | Uploaded tests/scripts can be malicious. | Static-only web analysis first; sandbox later. |
| GitHub URL reliability | Cloning can fail or repos may be large. | Size/time limits, cleanup, clear errors, local path first. |
| Subjective scoring | Users may disagree with thresholds. | Explain evidence, expose configuration, document limitations. |
| Frontend time sink | UI may delay the actual engine. | Build CLI/API core first. |
| ML as decoration | A model trained on trivial labels adds little value. | Explicit data/labeling methodology and meaningful comparison. |

---

# 18. Engineering workflow

## Principles — **Confirmed**

1. Build a small working slice before building the next layer.
2. Preserve a stable baseline; commit after meaningful working blocks.
3. Test parsers and scoring logic early.
4. Keep raw tool output for debugging, but expose normalized models to the rest of the system.
5. Treat missing/failed/unknown evidence differently.
6. Keep the LLM optional and non-blocking initially.
7. Document major changes in this blueprint or a later decisions log.
8. Use sample repositories designed to test both happy and failure paths.

## Branch examples

```text
feature/repository-scanner
feature/static-analysis
feature/readme-structure-audit
feature/scoring-reports
feature/github-url-input
feature/dataset-pipeline
feature/readiness-classifiers
feature/llm-remediation
feature/pr-change-impact
feature/web-app
```

---

# 19. Success criteria

## MVP success

- A local Python repository can be audited with one CLI command.
- The report accurately distinguishes available, missing, failed, and unknown evidence.
- The system produces readable Markdown and machine-readable JSON.
- Scores are transparent and tied to evidence.
- The system runs on controlled sample repositories and at least one real project.

## Final portfolio-project success

- DrRepo supports both readiness models with documented datasets, evaluation, and MLflow experiments.
- The model output is compared against deterministic rules and presented with limitations.
- The LLM produces validated remediation plans grounded in findings.
- Public GitHub URL audit reuses the same core engine.
- PR Change Impact Review works through GitHub Actions.
- Docker packaging and clear documentation make the project reproducible.
- The system can be explained in a two-minute interview walkthrough without exaggerating what it does.

---

# 20. Interview narrative

> **I built DrRepo, an evidence-driven repository health and remediation platform for Python projects. The audit engine combines test and coverage results, static analysis, security scanning, complexity metrics, README and structure checks, then exposes transparent health dimensions. I added two supervised ML classifiers—repository readiness and portfolio readiness—using a documented hybrid dataset strategy and MLflow experiment tracking. An LLM layer does not replace the checks; it converts validated findings into a prioritized remediation plan. The same core engine later powers GitHub Actions-based pull request change-impact review.**

---

# 21. Immediate next step

Implement the first vertical slice:

```text
Local path
→ repository scan
→ metadata summary
→ JSON output
→ test fixture
```

Do **not** begin with the web app, LLM, classifier, dashboard, or GitHub Action. The first vertical slice establishes the evidence contract that every later component depends on.



# DrRepo — Roadmap

> **Status:** Phased implementation plan, v0.3  
> The roadmap is intentionally staged to protect the project from scope creep. A phase is complete only when its acceptance criteria are met.

---

## Delivery principles

- Build the evidence pipeline before UI, LLM, or ML features.
- Implement one vertical slice at a time and keep the baseline working.
- Do not mark planned features as completed in the README/CV.
- Treat every phase as a demoable milestone.
- Update the blueprint when a decision changes.

---

# Phase 0 — Documentation and project foundation

**Goal:** Create a clean repository and a stable planning baseline.

### Deliverables

- `README.md`
- `docs/PROJECT_BLUEPRINT.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- package skeleton
- `pyproject.toml` draft
- initial sample-repository plan
- `.gitignore`

### Acceptance criteria

- Project identity is DrRepo.
- Repository Audit is documented as the primary mode.
- Two ML classifiers are documented as final-product components, not MVP components.
- Every uncertain major feature is labeled Proposed, Deferred, or Open Question.
- The project has a clean initial commit and can be explained in one minute.

### Not included

- actual analyzer implementation;
- web UI;
- LLM;
- ML model.

---

# Phase 1 — CLI and local repository scanner

**Goal:** Accept a local Python repository path and produce normalized metadata.

### Build

- `drrepo audit <path>` command;
- input validation and repository-root handling;
- file discovery;
- metadata model;
- detection of README, tests, source, docs, dependencies, config, `.gitignore`, `.env.example`, Docker/CI signals;
- JSON metadata output.

### Acceptance criteria

- `drrepo audit ./examples/sample_good_repo` runs locally.
- Invalid paths fail with a clear message.
- Scanner can distinguish at least a good sample repo and an intentionally weak/bad sample repo.
- Scanner unit tests exist.

### Not included

- running tools;
- scoring;
- GitHub URL;
- web input.

---

# Phase 2 — Deterministic analysis evidence

**Goal:** Run core Python analysis tools and normalize their output.

### Build

- Ruff runner and parser;
- Bandit runner and parser;
- Radon runner and parser;
- common tool-result schema;
- raw output capture for debugging;
- clear status values: completed, unavailable, skipped, failed, partial.

### Acceptance criteria

- Each runner can analyze the controlled sample repositories.
- Failures in one tool do not crash the entire audit.
- Each finding retains tool, location, severity/category, and message when available.
- Parser tests cover normal, empty, and malformed/error outputs.

### Not included

- automatic remediation;
- model training;
- LLM review.

---

# Phase 3 — Tests, coverage, README, and structure audit

**Goal:** Extend evidence beyond static tool results.

### Build

- pytest discovery and runner for local mode;
- coverage collection where possible;
- README rule checks;
- repository-structure rules;
- portfolio evidence model;
- explicit unknown/missing evidence handling.

### Acceptance criteria

- Reports identify whether tests are missing, fail, pass, or cannot run.
- Coverage “unavailable” is not reported as zero.
- README audit identifies major missing sections with stable finding IDs.
- Structure auditor finds absent dependency/configuration/test/doc signals in samples.

### Decision checkpoint

Review the initial evidence schema. Do not begin ML feature engineering until the field names and semantics are stable enough to version.

---

# Phase 4 — Rule-based scoring, diagnosis, and reports

**Goal:** Turn evidence into an explainable repository and portfolio diagnosis.

### Build

- category score engine;
- repository health/readiness score;
- portfolio readiness score;
- deterministic priority matrix;
- diagnosis engine;
- terminal summary;
- JSON report;
- Markdown report.

### Acceptance criteria

- Same evidence yields the same score and diagnosis.
- Every score deduction points to an evidence-backed reason.
- Report contains scope, limitations, category scores, key findings, and a prioritized action plan.
- Runs successfully on at least one real Python repository in addition to fixtures.

### Not included

- trained ML predictions;
- LLM advice;
- GitHub URL;
- web app.

### MVP 1 exit demo

```text
Local repository
→ scan
→ evidence collection
→ health + portfolio scores
→ Markdown/JSON report
```

At this point, DrRepo is already a coherent, demoable engineering tool.

---

# Phase 5 — Public GitHub repository URL audit

**Goal:** Audit public GitHub repositories using the same core engine.

### Build

- URL validation;
- temporary workspace manager;
- clone/download logic;
- size/time/error handling;
- cleanup;
- same report contract as local audit.

### Acceptance criteria

- `drrepo audit <public-github-url>` produces a report for a controlled public test repository.
- Temporary workspaces are cleaned after a successful and failed run.
- Private repository URLs are rejected with a helpful explanation of the local/ZIP alternative.

### Not included

- OAuth/private repositories;
- web upload;
- arbitrary remote script execution beyond the configured audit plan.

---

# Phase 6 — Dataset, labels, and feature-engineering foundation

**Goal:** Prepare a credible data path for both ML classifiers.

### Build

- feature schema `v1`;
- dataset record format;
- labeling rubric draft;
- data-source metadata fields;
- dataset-builder script;
- controlled synthetic samples;
- selected public-repository collection plan;
- train/validation/test split by repository;
- deterministic baseline for comparison.

### Dataset direction

Use a flexible hybrid strategy:

- manual labels;
- selected public Python repositories;
- synthetic repositories for edge cases and test coverage;
- later audit history if labels are reliable.

### Acceptance criteria

- A row can be produced from a normalized audit report using the feature schema.
- Dataset records identify source type and label provenance.
- A documented check explains why the chosen label does not simply duplicate the rule score.
- A baseline rule classifier/report is available for comparison.

### Decision checkpoint

Freeze proposed class labels only after inspecting class distribution and rubric consistency.

---

# Phase 7 — Repository Readiness Classifier + MLflow

**Goal:** Train, evaluate, and integrate the first ML classifier.

### Build

- baseline Logistic Regression;
- at least one tree-based baseline such as Random Forest;
- evaluation script;
- confusion matrix and precision/recall/F1 reporting;
- MLflow experiment tracking;
- saved model artifact and feature-schema link;
- inference adapter;
- model prediction shown in report with model version and confidence.

### Acceptance criteria

- Experiments are reproducible from a configuration and dataset snapshot.
- MLflow records parameters, metrics, artifacts, and model information.
- The report distinguishes rule score from model prediction.
- The model is compared with a deterministic baseline.
- Limitations are shown instead of exaggerated claims.

### Not included

- model deployment registry unless MLflow usage justifies it;
- automated retraining;
- PR model.

---

# Phase 8 — Portfolio Readiness Classifier + MLflow

**Goal:** Build the second supervised model focused on public-project readiness.

### Build

- separate label rubric / feature subset as needed;
- baseline models and evaluation;
- MLflow experiments;
- portfolio prediction in report;
- feature importance/explainability artifact where supported.

### Acceptance criteria

- The model answers a distinct portfolio question rather than duplicating repository readiness.
- It uses documented presentation/reproducibility features.
- It is evaluated against a baseline and discussed with limitations.
- The final report can show a repo that is technically healthy but not portfolio-ready, or vice versa.

---

# Phase 9 — LLM remediation advisor

**Goal:** Add structured AI explanation and prioritized recommendations grounded in evidence.

### Build

- mock reviewer first;
- provider abstraction;
- bounded context builder;
- prompt templates;
- Pydantic/JSON schema validation;
- fallback behavior;
- remediation plan merged into report.

### Acceptance criteria

- LLM output never breaks a completed deterministic audit.
- Recommendations reference finding IDs/evidence where possible.
- Invalid or unavailable provider responses are handled clearly.
- The LLM does not act as the sole blocker or score authority.

### Not included

- autonomous code edits;
- agent loops;
- LangGraph unless a specific tool-use requirement appears.

---

# Phase 10 — Pull Request / Change Impact Review

**Goal:** Reuse the core engine to assess changes against a repository baseline.

### Build

- PR diff extractor;
- changed-file filter;
- baseline vs new evidence comparison;
- PR score/decision policy;
- GitHub Actions workflow;
- report artifact;
- optional PR comment after the workflow is stable.

### Acceptance criteria

- A test PR triggers the workflow.
- The report identifies changes in test status, coverage, lint/security signals, or complexity where applicable.
- Configurable policy can return `mergeable`, `needs_work`, or `blocked`.
- Hard rules are explicit and evidence-based.

### Not included

- GitHub App;
- private-repository OAuth product flow;
- automatic merge/auto-fix.

---

# Phase 11 — Web app, uploads, storage, and dashboard

**Goal:** Make the proven engine usable by non-terminal users.

### Build

- FastAPI adapter;
- simple web UI or Streamlit prototype;
- public GitHub URL input;
- report status/results page;
- ZIP/file/code-text quick-review workflows as scoped capabilities;
- SQLite history;
- before/after score comparison;
- basic dashboard.

### Security acceptance criteria

- Web upload size/file limits exist.
- Archive extraction prevents path traversal.
- Static-only analysis is the default until sandboxed execution exists.
- Temporary uploaded files are cleaned.
- Reports do not expose detected secrets in plaintext.

### Decision checkpoint

Choose UI technology only after the API/report contract is stable. Do not rebuild the analyzer for the web interface.

---

# Phase 12 — Docker, hardening, observability, and presentation polish

**Goal:** Make the project reproducible, demonstrable, and interview-ready.

### Build

- Dockerfile;
- optional Docker Compose for API/storage/dashboard;
- environment documentation;
- demo repositories and screenshots/GIF;
- CI for DrRepo’s own tests;
- optional Prometheus/Grafana only if time and value justify it;
- final README/architecture diagrams.

### Acceptance criteria

- A new user can run the core project using documented instructions.
- The demo path works reliably.
- Documentation accurately distinguishes completed features from future plans.
- The project has a concise interview walkthrough and a deeper technical explanation.

---

# Scope-control matrix

| Feature | Priority | Why |
|---|---|---|
| Local repository audit | Must | Foundation for all other modes |
| Deterministic evidence and reports | Must | Makes the product real before AI/ML layers |
| README/structure/portfolio rules | Must | Core differentiator for full-repository audits |
| Public GitHub URL audit | Should | Important product input, but reuses core engine |
| Both ML classifiers | Must for final portfolio vision | Makes ML/MLOps claims legitimate |
| MLflow | Must with trained models | Reproducible MLOps evidence |
| LLM remediation | Should | High value after evidence contract is mature |
| PR Change Impact Review | Should | Strong DevOps integration, secondary product mode |
| Web app | Should | Accessible user-facing layer, not core engine |
| Dashboard/history | Could | Strong demonstration after storage exists |
| Docker | Should | Reproducibility and deployment readiness |
| Prometheus/Grafana | Could | Nice DevOps polish, not essential |
| Kubernetes/Terraform | Deferred | Too much scope unless a clear deployment need appears |
| LangGraph agent | Deferred | Only justified by concrete multi-step tool use |
| Auto-fix code | Deferred | Risky and unnecessary for first strong version |

---

# Suggested first week

| Day | Focus | Concrete output |
|---|---|---|
| 1 | Repo setup + docs | project skeleton, docs, initial commit |
| 2 | CLI + input validation | `drrepo audit <path>` accepts local path |
| 3 | Repository scanner | metadata JSON for sample repos |
| 4 | README + structure checks | first evidence findings |
| 5 | Ruff + Bandit + Radon | normalized tool results |
| 6 | Tests/coverage | test evidence states, coverage handling |
| 7 | Scores + report draft | first Markdown/JSON audit report |

The first week is successful when the product can audit a local repository end-to-end, even with basic scoring.

---

# Definition of done for a phase

Before moving to a new phase:

1. The phase deliverables exist and run.
2. Core logic has focused tests.
3. A controlled sample proves the happy path.
4. A controlled sample proves at least one failure/error path.
5. Documentation reflects the current reality.
6. The code is committed in a stable state.

---

# Current next implementation task

Start **Phase 1** with the smallest vertical slice:

```text
Create package
→ add CLI command
→ validate local path
→ scan files/folders
→ emit repository metadata JSON
→ test it on two sample repositories
```
