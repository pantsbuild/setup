# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import configparser
from pathlib import Path
from typing import Any, Dict

import toml


def create_pants_config(*, parent_folder: Path, pants_version: str, use_toml: bool = True) -> None:
    global_section: Dict[str, Any] = {
        "pants_version": pants_version,
        "backend_packages": ["pants.backend.python"],
    }
    # NB: string comparison is not always correct for semvers, but it works in the
    #  cases we care about for testing.
    if pants_version <= "1.28":
        global_section["plugins"] = ["pantsbuild.pants.contrib.go==%(pants_version)s"]

    if use_toml:
        with (parent_folder / "pants.toml").open("w") as f:
            toml.dump({"GLOBAL": global_section}, f)
    else:
        cp = configparser.ConfigParser()
        cp["GLOBAL"] = global_section
        with (parent_folder / "pants.ini").open("w") as f:
            cp.write(f)
