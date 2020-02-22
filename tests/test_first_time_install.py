# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Test that the first time installation flow described by
https://www.pantsbuild.org/install.html#recommended-installation works as expected."""

import os
import re
import subprocess

from test_base import TestBase


class TestFirstTimeInstall(TestBase):
    def test_venv_name_uses_most_recent_stable_release(self) -> None:
        with self.setup_pants_in_tmpdir() as tmpdir:
            completed_process = subprocess.run(
                ["./pants", "--version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                cwd=tmpdir,
            )
            # Pip will resolve the most recent stable release, which will be the output of
            # `./pants --version`.
            downloaded_version = completed_process.stdout.strip()
            assert re.search(
                fr"virtual environment successfully created at .*/bootstrap.*/{downloaded_version}_py",
                completed_process.stderr,
                flags=re.MULTILINE,
            )

    def test_only_bootstraps_the_first_time(self) -> None:
        with self.setup_pants_in_tmpdir() as tmpdir:
            first_run_pants_script_logging = subprocess.run(
                ["./pants", "--version"],
                check=True,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                cwd=tmpdir,
            ).stderr
            assert first_run_pants_script_logging
            second_run_pants_script_logging = subprocess.run(
                ["./pants", "--version"],
                check=True,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                cwd=tmpdir,
            ).stderr
            assert not second_run_pants_script_logging

    def test_pants_1_16_and_earlier_fails(self) -> None:
        with self.setup_pants_in_tmpdir() as tmpdir:
            self.create_pants_config(parent_folder=tmpdir, pants_version="1.16.0", use_toml=False)
            result = subprocess.run(
                ["./pants", "--version"], cwd=tmpdir, stderr=subprocess.PIPE, encoding="utf-8"
            )
        assert result.returncode != 0
        assert "does not work with Pants <= 1.16.0" in result.stderr

    def test_python2_fails(self) -> None:
        with self.setup_pants_in_tmpdir() as tmpdir:
            result = subprocess.run(
                ["./pants", "--version"],
                cwd=tmpdir,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                env={**os.environ, "PYTHON": "python2"},
            )
        assert result.returncode != 0
        assert "Pants requires Python 3.6+ to run" in result.stderr
