import json
from pathlib import Path

from tests.fixtures.synthetic_audits import healthy_audit, weak_audit
from drrepo.ml.audit_dataset import (
    load_audit_json,
    build_dataset_records_from_audit_files,
    export_dataset_from_audit_files,
)
from drrepo.ml.dataset import read_jsonl


def test_load_audit_json_valid(tmp_path):
    p = tmp_path / "sample.json"
    p.write_text(json.dumps(healthy_audit()), encoding="utf-8")
    d = load_audit_json(p)
    assert isinstance(d, dict)


def test_load_audit_json_list_root_rejected(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    try:
        load_audit_json(p)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_build_dataset_records_from_audit_files_one_per_file(tmp_path):
    a1 = tmp_path / "one.json"
    a1.write_text(json.dumps(healthy_audit()), encoding="utf-8")
    a2 = tmp_path / "two.json"
    a2.write_text(json.dumps(weak_audit()), encoding="utf-8")
    recs = build_dataset_records_from_audit_files([a1, a2], source_type="manual")
    assert len(recs) == 2


def test_build_dataset_records_from_audit_files_uses_file_stems(tmp_path):
    a = tmp_path / "sample_good_repo.json"
    a.write_text(json.dumps(healthy_audit()), encoding="utf-8")
    recs = build_dataset_records_from_audit_files([a], source_type="manual")
    assert recs[0]["source"]["identifier"] == "sample_good_repo"


def test_build_dataset_records_preserves_order(tmp_path):
    a1 = tmp_path / "a.json"
    a2 = tmp_path / "b.json"
    a1.write_text(json.dumps(healthy_audit()), encoding="utf-8")
    a2.write_text(json.dumps(weak_audit()), encoding="utf-8")
    recs = build_dataset_records_from_audit_files([a2, a1], source_type="manual")
    assert recs[0]["source"]["identifier"] == "b"
    assert recs[1]["source"]["identifier"] == "a"


def test_build_dataset_records_applies_labels_by_identifier(tmp_path):
    a = tmp_path / "lab.json"
    a.write_text(json.dumps(healthy_audit()), encoding="utf-8")
    labels = {"lab": {"repository_readiness_label": "repository_ready"}}
    recs = build_dataset_records_from_audit_files([a], source_type="manual", labels_by_identifier=labels)
    assert recs[0]["labels"]["repository_readiness_label"] == "repository_ready"


def test_export_writes_dataset_and_manifest_and_manifest_matches(tmp_path):
    a1 = tmp_path / "one.json"
    a1.write_text(json.dumps(healthy_audit()), encoding="utf-8")
    dataset_path = tmp_path / "data.jsonl"
    manifest_path = tmp_path / "manifest.json"
    manifest = export_dataset_from_audit_files([a1], dataset_path, manifest_path, "mydataset", dataset_description="d")
    assert manifest_path.exists()
    assert dataset_path.exists()
    # read back manifest
    m2 = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert m2 == manifest
    assert "quality_report" in manifest
    # read dataset back
    recs = read_jsonl(dataset_path)
    assert isinstance(recs, list) and len(recs) == 1


def test_export_with_strong_provenance_can_be_ready(tmp_path):
    a1 = tmp_path / "labeled.json"
    a1.write_text(json.dumps(healthy_audit()), encoding="utf-8")
    labels = {"labeled": {"repository_readiness_label": "repository_ready"}}
    prov = {"labeled": {"rubric_version": "v1-draft", "method": "manual_review", "labeler": "qa", "reviewed_evidence": ["tests"]}}
    dataset_path = tmp_path / "data2.jsonl"
    manifest_path = tmp_path / "manifest2.json"
    manifest = export_dataset_from_audit_files([a1], dataset_path, manifest_path, "mydataset2", labels_by_identifier=labels, label_provenance_by_identifier=prov)
    assert manifest.get("quality_report")
    # dataset_ready_for_training may appear inside quality report
    assert "dataset_ready_for_training" in manifest["quality_report"]
