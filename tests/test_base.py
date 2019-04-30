# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import configparser
import os
import shutil
import tempfile
from contextlib import contextmanager
from typing import Iterator, Optional
from unittest import TestCase


class TestBase(TestCase):
  """A base class with useful utils for tests."""

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

  def create_pants_ini(
    self, *, parent_folder: str, pants_version: str, python_version: Optional[str] = None
    ) -> None:
    config = configparser.ConfigParser()
    config["GLOBAL"] = {
      "pants_version": pants_version,
      "plugins": "['pantsbuild.pants.contrib.go==%(pants_version)s']"
    }
    if python_version is not None:
      config["GLOBAL"]["pants_runtime_python_version"] = python_version
    with open(f"{parent_folder}/pants.ini", "w") as f:
      config.write(f)

  def create_dummy_build(self, *, parent_folder: str) -> None:
    with open(f"{parent_folder}/BUILD", "w") as f:
      f.write("target(name='test')\n")
