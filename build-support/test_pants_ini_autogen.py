#!/usr/bin/env python3
# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Test that auto-generation of pants.ini works as expected.

Note this is a separate file from ci.py because we only want to test the auto-generation
part of ./pants here, and leave it to ci.py to test the other behavior like correctly
parsing values from pants.ini and that the virtual env actually works. """

import configparser
import subprocess
from pathlib import Path

from ci import PantsVersion, setup_pants_version
from common import (CONFIG_GLOBAL_SECTION, PANTS_INI, die, read_config,
                    temporarily_remove_config, travis_section)


def main() -> None:
  with travis_section("PantsIniAutoGen", "Testing auto-generation of pants.ini."):
    with temporarily_remove_config():
      subprocess.run(["./pants"], check=True)
      assert_file_created()
      config = read_config()
      assert_pants_version_pinned_properly(config)


def assert_file_created() -> None:
  if not Path(PANTS_INI).is_file():
    die("pants.ini not created in the repo root.")


def assert_pants_version_pinned_properly(config: configparser.ConfigParser) -> None:
  if "pants_version" not in config[CONFIG_GLOBAL_SECTION]:
    die("`pants_version` not pinned.")
  pinned_pants_v = config[CONFIG_GLOBAL_SECTION]["pants_version"]
  with setup_pants_version(PantsVersion.unspecified):
    unconfigured_pants_v = subprocess.run(
      ["./pants", "-V"], stdout=subprocess.PIPE, encoding="utf-8", check=True
    ).stdout.strip()
  if pinned_pants_v != unconfigured_pants_v:
    die(f"The pinned `pants_version` ({pinned_pants_v}) does not match the value when "
        f"leaving `pants_version` unspecified ({unconfigured_pants_v}).")


if __name__ == "__main__":
  main()
