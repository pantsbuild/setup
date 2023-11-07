# Copyright 2023 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Test the pantsup script."""

import os
import subprocess
from pathlib import Path


def test_installs_pants(tmp_path: Path) -> None:
    cwd = os.getcwd()
    proc = subprocess.run(
        ["/bin/bash", os.path.join(cwd, "pantsup.sh")],
        env={"HOME": str(tmp_path)},
        capture_output=True,
    )

    assert proc.returncode == 0
    assert b"Downloading and installing the pants launcher" in proc.stderr
    assert b"Installed the pants launcher from" in proc.stderr

    bin_path = tmp_path / ".local" / "bin" / "pants"
    assert os.path.isfile(bin_path)
    assert os.access(bin_path, os.X_OK)
