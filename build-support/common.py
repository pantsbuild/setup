# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Utils for scripts to interface with the outside world."""

import configparser
import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Tuple

# --------------------------------------------------------
# Logging utils
# --------------------------------------------------------

_SCRIPT_START_TIME = time.time()

_CLEAR_LINE = "\x1b[K"
_COLOR_BLUE = "\x1b[34m"
_COLOR_RED = "\x1b[31m"
_COLOR_GREEN = "\x1b[32m"
_COLOR_RESET = "\x1b[0m"


def die(message: str) -> None:
  raise SystemExit(f"{_COLOR_RED}{message}{_COLOR_RESET}")


def green(message: str) -> None:
  print(f"{_COLOR_GREEN}{message}{_COLOR_RESET}")


def banner(message: str) -> None:
  minutes, seconds = elapsed_time()
  print(f"{_COLOR_BLUE}[=== {minutes:02d}:{seconds:02d} {message} ===]{_COLOR_RESET}")


def elapsed_time() -> Tuple[int, int]:
  now = time.time()
  elapsed_seconds = int(now - _SCRIPT_START_TIME)
  return elapsed_seconds // 60, elapsed_seconds % 60


@contextmanager
def travis_section(slug: str, message: str):
  travis_fold_state = "/tmp/.travis_fold_current"

  def travis_fold(action: str, target: str) -> None:
    print(f"travis_fold:{action}:{target}\r{_CLEAR_LINE}", end="")

  def read_travis_fold_state() -> str:
    with open(travis_fold_state, "r") as f:
      return f.readline()

  def write_slug_to_travis_fold_state() -> None:
    with open(travis_fold_state, "w") as f:
      f.write(slug)

  def remove_travis_fold_state() -> None:
    Path(travis_fold_state).unlink()

  travis_fold("start", slug)
  write_slug_to_travis_fold_state()
  banner(message)
  try:
    yield
  finally:
    travis_fold("end", read_travis_fold_state())
    remove_travis_fold_state()

# --------------------------------------------------------
# Setup hermetic environment
# --------------------------------------------------------

@contextmanager
def copy_pants_into_tmpdir():
  with tempfile.TemporaryDirectory() as tmpdir:
    # NB: Unlike the install guide's instruction to curl the `./pants` script, we directly
    # copy it to ensure we are using the branch's version of the script and to avoid
    # network pings.
    shutil.copy("pants", f"{tmpdir}/pants")
    yield tmpdir


@contextmanager
def set_pants_cache_to_tmpdir():
  with tempfile.TemporaryDirectory() as tmpdir:
    original_env = os.environ.copy()
    os.environ["PANTS_HOME"] = tmpdir
    try:
      yield
    finally:
      os.environ = original_env


@contextmanager
def setup_pants_in_tmpdir():
  with set_pants_cache_to_tmpdir(), copy_pants_into_tmpdir() as buildroot_tmpdir:
    yield buildroot_tmpdir

# --------------------------------------------------------
# Rewrite pants.ini
# --------------------------------------------------------

PANTS_INI = 'pants.ini'
CONFIG_GLOBAL_SECTION = "GLOBAL"


def read_config() -> configparser.ConfigParser:
  cp = configparser.ConfigParser(delimiters=[":"])
  cp.read(PANTS_INI)
  return cp


def write_config(config: configparser.ConfigParser) -> None:
  with open(PANTS_INI, 'w') as f:
    config.write(f)


@contextmanager
def temporarily_rewrite_config(updated_config: configparser.ConfigParser):
  with open(PANTS_INI, "r") as f:
    original_config = f.read()
  write_config(updated_config)
  try:
    yield
  finally:
    with open(PANTS_INI, "w") as f:
      f.write(original_config)
