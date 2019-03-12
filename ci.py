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


PANTS_INI = 'pants.ini'


def main() -> None:
  args = create_parser().parse_args()
  run_tests(pants_version=args.pants_version)


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


def run_tests(*, pants_version: PantsVersion) -> None:
  version_command = ["./pants", "--version"]
  list_command = ["./pants", "list", "::"]
  env_with_pantsd = {**os.environ, "PANTS_ENABLE_PANTSD": "True"}
  with setup_pants_version(pants_version):
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
      f.writelines(line for line in original_pants_ini if "pants_version" not in line)
  yield
  with open(PANTS_INI, 'w') as f:
    f.writelines(original_pants_ini)    


if __name__ == "__main__":
  main()
