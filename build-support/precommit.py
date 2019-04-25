#!/usr/bin/env python3
# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import subprocess

import mypy
import shellcheck


def main() -> None:
  print("* Checking shell scripts via shellcheck")
  shellcheck.main()

  print("\n* Checking import order")
  subprocess.run(["./pants", "fmt.isort", "::", "--", "--check-only"], check=True)

  print("\n* Checking lint")
  subprocess.run(["./pants", "lint", "::"], check=True)

  print("\n* Checking types")
  mypy.main()


if __name__ == "__main__":
  main()
