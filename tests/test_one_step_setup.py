# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Test that the first time installation flow described by
https://www.pantsbuild.org/install.html#recommended-installation works as expected."""

import os
import subprocess
from pathlib import Path


def test_runs_on_clean_directory(tmp_path: Path) -> None:

    cwd = os.getcwd()

    proc = subprocess.run(
        ["/bin/bash", os.path.join(cwd, "one_step_setup.sh")],
        cwd=tmp_path,
    )

    assert proc.returncode == 0


def test_fails_if_pants_script_present(tmp_path: Path) -> None:

    cwd = os.getcwd()
    pants_script = tmp_path / "pants"
    pants_script.touch()

    proc = subprocess.run(
        ["/bin/bash", os.path.join(cwd, "one_step_setup.sh")],
        cwd=tmp_path,
    )

    assert proc.returncode == 1


def test_fails_if_pants_toml_present(tmp_path: Path) -> None:

    cwd = os.getcwd()
    pants_toml = tmp_path / "pants.toml"
    pants_toml.touch()

    proc = subprocess.run(
        ["/bin/bash", os.path.join(cwd, "one_step_setup.sh")],
        cwd=tmp_path,
    )

    assert proc.returncode == 1
