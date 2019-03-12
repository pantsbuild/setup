#!/usr/bin/env python3
# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import argparse
import os
import subprocess
from contextlib import contextmanager
from enum import Enum


PANTS_INI = 'pants.ini'


class PantsVersion(Enum):
  unspecified = "unspecified"
  pants_ini = "pants.ini"

  def __str__(self):
      return self.value


class PythonVersion(Enum):
  unspecified = "unspecified"
  py27 = "2.7"
  py36 = "3.6"
  py37 = "3.7"
  
  def __str__(self):
    return self.value


def main() -> None:
  args = create_parser().parse_args()
  run_tests(pants_version=args.pants_version, python_version=args.python_version)


def create_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(description="Utility to run CI for the setup repo.")
  parser.add_argument(
      "--pants-version",
      action="store",
      type=PantsVersion,
      choices=list(PantsVersion),
      required=True,
      help="Pants version to configure ./pants to use."
  )
  parser.add_argument(
      "--python-version",
      action="store",
      type=PythonVersion,
      choices=list(PythonVersion),
      required=True,
      help="Python version to configure ./pants to use."
  )
  return parser


def run_tests(*, pants_version: PantsVersion, python_version: PythonVersion) -> None:
  version_command = ["./pants", "--version"]
  list_command = ["./pants", "list", "::"]
  with setup_pants_version(pants_version):
    with setup_python_version(python_version):
      # NB: this env must be defined within the context manager setup_python_version()
      # to pick up its changes. Once we change the context manager to instead modify
      # pants.ini, we should move this line back up to the root level of this function.
      env_with_pantsd = {**os.environ, "PANTS_ENABLE_PANTSD": "True"}
      subprocess.run(version_command)
      subprocess.run(list_command)
      subprocess.run(version_command, env=env_with_pantsd)
      subprocess.run(list_command, env=env_with_pantsd)


@contextmanager
def setup_pants_version(pants_version: PantsVersion):
  """Modify pants.ini to allow the pants version to be unspecified or keep what was originally there."""
  with open(PANTS_INI, 'r') as f:
    original_pants_ini = list(f.readlines())
  pants_version_specified = any(line.startswith("pants_version:") for line in original_pants_ini)
  if pants_version == PantsVersion.pants_ini and not pants_version_specified:
    raise ValueError("You requested to use the pants_version from pants.ini for this test, but pants.ini "
                     "does not include a pants_version! Please update pants.ini and run again.")
  if pants_version == PantsVersion.unspecified and pants_version_specified:
    with open(PANTS_INI, 'w') as f:
      # NB: we must not only remove the original definition of `pants_version`, but also
      # any lines that make use of it, such as contrib packages pinning their version to `pants_version`.
      f.writelines(line for line in original_pants_ini if "pants_version" not in line)
  yield
  with open(PANTS_INI, 'w') as f:
    f.writelines(original_pants_ini)


@contextmanager
def setup_python_version(test_python_version: PythonVersion):
  """Modify pants.ini to allow the Python version to be unspecified or change to what was requested."""
  expected_prefix = "pants_engine_python_version"
  new_line = f"{expected_prefix}: {test_python_version.value}\n"
  with open(PANTS_INI, 'r') as f:
    original_pants_ini = list(f.readlines())
  python_version_specified = any(line.startswith(expected_prefix) for line in original_pants_ini)
  if test_python_version == PantsVersion.unspecified and python_version_specified:
    with open(PANTS_INI, 'w') as f:
      f.writelines(line for line in original_pants_ini if not line.startswith(expected_prefix))
  if test_python_version != PantsVersion.unspecified and python_version_specified:
    with open(PANTS_INI, 'w') as f:
      f.writelines(
          new_line if line.startswith(expected_prefix) else line
          for line in original_pants_ini
      )
  if test_python_version != PantsVersion.unspecified and not python_version_specified:
    with open(PANTS_INI, 'w') as f:
      global_section_header_index = next((i for i, line in enumerate(original_pants_ini) if "[GLOBAL]" in line), None)
      if global_section_header_index is None:
        raise ValueError(f"You requested to use the python version {test_python_version}, but your "
                         "pants.ini is missing a [GLOBAL] section header. Please add this and run again.")
      new_lines = (original_pants_ini[:global_section_header_index]
          + [new_line]
          + original_pants_ini[global_section_header_index:])
      f.writelines(new_line)
  yield
  with open(PANTS_INI, 'w') as f:
    f.writelines(original_pants_ini)


if __name__ == "__main__":
  main()
