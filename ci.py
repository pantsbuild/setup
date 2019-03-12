#!/usr/bin/env python3
# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import argparse
import os
import subprocess
from contextlib import contextmanager
from enum import Enum


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


PANTS_INI = 'pants.ini'


def main() -> None:
  args = create_parser().parse_args()
  run_tests(pants_version=args.pants_version, python_version=args.python_version)


def create_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
    description="Utility to run CI for the setup repo."
  )
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
  """Modify pants.ini to allow the pants version to be unspecified or what it originally was in pants.ini."""
  with open(PANTS_INI, 'r') as f:
    original_pants_ini = list(f.readlines())
  pants_version_line_index = next(
    (i for i, line in enumerate(original_pants_ini) if line.startswith("pants_version:")),
    None
  )
  if pants_version == PantsVersion.pants_ini and pants_version_line_index is None:
    raise ValueError("You requested to use the pants_version from pants.ini for this test, but pants.ini "
                     "does not include a pants_version! Please update pants.ini and run again.")
  if pants_version == PantsVersion.unspecified and pants_version_line_index is not None:
    with open(PANTS_INI, 'w') as f:
      f.writelines(line for i, line in enumerate(original_pants_ini) if i != pants_version_line_index)
  yield
  with open(PANTS_INI, 'w') as f:
    f.writelines(original_pants_ini)    


@contextmanager
def setup_python_version(python_version: PythonVersion):
  # TODO: modify this test to change pants.ini like we do in setup_pants_version!
  # Right now we are only testing that the virtual environment resolves properly, and
  # can't yet test that we parse pants.ini correctly until https://github.com/pantsbuild/pants/pull/7363
  # gets merged and is released with Pants.
  original_env = os.environ
  if python_version != PythonVersion.unspecified:
    os.environ = {**original_env, "PYTHON": f"python{python_version.value}"}
  yield
  os.environ = original_env   


if __name__ == "__main__":
  main()
