"""Human-readable output for TEFAS walk-forward backtests."""

from .records import WalkForwardRecord
from .tefas_backtest import TefasBacktestResult


def format_tefas_backtest_result(result: TefasBacktestResult) -> str:
    """Render provenance, decimal metrics, and dated prediction records."""
    metrics = result.evaluation.metrics
    cache_status = "hit" if result.acquisition.from_cache else "miss"
    lines = [
        f"fund={result.dataset.fund_id}",
        f"source_records={result.dataset.source_row_count}",
        f"predictions={len(result.evaluation.records)}",
        f"cache={cache_status}",
        f"raw={result.dataset.source_path}",
        f"model=linear-regression-baseline@{result.estimator.model_version}",
        f"lookback={result.estimator.lookback}",
        f"confidence_level={result.estimator.confidence_level}",
        f"mae_decimal={metrics.mean_absolute_error}",
        f"mean_error_decimal={metrics.mean_error}",
        f"rmse_decimal={metrics.root_mean_squared_error}",
        f"direction_accuracy={metrics.direction_accuracy}",
    ]
    if metrics.interval is not None:
        lines.extend(
            [
                f"interval_coverage={metrics.interval.coverage}",
                f"interval_mean_width_decimal={metrics.interval.mean_width}",
            ]
        )
    lines.append(
        "prediction_date,target_date,predicted_return_decimal,actual_return_decimal,"
        "lower_bound_decimal,upper_bound_decimal"
    )
    lines.extend(_format_record(record) for record in result.evaluation.records)
    return "\n".join(lines)


def _format_record(record: WalkForwardRecord) -> str:
    values = (
        record.prediction_date.date().isoformat(),
        record.target_date.date().isoformat(),
        record.predicted_return,
        record.actual_return,
        record.lower_bound,
        record.upper_bound,
    )
    return ",".join(str(value) for value in values)
