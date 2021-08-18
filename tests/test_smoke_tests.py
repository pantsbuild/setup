# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Test that `./pants` works correctly with some basic sanity checks."""
import dataclasses
import os
import shlex
import shutil
import subprocess
import tempfile
import textwrap
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Mapping, Optional

import pytest
from helpers import create_pants_config


@pytest.fixture(scope="module")
def pyenv_bin() -> str:
    pyenv_bin = os.environ.get("PYENV_BIN") or shutil.which("pyenv")
    if pyenv_bin is None:
        raise ValueError(
            "Pyenv must be installed. The binary `pyenv` must either be discoverable from "
            "the `$PATH` or you must set the environment variable `PYENV_BIN`."
        )
    return pyenv_bin


@pytest.fixture(scope="module")
def pyenv_versions(pyenv_bin: str) -> List[str]:
    return subprocess.run(
        [pyenv_bin, "versions", "--bare", "--skip-aliases"],
        stdout=subprocess.PIPE,
        encoding="utf-8",
        check=True,
    ).stdout.splitlines()


@dataclass(frozen=True)
class SmokeTester:
    pyenv_bin: str
    pyenv_versions: List[str]
    build_root: Path

    @dataclass(frozen=True)
    class PythonSetup:
        extra_env: Mapping[str, str] = dataclasses.field(default_factory=lambda: {})
        bad_python_exes: Iterable[Path] = ()

        @contextmanager
        def deactivate_bad_aliases(self) -> Iterator[None]:
            for exe in self.bad_python_exes:
                exe.chmod(0o644)
                exe.rename(exe.parent / f"DISABLED_{exe.name}")
            try:
                yield
            finally:
                for exe in self.bad_python_exes:
                    renamed_exe = exe.parent / f"DISABLED_{exe.name}"
                    renamed_exe.rename(exe)
                    exe.chmod(0o755)

    @contextmanager
    def _maybe_setup_python(
        self,
        python_version: Optional[str],
        *,
        alias: Optional[str] = None,
        bad_aliases: Optional[Mapping[str, str]] = None,
    ) -> Iterator[PythonSetup]:
        if python_version is None:
            yield self.PythonSetup()
            return

        def is_compatible(pyenv_version: str) -> bool:
            major, minor = pyenv_version.split(".")[:2]
            return f"{major}.{minor}" == python_version

        compatible_pyenv_version = next(
            (
                pyenv_version
                for pyenv_version in self.pyenv_versions
                if is_compatible(pyenv_version)
            ),
            None,
        )
        if compatible_pyenv_version is None:
            raise ValueError(
                f"Python {python_version} is not installed via Pyenv. Please install with "
                f"`pyenv install`. All installed versions: {', '.join(self.pyenv_versions)}."
            )

        if alias:
            with self._setup_alias(compatible_pyenv_version, alias, bad_aliases) as python_setup:
                yield python_setup
        else:
            with self._run_pyenv_local(compatible_pyenv_version):
                yield self.PythonSetup()

    @staticmethod
    def which(*exe_names: str, fallible: bool = False) -> Mapping[str, Path]:
        return {
            exe.name: exe
            for exe in map(
                Path,
                subprocess.run(
                    [
                        "/usr/bin/env",
                        "bash",
                        "-c",
                        f"command -v {' '.join(shlex.quote(exe_name) for exe_name in exe_names)}",
                    ],
                    check=not fallible,
                    stdout=subprocess.PIPE,
                )
                .stdout.decode()
                .splitlines(),
            )
        }

    @contextmanager
    def _setup_alias(
        self, python_version: str, alias: str, bad_aliases: Optional[Mapping[str, str]] = None
    ) -> Iterator[PythonSetup]:
        pyenv_root = Path(
            subprocess.run([self.pyenv_bin, "root"], check=True, stdout=subprocess.PIPE)
            .stdout.decode()
            .strip()
        )
        with tempfile.TemporaryDirectory(prefix="isolated.", suffix=".bin") as temp_dir:
            path_component = Path(temp_dir)
            python_alias = path_component / alias
            pyenv_python_exe_path = pyenv_root / "versions" / python_version / "bin" / "python"
            python_alias.symlink_to(pyenv_python_exe_path.resolve())

            required_exes = self.which(
                "as",
                "bash",
                "cat",
                "clang",
                "curl",
                "cut",
                "dirname",
                "gcc",
                "ld",
                "ln",
                "mkdir",
                "mktemp",
                "mv",
                "rm",
                "rmdir",
                "sed",
                "tr",
                "uname",
                # Only one of clang or gcc need be present making this call fallible. If other
                # binaries fail to be present, the pants run will fail in an obvious way printing
                # out the missing binary name.
                fallible=True,
            )
            for name, path in required_exes.items():
                (path_component / name).symlink_to(path)

            bad_python_exes = []
            if bad_aliases:
                for alias, version_output in bad_aliases.items():
                    bad_python_exe = path_component / alias
                    bad_python_exe.write_text(
                        textwrap.dedent(
                            f"""\
                            #!{required_exes["bash"]}

                            echo ">>> Bad Python EXE reporting version: {version_output}" >&2
                            echo "{version_output}"
                            """
                        )
                    )
                    bad_python_exe.chmod(0o755)
                    bad_python_exes.append(bad_python_exe)

            yield self.PythonSetup(
                extra_env={"PATH": temp_dir}, bad_python_exes=frozenset(bad_python_exes)
            )

    @contextmanager
    def _run_pyenv_local(self, python_version: str) -> Iterator[None]:
        subprocess.run(
            [self.pyenv_bin, "local", python_version],
            cwd=str(self.build_root),
            check=True,
        )
        try:
            yield
        finally:
            subprocess.run(
                [self.pyenv_bin, "local", "--unset", python_version],
                cwd=str(self.build_root),
                check=True,
            )

    def smoke_test(
        self,
        *,
        pants_version: str,
        python_version: Optional[str],
        alias: Optional[str] = None,
        bad_aliases: Optional[Mapping[str, str]] = None,
        sha: Optional[str] = None,
    ) -> None:
        env = {**os.environ}
        if sha:
            env["PANTS_SHA"] = sha
        version_command = ["./pants", "--version"]
        list_command = ["./pants", "list", "::"]
        if pants_version.startswith("1"):
            goal = "binary"
            tgt_type = "python_binary"
        else:
            goal = "package"
            tgt_type = "pex_binary"
            # Force the pex_binary to use this interpreter constraint so that pantsbuild.pants is
            # resolvable via the pants_requirement().
            env["PANTS_PYTHON_SETUP_INTERPRETER_CONSTRAINTS"] = "['==3.7.*']"
        binary_command = ["./pants", goal, "//:bin"]
        with self._maybe_setup_python(
            python_version, alias=alias, bad_aliases=bad_aliases
        ) as python_setup:
            create_pants_config(parent_folder=self.build_root, pants_version=pants_version)
            (self.build_root / "BUILD").write_text(
                textwrap.dedent(
                    f"""
                    target(name='test')

                    # To test that we can resolve these, esp. against custom shas.
                    pants_requirement(name='pantsreq')
                    {tgt_type}(name='bin', dependencies=[':pantsreq'], entry_point='fake')
                    """
                )
            )

            def run_command(command: List[str], **kwargs: Any) -> None:
                subprocess.run(command, check=True, cwd=str(self.build_root), **kwargs)

            def run_binary_command(**kwargs: Any) -> None:
                # Prevent the binary_command from seeing any bogus python interpreters we're using
                # to test bootstrap.
                with python_setup.deactivate_bad_aliases():
                    run_command(binary_command, env=env)

            env = {**env, **python_setup.extra_env}
            run_command(version_command, env=env)
            run_command(list_command, env=env)
            run_binary_command(env=env)
            if "SKIP_PANTSD_TESTS" not in env:
                env_with_pantsd = {**env, "PANTS_ENABLE_PANTSD": "True"}
                run_command(version_command, env=env_with_pantsd)
                run_command(list_command, env=env_with_pantsd)
                run_binary_command(env=env_with_pantsd)

    def smoke_test_for_all_python_versions(self, *python_versions: str, pants_version: str) -> None:
        for python_version in python_versions:
            self.smoke_test(pants_version=pants_version, python_version=python_version)


