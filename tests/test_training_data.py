from copy import deepcopy
from drrepo.ml.training_data import (
    get_ordered_feature_names,
    extract_feature_matrix,
    extract_labels,
    filter_labeled_records,
    prepare_supervised_dataset,
    prepare_split_supervised_datasets,
    REPOSITORY_LABEL_FIELD,
    PORTFOLIO_LABEL_FIELD,
)
from drrepo.features.schema import FEATURE_FIELDS
from tests.fixtures.synthetic_audits import healthy_audit
from drrepo.ml.dataset import build_dataset_record


def test_get_ordered_feature_names_matches_schema():
    assert get_ordered_feature_names() == list(FEATURE_FIELDS)


def test_extract_feature_matrix_preserves_order():
    a = healthy_audit()
    r1 = build_dataset_record(a, "synthetic", "r1")
    r2 = build_dataset_record(a, "synthetic", "r2")
    mat = extract_feature_matrix([r1, r2])
    assert len(mat) == 2


def test_extract_feature_matrix_converts_booleans_to_floats():
    a = healthy_audit()
    r = build_dataset_record(a, "synthetic", "r")
    mat = extract_feature_matrix([r])
    # find index of has_readme
    idx = get_ordered_feature_names().index("has_readme")
    assert mat[0][idx] in (0.0, 1.0)


def test_extract_feature_matrix_converts_numbers_to_floats():
    a = healthy_audit()
    r = build_dataset_record(a, "synthetic", "r")
    mat = extract_feature_matrix([r])
    idx = get_ordered_feature_names().index("total_files")
    assert isinstance(mat[0][idx], float)


def test_extract_feature_matrix_defaults_missing_to_zero():
    r = {"record_id": "x", "features": {}}
    mat = extract_feature_matrix([r])
    assert all(v == 0.0 for v in mat[0])


def test_extract_feature_matrix_rejects_string_values():
    r = {"record_id": "x", "features": {"total_files": "bad"}}
    try:
        extract_feature_matrix([r])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_filter_labeled_records_returns_only_repository_labels():
    a = healthy_audit()
    r1 = build_dataset_record(a, "synthetic", "r1", labels={REPOSITORY_LABEL_FIELD: "repository_ready"})
    r2 = build_dataset_record(a, "synthetic", "r2")
    filtered = filter_labeled_records([r1, r2], REPOSITORY_LABEL_FIELD)
    assert len(filtered) == 1 and filtered[0]["source"]["identifier"] == "r1"


def test_extract_labels_returns_repository_labels_in_order():
    a = healthy_audit()
    r1 = build_dataset_record(a, "synthetic", "r1", labels={REPOSITORY_LABEL_FIELD: "repository_ready"})
    r2 = build_dataset_record(a, "synthetic", "r2", labels={REPOSITORY_LABEL_FIELD: "needs_major_improvement"})
    labs = extract_labels([r1, r2], REPOSITORY_LABEL_FIELD)
    assert labs == ["repository_ready", "needs_major_improvement"]


def test_extract_labels_supports_portfolio_labels():
    a = healthy_audit()
    r = build_dataset_record(a, "synthetic", "r", labels={PORTFOLIO_LABEL_FIELD: "portfolio_ready"})
    labs = extract_labels([r], PORTFOLIO_LABEL_FIELD)
    assert labs == ["portfolio_ready"]


def test_extract_labels_rejects_unsupported_label_field():
    try:
        extract_labels([], "unknown")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_prepare_supervised_dataset_returns_expected_structure():
    a = healthy_audit()
    r = build_dataset_record(a, "synthetic", "r", labels={REPOSITORY_LABEL_FIELD: "repository_ready"})
    ds = prepare_supervised_dataset([r], REPOSITORY_LABEL_FIELD)
    assert ds["record_count"] == 1
    assert len(ds["X"]) == 1 and len(ds["y"]) == 1 and len(ds["record_ids"]) == 1


def test_prepare_supervised_dataset_handles_no_labeled_records():
    a = healthy_audit()
    r = build_dataset_record(a, "synthetic", "r")
    ds = prepare_supervised_dataset([r], REPOSITORY_LABEL_FIELD)
    assert ds["record_count"] == 0
    assert ds["X"] == [] and ds["y"] == [] and ds["record_ids"] == []


def test_prepare_split_supervised_datasets_returns_splits_and_stable_features():
    a = healthy_audit()
    r1 = build_dataset_record(a, "synthetic", "r1", labels={REPOSITORY_LABEL_FIELD: "repository_ready"})
    r2 = build_dataset_record(a, "synthetic", "r2", labels={REPOSITORY_LABEL_FIELD: "needs_major_improvement"})
    splits = {"train": [r1], "validation": [r2], "test": []}
    out = prepare_split_supervised_datasets(splits, REPOSITORY_LABEL_FIELD)
    assert set(out.keys()) == {"train", "validation", "test"}
    fn_train = out["train"]["feature_names"]
    fn_val = out["validation"]["feature_names"]
    assert fn_train == fn_val


def test_prepare_split_supervised_datasets_rejects_missing_keys():
    try:
        prepare_split_supervised_datasets({"train": [], "test": []}, REPOSITORY_LABEL_FIELD)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_input_records_not_mutated():
    a = healthy_audit()
    r = build_dataset_record(a, "synthetic", "r", labels={REPOSITORY_LABEL_FIELD: "repository_ready"})
    records = [deepcopy(r)]
    before = deepcopy(records)
    _ = prepare_supervised_dataset(records, REPOSITORY_LABEL_FIELD)
    assert records == before
