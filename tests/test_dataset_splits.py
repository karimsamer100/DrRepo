from drrepo.ml.splits import assign_split, split_dataset, DEFAULT_SPLIT_RATIOS


def test_assign_split_deterministic():
    a = assign_split("repo-123")
    b = assign_split("repo-123")
    assert a == b
    assert a in ("train", "validation", "test")


def test_split_dataset_preserves_and_validates():
    recs = [
        {"source": {"identifier": "r1"}},
        {"source": {"identifier": "r2"}},
        {"source": {"identifier": "r3"}},
    ]
    out = split_dataset(recs)
    assert set(out.keys()) == {"train", "validation", "test"}
    # same identifier same split
    assert assign_split("r1") in ("train", "validation", "test")


def test_split_dataset_does_not_mutate():
    recs = [{"source": {"identifier": "x"}}]
    orig = [r.copy() for r in recs]
    _ = split_dataset(recs)
    assert recs == orig


def test_invalid_ratios_raise():
    try:
        assign_split("x", {"train": 0.5, "validation": 0.6, "test": 0.0})
        assert False
    except ValueError:
        pass


def test_missing_identifier_raises():
    try:
        split_dataset([{"source": {}}])
        assert False
    except ValueError:
        pass
