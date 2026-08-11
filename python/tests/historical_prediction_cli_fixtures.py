"""CSV fixtures for historical prediction CLI tests."""

from datetime import date, timedelta
from pathlib import Path


def write_historical_prediction_cli_files(tmp_path: Path) -> list[str]:
    """Write a two-period schedule and matching unit-price history."""
    schedule_path = tmp_path / "prediction_schedule.csv"
    schedule_path.write_text(
        "prediction_date,pricing_as_of_date,target_date,"
        "prediction_timestamp,evaluation_timestamp\n"
        "2026-01-10,2026-01-10,2026-01-11,"
        "2026-01-10T18:00:00Z,2026-01-11T18:00:00Z\n"
        "2026-01-11,2026-01-11,2026-01-12,"
        "2026-01-11T18:00:00Z,2026-01-12T18:00:00Z\n",
        encoding="utf-8",
    )

    prices_path = tmp_path / "fund_unit_prices.csv"
    rows = ["fund_id,market_date,unit_price,available_at,ingested_at,source_id"]
    start = date(2026, 1, 1)
    price = 100.0
    for offset in range(12):
        market_date = start + timedelta(days=offset)
        price *= 1.002
        timestamp = f"{market_date.isoformat()}T18:00:00+00:00"
        rows.append(f"FUND_A,{market_date.isoformat()},{price},{timestamp},{timestamp},SOURCE_1")
    prices_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    return [
        "--schedule-csv",
        str(schedule_path),
        "--fund-unit-prices-csv",
        str(prices_path),
        "--fund-id",
        "FUND_A",
        "--source-id",
        "SOURCE_1",
        "--lookback",
        "5",
        "--confidence-level",
        "0.95",
        "--model-version",
        "v1.0",
    ]
