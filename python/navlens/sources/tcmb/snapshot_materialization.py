"""Point-in-time-safe TCMB FxRateSnapshot materialization."""

from collections.abc import Iterable
from pathlib import Path

from navlens import FxRateObservation
from navlens.datasets import FxRateDatasetError, FxRateSnapshot

from ._revision_index_contracts import TcmbRevisionRecord
from .errors import (
    TcmbMappingError,
    TcmbRawCacheError,
    TcmbSnapshotMaterializationError,
    TcmbXmlParseError,
)
from .mapper import map_tcmb_daily_rates
from .parser import parse_tcmb_daily_rates_xml
from .provenance import TCMB_SOURCE_ID
from .raw_cache import load_tcmb_raw_artifact
from .revision_availability import TcmbResolvedRevisionAvailability
from .revision_index import TcmbRevisionIndex


def materialize_tcmb_fx_rate_snapshots(
    root: str | Path,
    index: TcmbRevisionIndex,
    resolved_availabilities: Iterable[TcmbResolvedRevisionAvailability],
) -> tuple[FxRateSnapshot, ...]:
    """Materialize point-in-time-safe TCMB snapshots from deterministic dependencies."""
    if not isinstance(root, (str, Path)):
        raise TcmbSnapshotMaterializationError("root must be a string or Path")
    if not isinstance(index, TcmbRevisionIndex):
        raise TcmbSnapshotMaterializationError("index must be a TcmbRevisionIndex")
    if not isinstance(resolved_availabilities, Iterable):
        raise TcmbSnapshotMaterializationError("resolved_availabilities must be iterable")

    availabilities = _validate_availabilities(index, resolved_availabilities)
    root_path = Path(root)
    snapshots: list[FxRateSnapshot] = []
    for revision, resolved in zip(index.revisions, availabilities, strict=True):
        observations = _load_observations(root_path, revision.sha256_hex)
        snapshots.extend(_build_snapshots(index, revision, resolved, observations))
    return tuple(snapshots)


def _validate_availabilities(
    index: TcmbRevisionIndex,
    values: Iterable[TcmbResolvedRevisionAvailability],
) -> tuple[TcmbResolvedRevisionAvailability, ...]:
    availabilities = tuple(values)
    if len(availabilities) != len(index.revisions):
        raise TcmbSnapshotMaterializationError(
            f"expected {len(index.revisions)} resolved_availabilities, got {len(availabilities)}"
        )

    for position, (revision, resolved) in enumerate(
        zip(index.revisions, availabilities, strict=True)
    ):
        if not isinstance(resolved, TcmbResolvedRevisionAvailability):
            raise TcmbSnapshotMaterializationError(
                "resolved_availabilities must contain only "
                "TcmbResolvedRevisionAvailability instances"
            )
        if revision.sha256_hex != resolved.sha256_hex:
            raise TcmbSnapshotMaterializationError(
                f"digest mismatch at index {position}: expected {revision.sha256_hex}, "
                f"got {resolved.sha256_hex}"
            )
        if revision.first_observed_at != resolved.first_observed_at:
            raise TcmbSnapshotMaterializationError(
                f"first_observed_at mismatch for digest {revision.sha256_hex}: "
                f"expected {revision.first_observed_at}, got {resolved.first_observed_at}"
            )
    return availabilities


def _load_observations(root: Path, digest: str) -> tuple[FxRateObservation, ...]:
    try:
        raw_bytes = load_tcmb_raw_artifact(root, digest)
    except (OSError, TcmbRawCacheError) as error:
        raise TcmbSnapshotMaterializationError(
            f"raw cache error for artifact {digest}: {error}"
        ) from error
    if raw_bytes is None:
        raise TcmbSnapshotMaterializationError(f"missing raw artifact for digest {digest}")

    try:
        document = parse_tcmb_daily_rates_xml(raw_bytes)
    except TcmbXmlParseError as error:
        raise TcmbSnapshotMaterializationError(
            f"parse error for artifact {digest}: {error}"
        ) from error

    try:
        return map_tcmb_daily_rates(document)
    except TcmbMappingError as error:
        raise TcmbSnapshotMaterializationError(
            f"mapping error for artifact {digest}: {error}"
        ) from error


def _build_snapshots(
    index: TcmbRevisionIndex,
    revision: TcmbRevisionRecord,
    resolved: TcmbResolvedRevisionAvailability,
    observations: tuple[FxRateObservation, ...],
) -> tuple[FxRateSnapshot, ...]:
    snapshots: list[FxRateSnapshot] = []
    for observation in observations:
        if observation.market_date != index.market_date:
            raise TcmbSnapshotMaterializationError(
                f"mapped market date {observation.market_date} differs from "
                f"index market date {index.market_date} in artifact {revision.sha256_hex}"
            )
        try:
            snapshots.append(
                FxRateSnapshot(
                    observation=observation,
                    available_at=resolved.available_at,
                    ingested_at=revision.first_observed_at,
                    source_id=TCMB_SOURCE_ID,
                )
            )
        except FxRateDatasetError as error:
            raise TcmbSnapshotMaterializationError(
                f"dataset error for artifact {revision.sha256_hex}: {error}"
            ) from error
    return tuple(snapshots)
