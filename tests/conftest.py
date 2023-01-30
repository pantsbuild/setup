# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import shutil
from pathlib import Path
from typing import Optional

import pytest
from typing_extensions import Protocol


# There are no stubs for pytest and it is not in the typeshed so we model the type of the one
# API we use on this rather large class:
#   https://docs.pytest.org/en/latest/reference.html#_pytest.monkeypatch.MonkeyPatch.setenv
class MonkeyPatch(Protocol):
    def setenv(self, name: str, value: str, prepend: Optional[str] = None) -> None:
        ...


@pytest.fixture
def build_root(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    monkeypatch.setenv("PANTS_SETUP_CACHE", str(tmp_path / "PANTS_SETUP_CACHE"))

    # NB: Unlike the install guide's instruction to curl the `./pants` script, we directly
    # copy it to ensure we are using the branch's version of the script and to avoid
    # network pings.
    build_root = tmp_path / "project_dir"
    build_root.mkdir()
    shutil.copy("./pants", str(build_root / "pants"))
    return build_root
