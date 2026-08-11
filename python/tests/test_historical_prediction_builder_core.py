"""Tests for historical prediction dataset builder core materialization and success behavior."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Generic, TypeVar

from navlens import MarketDate
from navlens.prediction.historical import (
    HistoricalPredictionRecord,
    SkippedPredictionRecord,
    build_historical_prediction_dataset,
)
from tests.historical_prediction_fixtures import (
    make_request,
    make_scope,
    sample_snapshots,
)

T = TypeVar("T")


class SingleUseIterable(Generic[T]):
    """An iterable wrapper that strictly asserts it is iterated exactly once."""

    def __init__(self, items: list[T]) -> None:
        self._items = items
        self._iter_count = 0

    def __iter__(self) -> Iterator[T]:
        self._iter_count += 1
        if self._iter_count > 1:
            raise RuntimeError(
                f"Iterable was iterated {self._iter_count} times, expected exactly 1 iteration"
            )
        return iter(self._items)

    @property
    def iter_count(self) -> int:
        return self._iter_count


def test_empty_schedule_returns_empty_dataset_with_scope() -> None:
    scope = make_scope()
    snapshots = sample_snapshots(count=10)
    dataset = build_historical_prediction_dataset(scope, [], snapshots)

    assert dataset.scope == scope
    assert dataset.outcomes == ()


def test_single_use_iterable_snapshots_and_requests_consumed_exactly_once() -> None:
    scope = make_scope(lookback=5)
    snapshots_list = sample_snapshots(count=12)

    req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
    )

    req_iterable = SingleUseIterable([req1, req2])
    snap_iterable = SingleUseIterable(snapshots_list)

    dataset = build_historical_prediction_dataset(scope, req_iterable, snap_iterable)

    assert req_iterable.iter_count == 1
    assert snap_iterable.iter_count == 1
    assert len(dataset.outcomes) == 2


def test_successful_multiple_period_replay_and_request_preservation() -> None:
    scope = make_scope(lookback=5)
    snapshots = sample_snapshots(count=15)

    req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
    )

    dataset = build_historical_prediction_dataset(scope, [req1, req2], snapshots)

    assert len(dataset.outcomes) == 2
    assert dataset.outcomes[0].request is req1
    assert dataset.outcomes[1].request is req2

    rec1 = dataset.outcomes[0]
    rec2 = dataset.outcomes[1]
    assert isinstance(rec1, HistoricalPredictionRecord)
    assert isinstance(rec2, HistoricalPredictionRecord)
    assert rec1.realized_end_snapshot.observation.date == MarketDate(2026, 1, 11)
    assert rec2.realized_end_snapshot.observation.date == MarketDate(2026, 1, 12)


def test_all_skipped_dataset_remains_valid_and_preserves_requests() -> None:
    scope = make_scope(lookback=5)
    snapshots = []

    req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
    )

    dataset = build_historical_prediction_dataset(scope, [req1, req2], snapshots)

    assert dataset.scope == scope
    assert len(dataset.outcomes) == 2
    assert dataset.outcomes[0].request is req1
    assert dataset.outcomes[1].request is req2
    assert isinstance(dataset.outcomes[0], SkippedPredictionRecord)
    assert isinstance(dataset.outcomes[1], SkippedPredictionRecord)
