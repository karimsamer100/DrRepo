import json

from drrepo.ml.dataset import (
    build_dataset_record,
    validate_dataset_record,
    write_jsonl,
    read_jsonl,
    DATASET_RECORD_VERSION,
    ALLOWED_SOURCE_TYPES,
)
from drrepo.features.schema import FEATURE_FIELDS, FEATURE_SCHEMA_VERSION


def make_minimal_audit():
    return {"metadata": {"total_files": 1, "total_directories": 0, "python_files": 1, "test_files": 0}}


def test_build_record_basic():
    audit = make_minimal_audit()
    rec = build_dataset_record(audit, "local_path", "./repo")
    assert rec["record_version"] == DATASET_RECORD_VERSION
    assert rec["feature_schema_version"] == FEATURE_SCHEMA_VERSION
    # features contains all FEATURE_FIELDS
    for f in FEATURE_FIELDS:
        assert f in rec["features"]
    # schema_version must not be inside features
    assert "schema_version" not in rec["features"]


def test_source_metadata_merge_and_protection():
    audit = make_minimal_audit()
    sm = {"branch": "main", "note": "xyz"}
    rec = build_dataset_record(audit, "local_path", "./repo", source_metadata=sm)
    assert rec["source"]["type"] == "local_path"
    assert rec["source"]["identifier"] == "./repo"
    assert rec["source"]["branch"] == "main"

    # cannot override type/identifier
    try:
        build_dataset_record(audit, "local_path", "./repo", source_metadata={"type": "github_url"})
        assert False, "should have raised"
    except ValueError:
        pass


def test_record_id_deterministic():
    audit = make_minimal_audit()
    r1 = build_dataset_record(audit, "local_path", "./repo")
    r2 = build_dataset_record(audit, "local_path", "./repo")
    assert r1["record_id"] == r2["record_id"]

    r3 = build_dataset_record(audit, "local_path", "./repo2")
    assert r1["record_id"] != r3["record_id"]


def test_validate_unlabeled_record_accepts():
    audit = make_minimal_audit()
    rec = build_dataset_record(audit, "local_path", "./repo")
    errs = validate_dataset_record(rec)
    assert errs == []


def test_validate_labeled_record_requires_provenance():
    audit = make_minimal_audit()
    labels = {"repository_readiness_label": "repository_ready"}
    rec = build_dataset_record(audit, "local_path", "./repo", labels=labels, label_provenance={"rubric_version": "v1-draft", "method": "manual", "labeler": "me"})
    assert validate_dataset_record(rec) == []

    # missing provenance
    rec2 = build_dataset_record(audit, "local_path", "./repo", labels=labels)
    errs = validate_dataset_record(rec2)
    assert any("label_provenance" in e or "rubric_version" in e for e in errs)


def test_validate_invalid_source_type_rejected():
    audit = make_minimal_audit()
    try:
        build_dataset_record(audit, "bad", "id")
        assert False
    except ValueError:
        pass


def test_missing_feature_fields_rejected():
    audit = make_minimal_audit()
    rec = build_dataset_record(audit, "local_path", "./repo")
    # remove a feature
    rec2 = dict(rec)
    rec2["features"] = dict(rec2["features"])
    # drop one required feature
    dropped = FEATURE_FIELDS[0]
    rec2["features"].pop(dropped, None)
    errs = validate_dataset_record(rec2)
    assert any(dropped in e for e in errs)


def test_jsonl_roundtrip(tmp_path):
    audit = make_minimal_audit()
    rec = build_dataset_record(audit, "local_path", "./repo")
    p = tmp_path / "data.jsonl"
    write_jsonl([rec], p)
    out = read_jsonl(p)
    assert isinstance(out, list) and len(out) == 1
    assert out[0]["record_id"] == rec["record_id"]
