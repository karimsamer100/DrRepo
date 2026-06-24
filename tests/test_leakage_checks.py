from drrepo.ml.leakage import detect_label_leakage_risks, detect_dataset_leakage_risks
from tests.fixtures.synthetic_audits import healthy_audit, weak_audit
from drrepo.ml.dataset import build_dataset_record


def test_unlabeled_record_no_risks():
    audit = healthy_audit()
    rec = build_dataset_record(audit, "local_path", "r1")
    assert detect_label_leakage_risks(rec) == []


def test_detects_rule_score_method_risk():
    audit = healthy_audit()
    rec = build_dataset_record(audit, "local_path", "r2", labels={"repository_readiness_label": "repository_ready"}, label_provenance={"method": "rule_score"})
    risks = detect_label_leakage_risks(rec)
    assert any("weak provenance" in r or "rule_score" in r for r in risks)


def test_detects_missing_reviewed_evidence():
    audit = healthy_audit()
    rec = build_dataset_record(audit, "local_path", "r3", labels={"repository_readiness_label": "repository_ready"}, label_provenance={"method": "manual_review"})
    risks = detect_label_leakage_risks(rec)
    assert any("reviewed_evidence" in r for r in risks)


def test_no_flag_when_provenance_strong_even_if_matches_baseline():
    audit = healthy_audit()
    rec = build_dataset_record(audit, "local_path", "r4", labels={"repository_readiness_label": "repository_ready"}, label_provenance={"method": "manual_review", "rubric_version": "v1-draft", "labeler": "bob", "reviewed_evidence": ["tests"]})
    risks = detect_label_leakage_risks(rec)
    assert risks == []


def test_dataset_level_includes_index_and_identifier_and_detects_all_weak_matches():
    audits = [weak_audit(), weak_audit()]
    recs = [build_dataset_record(a, "local_path", f"r{i}", labels={"repository_readiness_label": "needs_improvement"}, label_provenance={"method": "baseline_prediction"}) for i, a in enumerate(audits)]
    warns = detect_dataset_leakage_risks(recs)
    assert any("record[0]" in w or "record[1]" in w for w in warns)
    assert any("All labeled records match baseline" in w for w in warns)
