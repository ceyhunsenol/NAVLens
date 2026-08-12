import argparse
import shutil
import subprocess
import sys
from importlib.metadata import distribution, version
from pathlib import Path

import navlens
from historical_prediction_smoke import verify_historical_prediction_example


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-version", required=True)
    return parser.parse_args()


def _console_script_names() -> list[str]:
    return sorted(
        entry_point.name
        for entry_point in distribution("navlens").entry_points
        if entry_point.group == "console_scripts"
    )


def _resolve_console_script(name: str) -> str:
    executable = shutil.which(name)
    if executable is not None:
        return executable

    suffix = ".exe" if sys.platform == "win32" else ""
    candidate = Path(sys.executable).parent / f"{name}{suffix}"
    if candidate.is_file():
        return str(candidate)
    raise SystemExit(f"console script is not installed: {name}")


def _run_command(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise SystemExit(f"command failed ({' '.join(command)}):\n{result.stderr}")
    return result.stdout


def _verify_console_scripts(names: list[str]) -> None:
    if not names:
        raise SystemExit("installed package does not publish any console scripts")

    for name in names:
        executable = _resolve_console_script(name)
        _run_command([executable, "--help"])
        result = subprocess.run([executable], capture_output=True, text=True, encoding="utf-8")
        valid_usage_error = (
            result.returncode == 2
            and not result.stdout
            and "usage:" in result.stderr
            and "error:" in result.stderr
            and "Traceback" not in result.stderr
        )
        if not valid_usage_error:
            raise SystemExit(
                f"invalid missing-argument behavior for {name}: "
                f"exit={result.returncode}, stdout={result.stdout!r}, "
                f"stderr={result.stderr!r}"
            )


def main() -> None:
    expected_version = _parse_args().expected_version
    installed_version = version("navlens")
    if navlens.__version__ != expected_version or installed_version != expected_version:
        raise SystemExit(
            "installed version mismatch: "
            f"expected={expected_version}, package={navlens.__version__}, "
            f"metadata={installed_version}"
        )

    names = _console_script_names()
    _verify_console_scripts(names)
    prediction_executable = _resolve_console_script("navlens-evaluate-historical-prediction-csv")
    verify_historical_prediction_example(prediction_executable)
    print(
        f"verified navlens {installed_version}, {len(names)} console scripts, "
        "and the historical prediction example"
    )


if __name__ == "__main__":
    main()
