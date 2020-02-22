# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Test that `./pants` works correctly with some basic sanity checks."""

import os
import subprocess
from typing import Any, List, Optional

from test_base import TestBase


class TestSanityCheck(TestBase):
    def sanity_check(self, *, pants_version: Optional[str], python_version: Optional[str]) -> None:
        version_command = ["./pants", "--version"]
        list_command = ["./pants", "list", "::"]

        with self.setup_pants_in_tmpdir() as tmpdir, self.maybe_run_pyenv_local(
            python_version, parent_folder=tmpdir
        ):
            self.create_pants_ini(parent_folder=tmpdir, pants_version=pants_version)
            self.create_dummy_build(parent_folder=tmpdir)

            def run_command(command: List[str], **kwargs: Any) -> None:
                subprocess.run(command, check=True, cwd=tmpdir, **kwargs)

            run_command(version_command)
            run_command(list_command)
            if "SKIP_PANTSD_TESTS" not in os.environ:
                env_with_pantsd = {**os.environ, "PANTS_ENABLE_PANTSD": "True"}
                run_command(version_command, env=env_with_pantsd)
                run_command(list_command, env=env_with_pantsd)

    def check_for_all_python_versions(
        self, *python_versions: str, pants_version: Optional[str]
    ) -> None:
        for python_version in python_versions:
            self.sanity_check(pants_version=pants_version, python_version=python_version)

    def test_pants_1_24(self) -> None:
        self.sanity_check(python_version=None, pants_version="1.24.0")
        self.check_for_all_python_versions("3.6", "3.7", "3.8", pants_version="1.24.0")

    def test_pants_latest(self) -> None:
        self.sanity_check(python_version=None, pants_version=None)
        self.check_for_all_python_versions("3.6", "3.7", "3.8", pants_version=None)
