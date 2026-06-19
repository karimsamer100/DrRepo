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
