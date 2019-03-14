#!/usr/bin/env python3
# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import argparse
import os
import subprocess
from contextlib import contextmanager
from enum import Enum
from typing import List, Iterable, Optional


PANTS_INI = 'pants.ini'


class PantsVersion(Enum):
  unspecified = "unspecified"
  config = "config"

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
  run_tests(test_pants_version=args.pants_version, test_python_version=args.python_version)


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


def run_tests(*, test_pants_version: PantsVersion, test_python_version: PythonVersion) -> None:
  version_command = ["./pants", "--version"]
  list_command = ["./pants", "list", "::"]
  env_with_pantsd = {**os.environ, "PANTS_ENABLE_PANTSD": "True"}
  with setup_pants_version(test_pants_version):
    with setup_python_version(test_python_version):
      subprocess.run(version_command, check=True)
      subprocess.run(list_command, check=True)
      subprocess.run(version_command, env=env_with_pantsd, check=True)
      subprocess.run(list_command, env=env_with_pantsd, check=True)


@contextmanager
def setup_pants_version(test_pants_version: PantsVersion):
  """Modify pants.ini to allow the pants version to be unspecified or keep what was originally there."""
  original_lines = read_pants_ini()
  if test_pants_version == PantsVersion.unspecified:
    write_config_entry("pants_version", None)
  elif test_pants_version == PantsVersion.config:
    pants_version_defined = any(line.startswith("pants_version") for line in original_lines)
    if not pants_version_defined:
      raise ValueError("You requested to use the pants_version from pants.ini for this test, but pants.ini "
                       "does not include a pants_version! Please update pants.ini and run again.")
  yield
  write_pants_ini(original_lines)


@contextmanager
def setup_python_version(test_python_version: PythonVersion):
  """Modify pants.ini to allow the Python version to be unspecified or change to what was requested."""
  original_lines = read_pants_ini()
  requested_python_version = None if test_python_version == PythonVersion.unspecified else test_python_version.value
  write_config_entry(entry_name="pants_runtime_python_version", entry_value=requested_python_version)
  yield
  write_pants_ini(original_lines)


def read_pants_ini() -> List[str]:
  with open(PANTS_INI, 'r') as f:
    return list(f.readlines())


def write_pants_ini(lines: Iterable[str]) -> None:
  with open(PANTS_INI, 'w') as f:
    f.writelines(lines)


def write_config_entry(*, entry_name: str, entry_value: Optional[str]) -> None:
  """Rewrite the entry in pants.ini to use the given value, entirely removing the entry if entry_value is None."""
  original_lines = read_pants_ini()
  entry_already_defined = any(line.startswith(entry_name) for line in original_lines)
  # import pdb; pdb.set_trace()
  if entry_value is None and not entry_already_defined:
    new_lines = original_lines
  elif entry_value is None and entry_already_defined:
    new_lines = (line for line in original_lines if entry_name not in line)
  elif entry_value is not None and entry_already_defined:
    new_lines = (line if not line.startswith(entry_name) else f"{entry_name}: {entry_value}" for line in original_lines)
  else:
    global_section_header_index = next((i for i, line in enumerate(original_lines) if "[GLOBAL]" in line), None)
    if global_section_header_index is None:
      raise ValueError("Your pants.ini is missing a [GLOBAL] section header. Please add this and run again.")
    new_lines = original_lines
    new_lines.insert(global_section_header_index + 1, f"{entry_name}: {entry_value}")
  write_pants_ini(new_lines)


if __name__ == "__main__":
  main()
