from drrepo.ml.labels import get_label_rubric, validate_labels, LABEL_RUBRIC_VERSION


def test_get_label_rubric_contents():
    r = get_label_rubric()
    assert r.get("rubric_version") == LABEL_RUBRIC_VERSION
    assert "repository_readiness_labels" in r
    assert "portfolio_readiness_labels" in r


def test_validate_labels_accepts_empty():
    assert validate_labels({}) == []


def test_validate_labels_accepts_valid():
    labels = {"repository_readiness_label": "repository_ready", "portfolio_readiness_label": "portfolio_ready"}
    assert validate_labels(labels) == []


def test_validate_labels_unknown_key_rejected():
    errs = validate_labels({"unknown": "x"})
    assert any("unknown label key" in e for e in errs)


def test_validate_labels_invalid_values_rejected():
    errs = validate_labels({"repository_readiness_label": "bad"})
    assert any("invalid repository_readiness_label" in e for e in errs)

    errs = validate_labels({"portfolio_readiness_label": "bad"})
    assert any("invalid portfolio_readiness_label" in e for e in errs)
