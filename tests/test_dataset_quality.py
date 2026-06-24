from tests.fixtures.synthetic_audits import healthy_audit, weak_audit
from drrepo.ml.dataset import build_dataset_record
from drrepo.ml.quality import (
    summarize_label_counts,
    summarize_source_counts,
    summarize_baseline_predictions,
    build_dataset_quality_report,
)
from drrepo.ml.dataset_builder import build_dataset_records


def test_summarize_label_counts():
    a = healthy_audit()
    rec = build_dataset_record(a, "local_path", "r1", labels={"repository_readiness_label": "repository_ready", "portfolio_readiness_label": "portfolio_ready"})
    counts = summarize_label_counts([rec])
    assert counts["repository_readiness_label"]["repository_ready"] == 1
    assert counts["portfolio_readiness_label"]["portfolio_ready"] == 1


def test_summarize_source_counts():
    a = healthy_audit()
    rec = build_dataset_record(a, "github_url", "gh1")
    s = summarize_source_counts([rec])
    assert s.get("github_url") == 1


def test_summarize_baseline_predictions_handles_malformed():
    a = healthy_audit()
    rec = build_dataset_record(a, "local_path", "r1")
    # inject malformed record for baseline failure
    rec_bad = dict(rec)
    rec_bad.pop("features", None)
    res = summarize_baseline_predictions([rec, rec_bad])
    assert "error" in res["repository_readiness_baseline"]


def test_build_dataset_quality_report_and_ready_flag():
    a1 = healthy_audit()
    a2 = weak_audit()
    recs = build_dataset_records([a1, a2], "local_path", ["r1", "r2"])    
    # unlabeled dataset should not be ready
    report = build_dataset_quality_report(recs)
    assert report["report_version"] == "v1"
    assert report["dataset_ready_for_training"] is False

    # label one record with strong provenance
    recs_labeled = list(recs)
    recs_labeled[0]["labels"] = {"repository_readiness_label": "repository_ready"}
    recs_labeled[0]["label_provenance"] = {"rubric_version": "v1-draft", "method": "manual_review", "labeler": "qa", "reviewed_evidence": ["tests"]}
    report2 = build_dataset_quality_report(recs_labeled)
    # now there is at least one labeled record; if no leakage and no validation errors, dataset_ready may be True
    assert "feature_schema_versions" in report2
