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
  config = "config"

  def __str__(self):
      return self.value


def main() -> None:
  args = create_parser().parse_args()
  run_tests(test_pants_version=args.pants_version)


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
  return parser


def run_tests(*, test_pants_version: PantsVersion) -> None:
  version_command = ["./pants", "--version"]
  list_command = ["./pants", "list", "::"]
  env_with_pantsd = {**os.environ, "PANTS_ENABLE_PANTSD": "True"}
  with setup_pants_version(test_pants_version):
    subprocess.run(version_command).check_returncode()
    subprocess.run(list_command).check_returncode()
    subprocess.run(version_command, env=env_with_pantsd).check_returncode()
    subprocess.run(list_command, env=env_with_pantsd).check_returncode()


@contextmanager
def setup_pants_version(test_pants_version: PantsVersion):
  """Modify pants.ini to allow the pants version to be unspecified or keep what was originally there."""
  with open(PANTS_INI, 'r') as f:
    original_pants_ini = list(f.readlines())
  pants_version_already_specified = any(line.startswith("pants_version:") for line in original_pants_ini)
  if test_pants_version == PantsVersion.config and not pants_version_already_specified:
    raise ValueError("You requested to use the pants_version from pants.ini for this test, but pants.ini "
                     "does not include a pants_version! Please update pants.ini and run again.")
  if test_pants_version == PantsVersion.unspecified and pants_version_already_specified:
    with open(PANTS_INI, 'w') as f:
      # NB: we must not only remove the original definition of `pants_version`, but also
      # any lines that make use of it, such as contrib packages pinning their version to `pants_version`.
      f.writelines(line for line in original_pants_ini if "pants_version" not in line)
  yield
  with open(PANTS_INI, 'w') as f:
    f.writelines(original_pants_ini)


if __name__ == "__main__":
  main()
