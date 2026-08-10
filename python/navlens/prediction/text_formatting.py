"""Text report formatting for single return prediction results."""

from .contracts import SingleReturnPredictionResult


def format_prediction_text(result: SingleReturnPredictionResult) -> str:
    """Format a SingleReturnPredictionResult into a human-readable text report."""
    expected_pct = result.expected_return_decimal * 100.0
    lower_pct = result.prediction_interval_lower_decimal * 100.0
    upper_pct = result.prediction_interval_upper_decimal * 100.0
    confidence_pct = result.confidence_level * 100.0

    lines = [
        "=== NAVLens Point-in-Time Return Prediction ===",
        f"Fund ID: {result.fund_id}",
        f"Source ID: {result.source_id}",
        f"Prediction Timestamp: {result.prediction_timestamp.isoformat()}",
        f"Prediction Date: {result.prediction_date}",
        f"Pricing As-Of Date: {result.pricing_as_of_date}",
        f"Target Date: {result.target_date}",
        f"Last Observation Date: {result.last_observation_date}",
        f"Last Observation Available At: {result.last_observation_available_at.isoformat()}",
        f"Last Observation Ingested At: {result.last_observation_ingested_at.isoformat()}",
        f"Actual Data As Of: {result.actual_data_as_of.isoformat()}",
        f"Selected Snapshots: {result.selected_snapshot_count}",
        f"Canonical Returns: {result.canonical_return_count}",
        f"Training Returns: {result.training_return_count}",
        (
            f"Training Target Window: {result.training_target_start_date} "
            f"to {result.training_target_end_date}"
        ),
        f"Lookback: {result.lookback}",
        f"Model: {result.model_name} ({result.model_version})",
        f"Feature Schema: {result.feature_schema_version}",
        f"Target Semantics: {result.target_definition}",
        f"Confidence Level: {confidence_pct:.2f}%",
        f"Expected Return (Decimal): {result.expected_return_decimal:.6f}",
        f"Expected Return (Percent): {expected_pct:.6f}%",
        (
            f"Prediction Interval (Decimal): [{result.prediction_interval_lower_decimal:.6f}, "
            f"{result.prediction_interval_upper_decimal:.6f}]"
        ),
        f"Prediction Interval (Percent): [{lower_pct:.6f}%, {upper_pct:.6f}%]",
    ]
    return "\n".join(lines)
