# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import configparser
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional
from unittest import TestCase


class TestBase(TestCase):
    """A base class with useful utils for tests."""

    def setUp(self) -> None:
        self.pyenv_bin: str
        if "PYENV_BIN" in os.environ:
            self.pyenv_bin = os.environ["PYENV_BIN"]
        else:
            pyenv_path = shutil.which("pyenv")
            if pyenv_path is None:
                raise ValueError(
                    "Pyenv must be installed. The binary `pyenv` must either be discoverable from "
                    "the `$PATH` or you must set the environment variable `PYENV_BIN`."
                )
            self.pyenv_bin = pyenv_path
        if "PYENV_ROOT" not in os.environ:
            raise ValueError(
                "The environment variable `PYENV_ROOT` must be set. Please run "
                "`export PYENV_ROOT=$(pyenv root)`."
            )
        self.pyenv_versions = subprocess.run(
            [self.pyenv_bin, "versions", "--bare"],
            stdout=subprocess.PIPE,
            encoding="utf-8",
            check=True,
        ).stdout.splitlines()
        print(self.pyenv_versions)

    @contextmanager
    def copy_pants_into_tmpdir(self) -> Iterator[str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            # NB: Unlike the install guide's instruction to curl the `./pants` script, we directly
            # copy it to ensure we are using the branch's version of the script and to avoid
            # network pings.
            shutil.copy("pants", f"{tmpdir}/pants")
            yield tmpdir

    @contextmanager
    def set_pants_cache_to_tmpdir(self) -> Iterator[None]:
        with tempfile.TemporaryDirectory() as tmpdir:
            original_env = os.environ.copy()
            os.environ["PANTS_HOME"] = tmpdir
            try:
                yield
            finally:
                os.environ.clear()
                os.environ.update(original_env)

    @contextmanager
    def setup_pants_in_tmpdir(self) -> Iterator[str]:
        with self.set_pants_cache_to_tmpdir(), self.copy_pants_into_tmpdir() as buildroot_tmpdir:
            yield buildroot_tmpdir

    @contextmanager
    def maybe_run_pyenv_local(
        self, python_version: Optional[str], *, parent_folder: str
    ) -> Iterator[None]:
        if python_version is None:
            yield
            return

        def is_compatible(pyenv_version: str) -> bool:
            major, minor, _ = pyenv_version.split(".")
            return f"{major}.{minor}" == python_version

        compatible_pyenv_version = next(
            (
                pyenv_version
                for pyenv_version in self.pyenv_versions
                if is_compatible(pyenv_version)
            ),
            None,
        )
        if compatible_pyenv_version is None:
            raise ValueError(
                f"Python {python_version} is not installed via Pyenv. Please install with "
                f"`pyenv install`. All installed versions: {', '.join(self.pyenv_versions)}."
            )
        subprocess.run(
            [self.pyenv_bin, "local", compatible_pyenv_version], cwd=parent_folder, check=True
        )
        try:
            yield
        finally:
            subprocess.run(
                [self.pyenv_bin, "local", "--unset", compatible_pyenv_version],
                cwd=parent_folder,
                check=True,
            )

    @staticmethod
    def create_pants_ini(*, parent_folder: str, pants_version: str) -> None:
        config = configparser.ConfigParser()
        config["GLOBAL"] = {
            "pants_version": pants_version,
            "plugins": "['pantsbuild.pants.contrib.go==%(pants_version)s']",
        }
        with open(f"{parent_folder}/pants.ini", "w") as f:
            config.write(f)

    @staticmethod
    def create_dummy_build(*, parent_folder: str) -> None:
        Path(parent_folder, "BUILD").write_text("target(name='test')\n")
