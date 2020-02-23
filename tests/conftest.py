# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import shutil
import subprocess
from pathlib import Path, PurePath
from typing import Optional, Protocol

import pytest


@pytest.fixture(scope="session")
def project_root() -> PurePath:
    return PurePath(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            stdout=subprocess.PIPE,
            encoding="utf-8",
            check=True,
            cwd=str(Path(__file__).parent),
        ).stdout.strip()
    )


# There are no stubs for pytest and it is not in the typeshed so we model the type of the one
# API we use on this rather large class:
#   https://docs.pytest.org/en/latest/reference.html#_pytest.monkeypatch.MonkeyPatch.setenv
class MonkeyPatch(Protocol):
    def setenv(self, name: str, value: str, prepend: Optional[str] = None) -> None:
        ...


@pytest.fixture
def build_root(project_root: PurePath, tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    monkeypatch.setenv("PANTS_HOME", str(tmp_path / "PANTS_HOME"))

    # NB: Unlike the install guide's instruction to curl the `./pants` script, we directly
    # copy it to ensure we are using the branch's version of the script and to avoid
    # network pings.
    build_root = tmp_path / "project_dir"
    build_root.mkdir()
    shutil.copy(str(project_root / "pants"), str(build_root / "pants"))
    return build_root
