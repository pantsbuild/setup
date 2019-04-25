# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Test that the first time installation flow described by
https://www.pantsbuild.org/install.html#recommended-installation works as expected.

Note that this does not test the result of `./pants generate-pants-ini`, because that
is already tested by Pants at
https://github.com/pantsbuild/pants/blob/master/tests/python/pants_test/core_tasks/test_generate_pants_ini.py."""

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
        cwd=tmpdir
      )
      # Pip will resolve the most recent stable release, which will be the output of
      # `./pants --version`.
      downloaded_version = completed_process.stdout.strip()
      self.assertTrue(re.search(
        fr"virtual environment successfully created at .*/bootstrap.*/{downloaded_version}_py",
        completed_process.stderr, flags=re.MULTILINE
      ))

  def test_only_bootstraps_the_first_time(self) -> None:
    with self.setup_pants_in_tmpdir() as tmpdir:
      first_run_pants_script_logging = subprocess.run(
        ["./pants", "--version"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        cwd=tmpdir
      ).stderr
      # Check that stderr is truthy, i.e. there is output.
      self.assertTrue(first_run_pants_script_logging)
      second_run_pants_script_logging = subprocess.run(
        ["./pants", "--version"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        cwd=tmpdir
      ).stderr
      # Check that stderr is falsy, i.e. there is no output.
      self.assertFalse(second_run_pants_script_logging)
