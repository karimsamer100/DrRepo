from drrepo.ml.evaluation import confusion_matrix, classification_metrics


def test_confusion_matrix_counts_predictions():
    y_true = ["a", "b", "a", "c"]
    y_pred = ["a", "b", "c", "c"]
    cm = confusion_matrix(y_true, y_pred)
    assert cm["a"]["a"] == 1
    assert cm["a"]["c"] == 1
    assert cm["b"]["b"] == 1
    assert cm["c"]["c"] == 1


def test_confusion_matrix_includes_zero_count_labels():
    y_true = ["x"]
    y_pred = ["y"]
    cm = confusion_matrix(y_true, y_pred, labels=["x", "y", "z"])
    assert cm["z"]["x"] == 0
    assert cm["x"]["z"] == 0


def test_confusion_matrix_length_mismatch_raises():
    try:
        confusion_matrix(["a"], [])
        assert False
    except ValueError:
        pass


def test_classification_metrics_perfect():
    y_true = ["p", "q", "p"]
    y_pred = ["p", "q", "p"]
    m = classification_metrics(y_true, y_pred)
    assert m["accuracy"] == 1.0
    assert m["macro_f1"] == 1.0


def test_classification_metrics_partial():
    y_true = ["a", "a", "b", "b"]
    y_pred = ["a", "b", "b", "a"]
    m = classification_metrics(y_true, y_pred)
    assert m["sample_count"] == 4
    assert "per_class" in m and "confusion_matrix" in m


def test_classification_metrics_empty_inputs():
    m = classification_metrics([], [])
    assert m["sample_count"] == 0
    assert m["accuracy"] == 0.0


def test_classification_metrics_zero_division_safety():
    # all predictions to a class with no true positives
    y_true = ["a", "b"]
    y_pred = ["c", "c"]
    m = classification_metrics(y_true, y_pred)
    # ensure no exceptions and metrics present
    assert "per_class" in m


def test_classification_metrics_raises_on_length_mismatch():
    try:
        classification_metrics(["a"], [])
        assert False
    except ValueError:
        pass
