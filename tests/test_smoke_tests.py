# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Test that `./pants` works correctly with some basic sanity checks."""

import os
import shutil
import subprocess
import textwrap
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, List, Optional

import pytest
from helpers import create_pants_config


@pytest.fixture(scope="module")
def pyenv_bin() -> str:
    pyenv_bin = os.environ.get("PYENV_BIN") or shutil.which("pyenv")
    if pyenv_bin is None:
        raise ValueError(
            "Pyenv must be installed. The binary `pyenv` must either be discoverable from "
            "the `$PATH` or you must set the environment variable `PYENV_BIN`."
        )
    return pyenv_bin


@pytest.fixture(scope="module")
def pyenv_versions(pyenv_bin: str) -> List[str]:
    return subprocess.run(
        [pyenv_bin, "versions", "--bare", "--skip-aliases"],
        stdout=subprocess.PIPE,
        encoding="utf-8",
        check=True,
    ).stdout.splitlines()


@dataclass(frozen=True)
class SmokeTester:
    pyenv_bin: str
    pyenv_versions: List[str]
    build_root: Path

    @contextmanager
    def _maybe_run_pyenv_local(self, python_version: Optional[str]) -> Iterator[None]:
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
            [self.pyenv_bin, "local", compatible_pyenv_version],
            cwd=str(self.build_root),
            check=True,
        )
        try:
            yield
        finally:
            subprocess.run(
                [self.pyenv_bin, "local", "--unset", compatible_pyenv_version],
                cwd=str(self.build_root),
                check=True,
            )

    def smoke_test(
        self,
        *,
        pants_version: Optional[str],
        python_version: Optional[str],
        use_toml: bool = True,
        sha: Optional[str] = None,
    ) -> None:
        env = {**os.environ}
        if sha:
            env["PANTS_SHA"] = sha
        version_command = ["./pants", "--version"]
        list_command = ["./pants", "list", "::"]
        binary_command = ["./pants", "binary", "//:bin"]
        with self._maybe_run_pyenv_local(python_version):
            create_pants_config(
                parent_folder=self.build_root, pants_version=pants_version, use_toml=use_toml
            )
            (self.build_root / "BUILD").write_text(
                textwrap.dedent(
                    """
            target(name='test')

            # To test that we can resolve these, esp. against custom shas.
            pants_requirement(name='pantsreq')
            python_binary(name='bin', dependencies=[':pantsreq'])
            """
                )
            )

            def run_command(command: List[str], **kwargs: Any) -> None:
                subprocess.run(command, check=True, cwd=str(self.build_root), **kwargs)

            run_command(version_command, env=env)
            run_command(list_command, env=env)
            run_command(binary_command, env=env)
            if "SKIP_PANTSD_TESTS" not in os.environ:
                env_with_pantsd = {**env, "PANTS_ENABLE_PANTSD": "True"}
                run_command(version_command, env=env_with_pantsd)
                run_command(list_command, env=env_with_pantsd)
                run_command(binary_command, env=env_with_pantsd)

    def smoke_test_for_all_python_versions(
        self, *python_versions: str, pants_version: Optional[str], use_toml: bool = True
    ) -> None:
        for python_version in python_versions:
            self.smoke_test(
                pants_version=pants_version, python_version=python_version, use_toml=use_toml
            )


@pytest.fixture
def checker(pyenv_bin: str, pyenv_versions: List[str], build_root: Path) -> SmokeTester:
    return SmokeTester(pyenv_bin=pyenv_bin, pyenv_versions=pyenv_versions, build_root=build_root)


def test_pants_latest_stable(checker: SmokeTester) -> None:
    checker.smoke_test(python_version=None, pants_version=None, use_toml=False)
    checker.smoke_test_for_all_python_versions(
        "3.6", "3.7", "3.8", pants_version=None, use_toml=False
    )


def test_pants_1_28(checker: SmokeTester) -> None:
    checker.smoke_test(python_version=None, pants_version="1.28.0")
    checker.smoke_test_for_all_python_versions("3.6", "3.7", "3.8", pants_version="1.28.0")


def test_pants_2_0(checker: SmokeTester) -> None:
    checker.smoke_test(python_version=None, pants_version="2.0.0.dev6")
    checker.smoke_test_for_all_python_versions("3.6", "3.7", "3.8", pants_version="2.0.0.dev6")


def test_pants_at_sha(checker: SmokeTester) -> None:
    sha = "41ec94b758aac39c13f59e694fba5ed096a51ba9"
    version = "2.0.0.dev6+git41ec94b7"
    checker.smoke_test(python_version=None, pants_version=version, sha=sha)