@pytest.fixture
def checker(pyenv_bin: str, pyenv_versions: List[str], build_root: Path) -> SmokeTester:
    return SmokeTester(pyenv_bin=pyenv_bin, pyenv_versions=pyenv_versions, build_root=build_root)


def test_pants_1(checker: SmokeTester) -> None:
    checker.smoke_test(python_version=None, pants_version="1.30.4")
    checker.smoke_test_for_all_python_versions("3.6", "3.7", "3.8", pants_version="1.30.4")


def test_pants_2(checker: SmokeTester) -> None:
    checker.smoke_test(python_version=None, pants_version="2.3.0")
    checker.smoke_test_for_all_python_versions("3.7", "3.8", pants_version="2.3.0")


def test_pants_at_sha(checker: SmokeTester) -> None:
    sha = "e4a00eb2750d00371cfe1d438c872ec3ea926369"
    version = "2.3.0.dev6+gite4a00eb"
    checker.smoke_test(python_version=None, pants_version=version, sha=sha)


def test_python_alias(checker: SmokeTester) -> None:
    checker.smoke_test(python_version="3.6", pants_version="1.30.4", alias="python3")
    checker.smoke_test(
        python_version="3.7",
        pants_version="2.3.0",
        alias="python",
        bad_aliases={"python3.7": "35", "python3": "27"},
    )
