#!/usr/bin/env python3
# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Test that auto-generation of pants.ini works as expected.

Note this is a separate file from ci.py because we only want to test the auto-generation
part of ./pants here, and leave it to ci.py to test the other behavior like correctly
parsing values from pants.ini and that the virtual env actually works. """

import configparser
import subprocess
import unittest
from contextlib import contextmanager
from pathlib import Path

from ci import PantsVersion, setup_pants_version
from common import (CONFIG_GLOBAL_SECTION, PANTS_INI, banner, read_config,
                    temporarily_remove_config, travis_section)


class TestPantsIniAutogen(unittest.TestCase):

  @contextmanager
  def autogen_pants_ini(self):
    banner("Temporarily removing pants.ini.")
    with temporarily_remove_config():
      subprocess.run(["./pants"], check=True)
      yield
    banner("Restoring original pants.ini.")

  def test_file_created(self) -> None:
    with self.autogen_pants_ini():
      self.assertTrue(Path(PANTS_INI).is_file())


  def test_pants_versions_pinned_properly(self) -> None:
    with self.autogen_pants_ini():
      config = read_config()
      self.assertIn("pants_version", config[CONFIG_GLOBAL_SECTION])
      pinned_pants_version = config[CONFIG_GLOBAL_SECTION]["pants_version"]
      with setup_pants_version(PantsVersion.unspecified):
        unconfigured_pants_version = subprocess.run(
          ["./pants", "-V"], stdout=subprocess.PIPE, encoding="utf-8", check=True
        ).stdout.strip()
      self.assertEqual(pinned_pants_version, unconfigured_pants_version)


if __name__ == "__main__":
  with travis_section("PantsIniAutoGen", "Testing auto-generation of pants.ini."):
    unittest.main()
