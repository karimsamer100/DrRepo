from tests.fixtures.synthetic_audits import healthy_audit
from drrepo.ml.dataset import build_dataset_record
from drrepo.ml.artifacts import build_dataset_artifact_manifest, validate_dataset_artifact_manifest


def test_artifact_manifest_and_validation_is_deterministic():
    a1 = healthy_audit()
    rec1 = build_dataset_record(a1, "local_path", "r1")
    rec2 = build_dataset_record(a1, "local_path", "r2")
    manifest1 = build_dataset_artifact_manifest([rec1, rec2], "mydata", description="d")
    manifest2 = build_dataset_artifact_manifest([rec1, rec2], "mydata", description="d")
    assert manifest1["artifact_version"] == "v1"
    assert manifest1["quality_report"]
    assert manifest1["dataset_fingerprint"] == manifest2["dataset_fingerprint"]

    # change name changes fingerprint
    manifest3 = build_dataset_artifact_manifest([rec1, rec2], "other", description="d")
    assert manifest3["dataset_fingerprint"] != manifest1["dataset_fingerprint"]

    # change records changes fingerprint
    manifest4 = build_dataset_artifact_manifest([rec1], "mydata")
    assert manifest4["dataset_fingerprint"] != manifest1["dataset_fingerprint"]

    # validation
    assert validate_dataset_artifact_manifest(manifest1) == []

    bad = dict(manifest1)
    bad["artifact_version"] = "bad"
    errs = validate_dataset_artifact_manifest(bad)
    assert any("artifact_version" in e for e in errs)
