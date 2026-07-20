"""Atomic local-file replacement shared by artifact stores."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Write bytes completely before atomically replacing the target path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as output:
            temporary_path = Path(output.name)
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
