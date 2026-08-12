"""Safe output publication for prediction command artifacts."""

from pathlib import Path
from typing import BinaryIO

from navlens.storage import atomic_write_bytes


def publish_prediction_output(
    content: bytes,
    *,
    output_path: Path | None,
    stdout: BinaryIO,
) -> Path | None:
    """Write one LF-terminated payload to stdout or a new atomic artifact."""
    payload = content.rstrip(b"\n") + b"\n"
    if output_path is None:
        stdout.write(payload)
        return None
    if output_path.exists():
        raise FileExistsError(f"prediction output already exists: {output_path}")
    atomic_write_bytes(output_path, payload)
    return output_path
