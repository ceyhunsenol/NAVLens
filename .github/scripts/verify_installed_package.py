import argparse
import shutil
import subprocess
import sys
from importlib.metadata import distribution, version
from pathlib import Path

import navlens


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


def _verify_console_scripts(names: list[str]) -> None:
    if not names:
        raise SystemExit("installed package does not publish any console scripts")

    for name in names:
        executable = shutil.which(name)
        if executable is None:
            suffix = ".exe" if sys.platform == "win32" else ""
            candidate = Path(sys.executable).parent / f"{name}{suffix}"
            executable = str(candidate) if candidate.is_file() else None
        if executable is None:
            raise SystemExit(f"console script is not installed: {name}")

        result = subprocess.run([executable, "--help"], capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit(f"{name} --help failed:\n{result.stderr}")


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
    print(f"verified navlens {installed_version} and {len(names)} console scripts")


if __name__ == "__main__":
    main()
