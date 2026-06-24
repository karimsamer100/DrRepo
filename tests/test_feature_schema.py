from drrepo.features.schema import (
    FEATURE_SCHEMA_VERSION,
    FEATURE_FIELDS,
    get_feature_schema,
    validate_feature_row,
)


def test_schema_version_and_fields():
    s = get_feature_schema()
    assert s["schema_version"] == FEATURE_SCHEMA_VERSION
    assert isinstance(s["fields"], list)
    assert tuple(s["fields"]) == FEATURE_FIELDS
    assert s["field_count"] == len(FEATURE_FIELDS)


def test_validate_missing_and_version_and_forbidden():
    # missing fields should be reported
    errs = validate_feature_row({})
    assert any("missing schema_version" in e or "missing field" in e for e in errs)

    # wrong version
    row = {"schema_version": "bad"}
    # add one required field to ensure both errors appear
    row[FEATURE_FIELDS[0]] = 1
    errs = validate_feature_row(row)
    assert any("schema_version must be" in e for e in errs)

    # forbidden keys
    row = {"schema_version": FEATURE_SCHEMA_VERSION, FEATURE_FIELDS[0]: 1, "label": "x"}
    errs = validate_feature_row(row)
    assert any("forbidden key present: label" in e for e in errs)
