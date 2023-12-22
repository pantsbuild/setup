# Copyright 2023 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Test the pantsup script."""

import subprocess
from pathlib import Path
from typing import List, Optional


def script_location() -> Path:
    return Path(__file__).parent.parent / "get-pants.sh"


def _run(home: Path, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["/bin/bash", script_location(), *args],
        env={"HOME": str(home)},
        capture_output=True,
        check=check,
    )


def _check_launcher_runs(destination: Path, expected_version: Optional[str] = None) -> None:
    proc = subprocess.run(
        destination, env={"PANTS_BOOTSTRAP_VERSION": "report"}, capture_output=True, check=True
    )
    if expected_version is not None:
        assert proc.stdout.decode().strip() == expected_version
    else:
        # if we don't have a particular version, just verify that there's some output
        assert proc.stdout


def test_installs_pants_when_no_args(tmp_path: Path) -> None:
    proc = _run(home=tmp_path, args=[])

    assert b"Downloading and installing the pants launcher" in proc.stderr
    assert b"Installed the pants launcher from" in proc.stderr

    _check_launcher_runs(tmp_path / ".local" / "bin" / "pants")
