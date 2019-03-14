#!/usr/bin/env python3
# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import argparse
import configparser
import os
import subprocess
from contextlib import contextmanager
from enum import Enum


PANTS_INI = 'pants.ini'
GLOBAL_SECTION = "GLOBAL"


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
    subprocess.run(version_command, check=True)
    subprocess.run(list_command, check=True)
    subprocess.run(version_command, env=env_with_pantsd, check=True)
    subprocess.run(list_command, env=env_with_pantsd, check=True)


@contextmanager
def setup_pants_version(test_pants_version: PantsVersion):
  """Modify pants.ini to allow the pants version to be unspecified or keep what was originally there."""
  original_config = read_config()
  updated_config = read_config()
  config_entry = "pants_version"
  if test_pants_version == PantsVersion.unspecified:
    updated_config.remove_option(GLOBAL_SECTION, config_entry)
    # NB: We also remove plugins as they refer to the pants_version.
    updated_config.remove_option(GLOBAL_SECTION, "plugins")
  elif test_pants_version == PantsVersion.config:
    if config_entry not in original_config[GLOBAL_SECTION]:
      raise ValueError("You requested to use the pants_version from pants.ini for this test, but pants.ini "
                       "does not include a pants_version!")
  yield
  write_config(original_config)


def read_config() -> configparser.ConfigParser:
  cp = configparser.ConfigParser(delimiters={":"})
  cp.read(PANTS_INI)
  return cp


def write_config(config: configparser.ConfigParser) -> None:
  with open(PANTS_INI, 'w') as f:
    config.write(f, space_around_delimiters=False)


if __name__ == "__main__":
  main()
