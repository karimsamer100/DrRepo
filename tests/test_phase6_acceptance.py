import json
from pathlib import Path

from drrepo.audit import build_audit
from drrepo.features import build_feature_row, validate_feature_row, FEATURE_SCHEMA_VERSION
from drrepo.ml.dataset import build_dataset_record, validate_dataset_record, read_jsonl
from drrepo.ml.dataset_builder import build_dataset_records, validate_dataset
from drrepo.ml.quality import build_dataset_quality_report
from drrepo.ml.artifacts import build_dataset_artifact_manifest, validate_dataset_artifact_manifest
from drrepo.ml.audit_dataset import export_dataset_from_audit_files
from tests.fixtures.synthetic_audits import healthy_audit, weak_audit
from drrepo.ml.leakage import detect_dataset_leakage_risks


def test_phase6_builds_feature_row_from_real_sample_audit():
    audit = build_audit("examples/sample_good_repo")
    fr = build_feature_row(audit)
    assert validate_feature_row(fr) == []
    assert fr.get("schema_version") == FEATURE_SCHEMA_VERSION
    for k in ("total_files", "python_files", "overall_score", "repository_health_score", "portfolio_readiness_score"):
        assert k in fr


def test_phase6_builds_valid_dataset_record_from_real_sample_audit():
    audit = build_audit("examples/sample_good_repo")
    rec = build_dataset_record(audit, "fixture", "sample_good_repo")
    assert validate_dataset_record(rec) == []
    assert rec.get("feature_schema_version") == "v1"
    assert "schema_version" not in rec.get("features", {})


def test_phase6_dataset_quality_report_for_real_sample_audits():
    a1 = build_audit("examples/sample_good_repo")
    a2 = build_audit("examples/sample_bad_repo")
    recs = build_dataset_records([a1, a2], "fixture", ["sample_good_repo", "sample_bad_repo"])    
    val_errs = validate_dataset(recs)
    assert val_errs == []
    report = build_dataset_quality_report(recs)
    assert report.get("report_version") == "v1"
    assert report.get("record_count") == 2
    assert report.get("validation_errors") == []
    sc = report.get("split_counts") or {}
    for part in ("train", "validation", "test"):
        assert part in sc
    assert "baseline_prediction_counts" in report


def test_phase6_artifact_manifest_for_real_sample_audits():
    a1 = build_audit("examples/sample_good_repo")
    a2 = build_audit("examples/sample_bad_repo")
    recs = build_dataset_records([a1, a2], "fixture", ["sample_good_repo", "sample_bad_repo"])    
    m1 = build_dataset_artifact_manifest(recs, "phase6test", description="d")
    m2 = build_dataset_artifact_manifest(recs, "phase6test", description="d")
    assert validate_dataset_artifact_manifest(m1) == []
    assert m1.get("dataset_fingerprint") == m2.get("dataset_fingerprint")


def test_phase6_export_dataset_from_saved_audit_json_files(tmp_path):
    a1 = build_audit("examples/sample_good_repo")
    a2 = build_audit("examples/sample_bad_repo")
    p1 = tmp_path / "good.json"
    p2 = tmp_path / "bad.json"
    p1.write_text(json.dumps(a1), encoding="utf-8")
    p2.write_text(json.dumps(a2), encoding="utf-8")

    dataset_path = tmp_path / "out.jsonl"
    manifest_path = tmp_path / "manifest.json"
    manifest = export_dataset_from_audit_files([p1, p2], dataset_path, manifest_path, "phase6export", dataset_description="d")
    assert dataset_path.exists()
    assert manifest_path.exists()
    recs = read_jsonl(dataset_path)
    assert len(recs) == 2
    assert "quality_report" in manifest


def test_phase6_labeled_synthetic_dataset_can_be_ready_for_training():
    a = healthy_audit()
    b = weak_audit()
    labels = {"a": {"repository_readiness_label": "repository_ready"}, "b": {"repository_readiness_label": "repository_ready"}}
    prov = {
        "a": {"rubric_version": "v1-draft", "method": "manual_review", "labeler": "qa", "reviewed_evidence": ["tests"]},
        "b": {"rubric_version": "v1-draft", "method": "manual_review", "labeler": "qa", "reviewed_evidence": ["tests"]},
    }
    recs = build_dataset_records([a, b], "synthetic", ["a", "b"], labels_by_identifier=labels, label_provenance_by_identifier=prov)
    report = build_dataset_quality_report(recs)
    assert report.get("dataset_ready_for_training") is True
    assert detect_dataset_leakage_risks(recs) == []


def test_phase6_weak_label_provenance_blocks_training_readiness():
    a = healthy_audit()
    labels = {"x": {"repository_readiness_label": "repository_ready"}}
    prov = {"x": {"rubric_version": "v1-draft", "method": "rule_score", "labeler": "auto", "reviewed_evidence": []}}
    recs = build_dataset_records([a], "synthetic", ["x"], labels_by_identifier=labels, label_provenance_by_identifier=prov)
    report = build_dataset_quality_report(recs)
    assert report.get("dataset_ready_for_training") is False
    assert report.get("leakage_warnings")
