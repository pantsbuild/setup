# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from pathlib import Path
from textwrap import dedent


def create_pants_config(
    *, parent_folder: Path, pants_version: str, quote: str = '"', suffix: str = ""
) -> None:
    # NB: string comparison is not always correct for semvers, but it works in the
    #  cases we care about for testing.
    extra = ""
    if pants_version <= "1.28":
        extra = 'plugins = ["pantsbuild.pants.contrib.go==%(pants_version)s"]'

    (parent_folder / "pants.toml").write_text(
        dedent(
            f"""\
            [GLOBAL]
            pants_version = {quote}{pants_version}{quote}{suffix}
            backend_packages = ["pants.backend.python"]
            {extra}
            """
        )
    )
