# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import configparser
from pathlib import Path
from typing import Optional

import toml


def create_pants_config(
    *, parent_folder: Path, pants_version: Optional[str], use_toml: bool = True
) -> None:
    # NB: string comparison is not always correct for semvers, but it works in the
    #  cases we care about for testing.
    no_plugin = pants_version and pants_version >= "1.29"
    global_section = {}
    if pants_version:
        global_section["pants_version"] = pants_version
    if not no_plugin:
        global_section["plugins"] = (
            ["pantsbuild.pants.contrib.go==%(pants_version)s"]  # type: ignore
            if pants_version
            else ["pantsbuild.pants.contrib.go"]
        )

    if use_toml:
        config = {"GLOBAL": global_section}
        # TODO: string interpolation does not work for TOML when the value comes from the same
        #  section. This is fixed in Pants 1.26.0.dev1+.
        if pants_version is not None:
            config["GLOBAL"].pop("pants_version")
            config["DEFAULT"] = {"pants_version": pants_version}
        with (parent_folder / "pants.toml").open("w") as f:
            toml.dump(config, f)
    else:
        cp = configparser.ConfigParser()
        cp["GLOBAL"] = global_section
        with (parent_folder / "pants.ini").open("w") as f:
            cp.write(f)
