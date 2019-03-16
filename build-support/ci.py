#!/usr/bin/env python3
# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import argparse
import configparser
import os
import subprocess
from contextlib import contextmanager
from enum import Enum

from common import (CONFIG_GLOBAL_SECTION, PANTS_INI, banner, die, read_config,
                    temporarily_rewrite_config, travis_section)


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
  with setup_pants_version(args.pants_version):
    with setup_python_version(args.python_version):
      run_tests(skip_pantsd_tests=args.skip_pantsd_tests)


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
  parser.add_argument("--skip-pantsd-tests", action="store_true")
  return parser


def run_tests(*, skip_pantsd_tests: bool) -> None:
  version_command = ["./pants", "--version"]
  list_command = ["./pants", "list", "::"]
  env_with_pantsd = {**os.environ, "PANTS_ENABLE_PANTSD": "True"}
  with travis_section("PantsVersion", f"Testing `{' '.join(version_command)}`."):
    subprocess.run(version_command, check=True)
  with travis_section("PantsList", f"Testing `{' '.join(list_command)}`."):
    subprocess.run(list_command, check=True)
  if not skip_pantsd_tests:
    with travis_section("PantsVersionDaemon", f"Testing `{' '.join(version_command)}` with pantsd enabled."):
      subprocess.run(version_command, env=env_with_pantsd, check=True)
    with travis_section("PantsListDaemon", f"Testing `{' '.join(list_command)}` with pantsd enabled."):
      subprocess.run(list_command, env=env_with_pantsd, check=True)


@contextmanager
def setup_pants_version(test_pants_version: PantsVersion):
  """Modify pants.ini to allow the pants version to be unspecified or keep what was originally there."""
  updated_config = read_config()
  config_entry = "pants_version"
  if test_pants_version == PantsVersion.unspecified:
    updated_config.remove_option(CONFIG_GLOBAL_SECTION, config_entry)
    # NB: We also remove plugins as they refer to the pants_version.
    updated_config.remove_option(CONFIG_GLOBAL_SECTION, "plugins")
    banner(f"Temporarily removing `{config_entry}` from pants.ini.")
  elif test_pants_version == PantsVersion.config:
    if config_entry not in updated_config[CONFIG_GLOBAL_SECTION]:
      die(f"You requested to use `{config_entry}` from pants.ini, but pants.ini does not include `{config_entry}`!")
    current_pants_version = updated_config[CONFIG_GLOBAL_SECTION][config_entry]
    banner(f"Using the `{config_entry}` set in pants.ini: `{current_pants_version}`.")
  with temporarily_rewrite_config(updated_config):
    yield


@contextmanager
def setup_python_version(test_python_version: PythonVersion):
  """Modify pants.ini to allow the Python version to be unspecified or change to what was requested."""
  updated_config = read_config()
  config_entry = "pants_runtime_python_version"
  if test_python_version == PythonVersion.unspecified:
    updated_config.remove_option(CONFIG_GLOBAL_SECTION, config_entry)
    banner(f"Temporarily removing `{config_entry}` from pants.ini.")
  else:
    updated_config[CONFIG_GLOBAL_SECTION][config_entry] = test_python_version.value
    banner(f"Temporarily rewriting `{config_entry}` to `{test_pants_version}`.")
  with temporarily_rewrite_config(updated_config):
    yield


if __name__ == "__main__":
  main()
