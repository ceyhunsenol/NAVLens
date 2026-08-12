from io import BytesIO
from pathlib import Path

import pytest
from navlens.prediction.output import publish_prediction_output


def test_publishes_one_lf_terminated_payload_to_stdout() -> None:
    stdout = BytesIO()

    stored = publish_prediction_output(b"result\n\n", output_path=None, stdout=stdout)

    assert stored is None
    assert stdout.getvalue() == b"result\n"


def test_atomically_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "prediction.json"

    stored = publish_prediction_output(b"{}", output_path=path, stdout=BytesIO())

    assert stored == path
    assert path.read_bytes() == b"{}\n"


def test_refuses_to_overwrite_existing_prediction(tmp_path: Path) -> None:
    path = tmp_path / "prediction.json"
    path.write_bytes(b"original")

    with pytest.raises(FileExistsError, match="already exists"):
        publish_prediction_output(b"replacement", output_path=path, stdout=BytesIO())

    assert path.read_bytes() == b"original"
