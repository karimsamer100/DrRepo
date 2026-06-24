from tests.fixtures.synthetic_audits import healthy_audit, weak_audit, failing_tests_audit
from drrepo.ml.dataset import build_dataset_record, validate_dataset_record
from drrepo.ml.dataset_builder import build_dataset_records, validate_dataset
from drrepo.ml.splits import split_dataset
from drrepo.ml.baseline import predict_record_baseline
from drrepo.ml.leakage import detect_label_leakage_risks


def test_synthetic_records_build_and_validate():
    a1 = healthy_audit()
    a2 = weak_audit()
    rec1 = build_dataset_record(a1, "local_path", "healthy")
    rec2 = build_dataset_record(a2, "local_path", "weak")
    assert validate_dataset_record(rec1) == []
    assert validate_dataset_record(rec2) == []

    recs = build_dataset_records([a1, a2], "local_path", ["healthy", "weak"])
    assert validate_dataset(recs) == []


def test_splitting_and_baseline_on_synthetic():
    a1 = healthy_audit()
    a2 = failing_tests_audit()
    recs = build_dataset_records([a1, a2], "local_path", ["h", "f"])    
    splits = split_dataset(recs)
    assert set(splits.keys()) == {"train", "validation", "test"}

    for rec in recs:
        base = predict_record_baseline(rec)
        assert "baseline_version" in base


def test_labeled_synthetic_with_strong_provenance_has_no_leakage():
    a1 = healthy_audit()
    rec = build_dataset_record(a1, "local_path", "r1", labels={"repository_readiness_label": "repository_ready"}, label_provenance={"rubric_version": "v1-draft", "method": "manual_review", "labeler": "qa", "reviewed_evidence": ["tests", "readme"]})
    assert detect_label_leakage_risks(rec) == []
