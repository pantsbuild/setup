# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Test that the first time installation flow described by
https://www.pantsbuild.org/install.html#recommended-installation works as expected."""

import os
import re
import subprocess
from pathlib import Path

import pytest
from colors import yellow
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
    assert "Bootstrapping Pants using" in first_run_pants_script_logging
    second_run_pants_script_logging = subprocess.run(
        ["./pants", "--version"],
        check=True,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        cwd=str(build_root),
    ).stderr
    assert "Bootstrapping Pants using" not in second_run_pants_script_logging


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
        r"New virtual environment successfully created at .*/relative_dir/bootstrap.*/",
        result.stderr,
        flags=re.MULTILINE,
    )


def test_pants_1_25_and_earlier_fails(build_root: Path) -> None:
    create_pants_config(parent_folder=build_root, pants_version="1.25.0")
    result = subprocess.run(
        ["./pants", "--version"], cwd=str(build_root), stderr=subprocess.PIPE, encoding="utf-8"
    )
    assert result.returncode != 0
    assert "does not work with Pants <= 1.25.0" in result.stderr


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
    assert (
        'For `pants_version = "1.30.1"`, Pants requires Python 3.6, 3.7, or 3.8 to run.'
        in result.stderr
    )


def test_pex_shrinkwrap_issues_105(build_root: Path) -> None:
    create_pants_config(parent_folder=build_root, pants_version="1.30.1")
    result = subprocess.run(
        ["./pants", "--version"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        cwd=str(build_root),
        env={
            **os.environ,
            "PEX_MODULE": "foo",
            "PEX_SCRIPT": "bar",
        },
    )
    stderr_lines = result.stderr.splitlines()
    assert (
        yellow("Scrubbing PEX_MODULE PEX_SCRIPT") in stderr_lines
        or yellow("Scrubbing PEX_SCRIPT PEX_MODULE") in stderr_lines
    )


@pytest.mark.parametrize(
    ["quote", "suffix"],
    [
        pytest.param('"', " ", id="double quoted"),
        pytest.param('"', "  # Because.", id="double quoted trailing comment"),
        pytest.param("'", " ", id="single quoted"),
        pytest.param("'", "  # You see...", id="single quoted trailing comment"),
    ],
)
def test_pants_version_parsing_issues_103(build_root: Path, quote: str, suffix: str) -> None:
    create_pants_config(
        parent_folder=build_root, pants_version="1.30.1", quote=quote, suffix=suffix
    )
    result = subprocess.run(
        ["./pants", "--version"],
        check=True,
        stdout=subprocess.PIPE,
        encoding="utf-8",
        cwd=str(build_root),
    )
    assert "1.30.1" == result.stdout.strip()
