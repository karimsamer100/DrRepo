from drrepo.ml.rubric import (
    RUBRIC_VERSION,
    get_full_labeling_rubric,
    get_repository_readiness_rubric,
    get_portfolio_readiness_rubric,
    validate_label_provenance_for_training,
)


def test_full_rubric_contains_version_and_warning():
    r = get_full_labeling_rubric()
    assert r.get("rubric_version") == RUBRIC_VERSION
    assert "leakage_warning" in r


def test_repository_and_portfolio_rubrics_include_labels():
    rr = get_repository_readiness_rubric()
    pr = get_portfolio_readiness_rubric()
    assert any(l["label"] == "repository_ready" for l in rr["labels"])
    assert any(l["label"] == "portfolio_ready" for l in pr["labels"])


def test_validate_label_provenance_accepts_empty():
    assert validate_label_provenance_for_training({}, {}) == []


def test_validate_label_provenance_accepts_strong():
    labels = {"repository_readiness_label": "repository_ready"}
    prov = {"rubric_version": RUBRIC_VERSION, "method": "manual_review", "labeler": "alice", "reviewed_evidence": ["tests", "readme"]}
    assert validate_label_provenance_for_training(labels, prov) == []


def test_validate_label_provenance_rejects_weak_method():
    labels = {"repository_readiness_label": "repository_ready"}
    prov = {"rubric_version": RUBRIC_VERSION, "method": "rule_score", "labeler": "alice", "reviewed_evidence": ["tests"]}
    errs = validate_label_provenance_for_training(labels, prov)
    assert any("weak method" in e or "rule_score" in e for e in errs)


def test_validate_label_provenance_requires_reviewed_evidence():
    labels = {"repository_readiness_label": "repository_ready"}
    prov = {"rubric_version": RUBRIC_VERSION, "method": "manual_review", "labeler": "alice", "reviewed_evidence": []}
    errs = validate_label_provenance_for_training(labels, prov)
    assert any("reviewed_evidence" in e for e in errs)
