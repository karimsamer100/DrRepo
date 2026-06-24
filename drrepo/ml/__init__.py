from .labels import LABEL_RUBRIC_VERSION, get_label_rubric, validate_labels
from .dataset import (
    DATASET_RECORD_VERSION,
    ALLOWED_SOURCE_TYPES,
    build_dataset_record,
    validate_dataset_record,
    write_jsonl,
    read_jsonl,
)

__all__ = [
    "LABEL_RUBRIC_VERSION",
    "get_label_rubric",
    "validate_labels",
    "DATASET_RECORD_VERSION",
    "ALLOWED_SOURCE_TYPES",
    "build_dataset_record",
    "validate_dataset_record",
    "write_jsonl",
    "read_jsonl",
]

from .quality import build_dataset_quality_report, summarize_label_counts
from .artifacts import build_dataset_artifact_manifest, validate_dataset_artifact_manifest, DATASET_ARTIFACT_VERSION

__all__ += [
    "build_dataset_quality_report",
    "summarize_label_counts",
    "build_dataset_artifact_manifest",
    "validate_dataset_artifact_manifest",
    "DATASET_ARTIFACT_VERSION",
]

from .audit_dataset import load_audit_json, build_dataset_records_from_audit_files, export_dataset_from_audit_files

__all__ += ["load_audit_json", "build_dataset_records_from_audit_files", "export_dataset_from_audit_files"]
from .training_data import (
    REPOSITORY_LABEL_FIELD,
    PORTFOLIO_LABEL_FIELD,
    get_ordered_feature_names,
    extract_feature_matrix,
    extract_labels,
    filter_labeled_records,
    prepare_supervised_dataset,
    prepare_split_supervised_datasets,
)

__all__ += [
    "REPOSITORY_LABEL_FIELD",
    "PORTFOLIO_LABEL_FIELD",
    "get_ordered_feature_names",
    "extract_feature_matrix",
    "extract_labels",
    "filter_labeled_records",
    "prepare_supervised_dataset",
    "prepare_split_supervised_datasets",
]
from .evaluation import (
    EVALUATION_REPORT_VERSION,
    confusion_matrix,
    classification_metrics,
    evaluate_repository_baseline,
    evaluate_portfolio_baseline,
    evaluate_split_baselines,
)

__all__ += [
    "EVALUATION_REPORT_VERSION",
    "confusion_matrix",
    "classification_metrics",
    "evaluate_repository_baseline",
    "evaluate_portfolio_baseline",
    "evaluate_split_baselines",
]

from .dataset_builder import build_dataset_records, validate_dataset
from .splits import assign_split, split_dataset, DEFAULT_SPLIT_RATIOS
from .baseline import predict_record_baseline, predict_repository_readiness_baseline, predict_portfolio_readiness_baseline

__all__ += [
    "build_dataset_records",
    "validate_dataset",
    "assign_split",
    "split_dataset",
    "DEFAULT_SPLIT_RATIOS",
    "predict_record_baseline",
    "predict_repository_readiness_baseline",
    "predict_portfolio_readiness_baseline",
]
