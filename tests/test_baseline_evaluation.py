from copy import deepcopy
from drrepo.ml.evaluation import evaluate_repository_baseline, evaluate_portfolio_baseline, evaluate_split_baselines
from drrepo.ml.dataset import build_dataset_record
from tests.fixtures.synthetic_audits import healthy_audit, weak_audit


def test_evaluate_repository_baseline_ignores_unlabeled():
    a = healthy_audit()
    r_unlabeled = build_dataset_record(a, "synthetic", "u")
    r_labeled = build_dataset_record(a, "synthetic", "l", labels={"repository_readiness_label": "repository_ready"})
    res = evaluate_repository_baseline([r_unlabeled, r_labeled])
    assert res["record_ids"] == [r_labeled["record_id"]]


def test_evaluate_repository_baseline_report_version_and_metrics_present():
    a = healthy_audit()
    r = build_dataset_record(a, "synthetic", "r", labels={"repository_readiness_label": "repository_ready"})
    res = evaluate_repository_baseline([r])
    assert res["report_version"] == "v1"
    assert "metrics" in res and "record_ids" in res


def test_evaluate_repository_baseline_accuracy_perfect_when_labels_match_baseline():
    a = healthy_audit()
    # healthy_audit should trigger repository_ready baseline
    r = build_dataset_record(a, "synthetic", "r", labels={"repository_readiness_label": "repository_ready"})
    res = evaluate_repository_baseline([r])
    assert res["metrics"]["accuracy"] == 1.0


def test_evaluate_portfolio_baseline_works_for_portfolio_labels():
    a = healthy_audit()
    r = build_dataset_record(a, "synthetic", "r", labels={"portfolio_readiness_label": "portfolio_ready"})
    res = evaluate_portfolio_baseline([r])
    assert res["report_version"] == "v1"


def test_evaluate_split_baselines_returns_expected_structure():
    a = healthy_audit()
    r1 = build_dataset_record(a, "synthetic", "r1", labels={"repository_readiness_label": "repository_ready"})
    r2 = build_dataset_record(a, "synthetic", "r2", labels={"repository_readiness_label": "repository_ready"})
    splits = {"train": [r1], "validation": [r2], "test": []}
    res = evaluate_split_baselines(splits)
    assert set(res.keys()) == {"train", "validation", "test"}
    assert "repository" in res["train"] and "portfolio" in res["train"]


def test_evaluate_split_baselines_rejects_missing_keys():
    try:
        evaluate_split_baselines({"train": [], "test": []})
        assert False
    except ValueError:
        pass


def test_baseline_evaluation_does_not_mutate_input_records():
    a = healthy_audit()
    r = build_dataset_record(a, "synthetic", "r", labels={"repository_readiness_label": "repository_ready"})
    before = deepcopy(r)
    _ = evaluate_repository_baseline([r])
    assert r == before
