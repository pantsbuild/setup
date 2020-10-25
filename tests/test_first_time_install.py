# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Test that the first time installation flow described by
https://www.pantsbuild.org/install.html#recommended-installation works as expected."""

import os
import re
import subprocess
from pathlib import Path

from helpers import create_pants_config


def test_only_bootstraps_the_first_time(build_root: Path) -> None:
    create_pants_config(parent_folder=build_root, pants_version="1.30.1")
    first_run_pants_script_logging = subprocess.run(
        ["./pants", "--version"],
        check=True,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        cwd=str(build_root),
    ).stderr
    assert "Collecting pantsbuild.pants==" in first_run_pants_script_logging
    second_run_pants_script_logging = subprocess.run(
        ["./pants", "--version"],
        check=True,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        cwd=str(build_root),
    ).stderr
    assert "Collecting pantsbuild.pants==" not in second_run_pants_script_logging


def test_relative_cache_locations_work(build_root: Path) -> None:
    create_pants_config(parent_folder=build_root, pants_version="1.30.1")
    result = subprocess.run(
        ["./pants", "--version"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        cwd=str(build_root),
        env={**os.environ, "PANTS_SETUP_CACHE": "relative_dir"},
    )
    assert re.search(
        r"virtual environment successfully created at .*/relative_dir/bootstrap.*/",
        result.stderr,
        flags=re.MULTILINE,
    )


def test_pants_1_22_and_earlier_fails(build_root: Path) -> None:
    create_pants_config(parent_folder=build_root, pants_version="1.22.0", use_toml=False)
    result = subprocess.run(
        ["./pants", "--version"], cwd=str(build_root), stderr=subprocess.PIPE, encoding="utf-8"
    )
    assert result.returncode != 0
    assert "does not work with Pants <= 1.22.0" in result.stderr


def test_pants_version_must_be_set(build_root: Path) -> None:
    # We do not call `create_pants_config()`.
    result = subprocess.run(
        ["./pants", "--version"],
        cwd=str(build_root),
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    assert result.returncode != 0
    assert "Please explicitly specify the `pants_version` in your `pants.toml`" in result.stderr


def test_python2_fails(build_root: Path) -> None:
    create_pants_config(parent_folder=build_root, pants_version="1.30.1")
    result = subprocess.run(
        ["./pants", "--version"],
        cwd=str(build_root),
        stderr=subprocess.PIPE,
        encoding="utf-8",
        env={**os.environ, "PYTHON": "python2"},
    )
    assert result.returncode != 0
    assert "Pants requires Python 3.6+ to run" in result.stderr
