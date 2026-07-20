"""Local storage adapter for versioned run manifests."""

from pathlib import Path
from uuid import UUID

from navlens.storage import atomic_write_bytes

from .records import BacktestRunManifest, StoredRunManifest
from .serialization import serialize_run_manifest


def store_run_manifest(
    manifest: BacktestRunManifest,
    run_root: str | Path,
) -> StoredRunManifest:
    """Atomically persist one manifest under its safe UUID identifier."""
    canonical_run_id = str(UUID(manifest.run_id))
    root = Path(run_root)
    path = root / f"{canonical_run_id}.json"
    if path.exists():
        raise FileExistsError(f"run manifest already exists: {path}")
    atomic_write_bytes(path, serialize_run_manifest(manifest))
    return StoredRunManifest(canonical_run_id, path)
