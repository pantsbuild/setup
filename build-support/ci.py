#!/usr/bin/env python3
# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import argparse
import itertools
import os
import subprocess
from contextlib import contextmanager
from enum import Enum
from typing import Iterator, List

from common import (CONFIG_GLOBAL_SECTION, banner, die, read_config,
                    temporarily_rewrite_config, travis_section)


class PantsVersion(Enum):
  config = "config"
  # NB: we test all of the below Pants versions because they each represent
  # a boundary in our Python 3 migration, as follows:
  # * <= 1.14.0: Python 2.7
  # * == 1.15.0: Python 2.7 or 3.6
  # * == 1.16.0: Python 2.7, 3.6, or 3.7
  # * >= 1.17.0: Python 3.6 or 3.7
  one_fourteen = "1.14.0"
  one_fifteen = "1.15.0"
  one_sixteen = "1.16.0"
  one_seventeen = "1.17.0"

  def __str__(self) -> str:
      return str(self.value)


class PythonVersion(Enum):
  unspecified = "unspecified"
  py27 = "2.7"
  py36 = "3.6"
  py37 = "3.7"

  def __str__(self) -> str:
    return str(self.value)


def main() -> None:
  args = create_parser().parse_args()
  envs = itertools.product(args.pants_versions, args.python_versions)
  skip_pantsd_tests = args.skip_pantsd_tests or "SKIP_PANTSD_TESTS" in os.environ
  for pants_version, python_version in envs:
    run_tests_with_env(
      pants_version=pants_version,
      python_version=python_version,
      skip_pantsd_tests=skip_pantsd_tests
    )


def create_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(description="Utility to run CI for the setup repo.")
  parser.add_argument(
      "--pants-versions",
      action="store",
      type=PantsVersion,
      choices=list(PantsVersion),
      required=True,
      nargs="+",
      help="Pants version to configure ./pants to use."
  )
  parser.add_argument(
      "--python-versions",
      action="store",
      type=PythonVersion,
      choices=list(PythonVersion),
      required=True,
      nargs="+",
      help="Python version to configure ./pants to use."
  )
  parser.add_argument("--skip-pantsd-tests", action="store_true")
  return parser


def run_tests_with_env(*,
    pants_version: PantsVersion, python_version: PythonVersion, skip_pantsd_tests: bool
  ) -> None:
  slug = f"Tests_{pants_version}_{python_version}"
  banner_message = f"Running tests with `--pants-version={pants_version}` and `--python_version={python_version}`."
  with travis_section(slug, banner_message):
    with setup_pants_version(pants_version), setup_python_version(python_version):
      run_tests(skip_pantsd_tests=skip_pantsd_tests)


def run_tests(*, skip_pantsd_tests: bool) -> None:
  version_command = ["./pants", "--version"]
  list_command = ["./pants", "list", "::"]

  def run_test(command: List[str]) -> None:
    banner(f"Testing `{' '.join(command)}`.")
    subprocess.run(command, check=True)

  def run_test_with_pantsd(command: List[str]) -> None:
    env_with_pantsd = {**os.environ, "PANTS_ENABLE_PANTSD": "True"}
    banner(f"Testing `{' '.join(command)}` with pantsd enabled.")
    subprocess.run(command, env=env_with_pantsd, check=True)

  run_test(version_command)
  run_test(list_command)
  if not skip_pantsd_tests:
    run_test_with_pantsd(version_command)
    run_test_with_pantsd(list_command)


@contextmanager
def setup_pants_version(test_pants_version: PantsVersion) -> Iterator[None]:
  """Modify pants.ini to allow the pants version to be a specified version or to keep what was originally there."""
  updated_config = read_config()
  config_entry = "pants_version"
  if test_pants_version == PantsVersion.config:
    if config_entry not in updated_config[CONFIG_GLOBAL_SECTION]:
      die(f"You requested to use `{config_entry}` from pants.ini, but pants.ini does not include `{config_entry}`!")
    current_pants_version = updated_config[CONFIG_GLOBAL_SECTION][config_entry]
    banner(f"Using the `{config_entry}` set in pants.ini: `{current_pants_version}`.")
  else:
    updated_config[CONFIG_GLOBAL_SECTION][config_entry] = test_pants_version.value
    banner(f"Temporarily rewriting `{config_entry}` to `{test_pants_version}`.")
  with temporarily_rewrite_config(updated_config):
    yield
  banner(f"Restoring original `{config_entry}` value in pants.ini.")


@contextmanager
def setup_python_version(test_python_version: PythonVersion) -> Iterator[None]:
  """Modify pants.ini to allow the Python version to be unspecified or change to what was requested."""
  updated_config = read_config()
  config_entry = "pants_runtime_python_version"
  if test_python_version == PythonVersion.unspecified:
    updated_config.remove_option(CONFIG_GLOBAL_SECTION, config_entry)
    banner(f"Temporarily removing `{config_entry}` from pants.ini.")
  else:
    updated_config[CONFIG_GLOBAL_SECTION][config_entry] = test_python_version.value
    banner(f"Temporarily rewriting `{config_entry}` to `{test_python_version}`.")
  with temporarily_rewrite_config(updated_config):
    yield
  banner(f"Restoring original `{config_entry}` value in pants.ini.")


if __name__ == "__main__":
  main()
