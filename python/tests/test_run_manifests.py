import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from navlens.evaluation import LinearBaselineWalkForward
from navlens.evaluation.manifests import (
    build_tefas_run_manifest,
    serialize_run_manifest,
    store_run_manifest,
)
from navlens.evaluation.tefas_backtest import evaluate_tefas_acquisition
from navlens.sources.tefas import (
    TefasAcquisitionResult,
    TefasPriceRecord,
    TefasPriceRequest,
)

RUN_ID = UUID("3c42df1a-2d86-4c17-93e7-d1826d687638")


def test_builds_complete_versioned_manifest(tmp_path: Path) -> None:
    result, request = _completed_backtest(tmp_path)
    manifest = build_tefas_run_manifest(
        result,
        request,
        date(2026, 7, 20),
        datetime(2026, 7, 20, 12, 30, tzinfo=UTC),
        RUN_ID,
    )
    payload = json.loads(serialize_run_manifest(manifest))

    assert payload["schema_version"] == "navlens-backtest-run-v1"
    assert payload["run_id"] == str(RUN_ID)
    assert payload["target_definition"] == "next_published_nav_return_decimal"
    assert payload["configuration"]["linear_lookback"] == 2
    assert payload["source"]["provider"] == "tefas"
    assert payload["source"]["acquisition_as_of"] == "2026-07-20"
    assert len(payload["source"]["sha256"]) == 64
    assert [model["model_name"] for model in payload["models"]] == [
        "linear-regression-baseline",
        "historical-mean-baseline",
        "last-return-baseline",
    ]
    target_dates = [
        [prediction["target_date"] for prediction in model["predictions"]]
        for model in payload["models"]
    ]
    assert all(dates == target_dates[0] for dates in target_dates)
    assert all(model["metrics"]["sample_count"] == 3 for model in payload["models"])


def test_atomically_stores_manifest_by_run_id(tmp_path: Path) -> None:
    result, request = _completed_backtest(tmp_path)
    manifest = build_tefas_run_manifest(
        result,
        request,
        date(2026, 7, 20),
        datetime(2026, 7, 20, 12, 30, tzinfo=UTC),
        RUN_ID,
    )

    stored = store_run_manifest(manifest, tmp_path / "runs")

    assert stored.run_id == str(RUN_ID)
    assert stored.path == tmp_path / "runs" / f"{RUN_ID}.json"
    assert stored.path.read_bytes() == serialize_run_manifest(manifest)
    with pytest.raises(FileExistsError, match="already exists"):
        store_run_manifest(manifest, tmp_path / "runs")


def test_rejects_naive_generation_timestamp(tmp_path: Path) -> None:
    result, request = _completed_backtest(tmp_path)

    with pytest.raises(ValueError, match="timezone"):
        build_tefas_run_manifest(
            result,
            request,
            date(2026, 7, 20),
            datetime(2026, 7, 20, 12, 30),
        )


def _completed_backtest(tmp_path: Path):
    source_path = tmp_path / "payload.json"
    source_path.write_text('{"data": []}', encoding="utf-8")
    request = TefasPriceRequest("AAL", date(2026, 7, 8), date(2026, 7, 20))
    acquisition = TefasAcquisitionResult(_price_records(), source_path, True)
    estimator = LinearBaselineWalkForward(lookback=2, model_version="0.1.0")
    return evaluate_tefas_acquisition(acquisition, estimator), request


def _price_records() -> tuple[TefasPriceRecord, ...]:
    first_date = date(2026, 7, 8)
    prices = (100.0, 101.0, 100.5, 102.0, 101.0, 103.0, 104.0, 103.0, 105.0)
    return tuple(
        TefasPriceRecord(first_date + timedelta(days=offset), "AAL", price)
        for offset, price in enumerate(prices)
    )
