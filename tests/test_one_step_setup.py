# Copyright 2022 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Test that the one-step setup flow described in Pants docs works as expected."""

import os
import subprocess
from pathlib import Path


def test_runs_on_clean_directory(tmp_path: Path) -> None:

    cwd = os.getcwd()

    proc = subprocess.run(
        ["/bin/bash", os.path.join(cwd, "one_step_setup.sh")],
        cwd=tmp_path,
        capture_output=True,
    )

    assert proc.returncode == 0
    assert b"Pants was installed successfully" in proc.stderr


def test_pin_version(tmp_path: Path) -> None:

    cwd = os.getcwd()
    env = os.environ.copy()
    env["PANTS_VERSION"] = "2.11.0rc6"

    proc = subprocess.run(
        ["/bin/bash", os.path.join(cwd, "one_step_setup.sh")],
        cwd=tmp_path,
        env=env,
    )

    assert proc.returncode == 0

    pants_proc = subprocess.run(
        [tmp_path / "pants", "--version"],
        cwd=tmp_path,
        capture_output=True,
    )

    assert pants_proc.stdout.decode().strip() == "2.11.0rc6"


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
