from drrepo.ml.dataset_builder import build_dataset_records, validate_dataset
from drrepo.ml.dataset import build_dataset_record


def make_audits(n):
    audits = []
    ids = []
    for i in range(n):
        audits.append({"metadata": {"total_files": i + 1, "total_directories": 0, "python_files": 1}})
        ids.append(f"repo{i}")
    return audits, ids


def test_build_preserves_order_and_matches_labels_and_meta():
    audits, ids = make_audits(3)
    labels_by_id = {"repo1": {"repository_readiness_label": "repository_ready"}}
    prov = {"repo1": {"rubric_version": "v1-draft", "method": "manual", "labeler": "me"}}
    src_meta = {"repo2": {"branch": "dev"}}
    recs = build_dataset_records(audits, "local_path", ids, labels_by_identifier=labels_by_id, label_provenance_by_identifier=prov, source_metadata_by_identifier=src_meta)
    assert len(recs) == 3
    # order preserved
    assert recs[0]["source"]["identifier"] == "repo0"
    # labels matched
    assert recs[1]["labels"].get("repository_readiness_label") == "repository_ready"
    # provenance matched
    assert recs[1]["label_provenance"].get("labeler") == "me"
    # source metadata matched
    assert recs[2]["source"].get("branch") == "dev"


def test_mismatched_lengths_raises():
    audits, ids = make_audits(2)
    try:
        build_dataset_records(audits, "local_path", ["a"])
        assert False
    except ValueError:
        pass


def test_validate_dataset_detects_duplicates_and_invalid():
    audits, ids = make_audits(2)
    recs = build_dataset_records(audits, "local_path", ids)
    # duplicate id
    recs.append(recs[0])
    errs = validate_dataset(recs)
    assert any("duplicate record_id" in e for e in errs)
    # duplicate source pair
    recs2 = build_dataset_records(audits, "local_path", ids)
    recs2.append(recs2[0].copy())
    errs2 = validate_dataset(recs2)
    assert any("duplicate source pair" in e for e in errs2)
