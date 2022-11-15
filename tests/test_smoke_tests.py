# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Test that `./pants` works correctly with some basic sanity checks."""
import dataclasses
import os
import shlex
import subprocess
import sys
import tempfile
import textwrap
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional

import pytest
from helpers import create_pants_config


@dataclass(frozen=True)
class PythonVersion:
    @classmethod
    def extract(cls, python_exe_path: Path) -> Optional["PythonVersion"]:
        result = subprocess.run(
            args=[
                str(python_exe_path.resolve()),
                "-c",
                "import sys; print('.'.join(map(str, sys.version_info[:2])))",
            ],
            encoding="utf-8",
            stdout=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            return None
        major, minor = map(int, result.stdout.strip().split(".")[:2])
        return cls(major=major, minor=minor)

    major: int
    minor: int
    required: bool = True

    def iter_basenames(self) -> Iterator[str]:
        yield f"python{self.major}.{self.minor}"
        yield f"python{self.major}"
        yield "python"

    def __str__(self) -> str:
        return f"Python {self.major}.{self.minor}"


@dataclass(frozen=True)
class SmokeTester:
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
        python_version: Optional[PythonVersion],
        *,
        alias: Optional[str] = None,
        bad_aliases: Optional[Mapping[str, str]] = None,
    ) -> Iterator[Optional[PythonSetup]]:
        if python_version is None:
            yield self.PythonSetup()
            return

        python_exe_paths = self.which(*python_version.iter_basenames(), fallible=True, all=True)
        python_exe_path: Optional[Path] = None
        attempts: Dict[Path, Optional[PythonVersion]] = {}
        for path in python_exe_paths.values():
            version = PythonVersion.extract(path)
            if python_version == version:
                python_exe_path = path
                break
            attempts[path] = version

        if python_version.required and not python_exe_path:
            versions = [f"{path}: {version or '<broken>'}" for path, version in attempts.items()]
            raise AssertionError(
                f"Testing requires {python_version} installed and available on the $PATH.\n"
                "Found the following Python executables:\n"
                f"{os.linesep.join(versions)}"
            )
        elif not python_exe_path:
            yield None
        elif alias:
            with self._setup_alias(python_exe_path, alias, bad_aliases) as python_setup:
                yield python_setup
        else:
            yield self.PythonSetup()

    @staticmethod
    def which(*exe_names: str, fallible: bool = False, all: bool = False) -> Mapping[str, Path]:
        which = "which -a" if all else "which"
        return {
            exe.name: exe
            for exe in map(
                Path,
                subprocess.run(
                    [
                        "/usr/bin/env",
                        "bash",
                        "-c",
                        f"{which} {' '.join(shlex.quote(exe_name) for exe_name in exe_names)}",
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
        self, python_exe_path: Path, alias: str, bad_aliases: Optional[Mapping[str, str]] = None
    ) -> Iterator[PythonSetup]:
        with tempfile.TemporaryDirectory(prefix="isolated.", suffix=".bin") as temp_dir:
            path_component = Path(temp_dir)
            python_alias = path_component / alias
            python_alias.symlink_to(python_exe_path.resolve())

            required_exes = self.which(
                "as",
                "bash",
                "cat",
                "clang",
                "curl",
                "cut",
                "dirname",
                "gcc",
                "head",
                "ld",
                "ln",
                "mkdir",
                "mktemp",
                "mv",
                "readlink",
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

    def smoke_test(
        self,
        *,
        pants_version: str,
        python_version: Optional[PythonVersion],
        alias: Optional[str] = None,
        bad_aliases: Optional[Mapping[str, str]] = None,
        sha: Optional[str] = None,
        override_version: Optional[str] = None,
    ) -> None:
        env = {**os.environ}
        if sha:
            env["PANTS_SHA"] = sha

        if override_version:
            env["PANTS_VERSION"] = override_version

        version_command = ["./pants", "--version"]
        list_command = ["./pants", "list", "::"]
        bootstrap_cache_key_command = ["./pants", "bootstrap-cache-key"]
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
            if python_setup is None:
                print(f"{python_version} is not present, skipping test.", file=sys.stderr)
                return

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
                assert python_setup is not None  # This is to help mypy figure things out.
                with python_setup.deactivate_bad_aliases():
                    run_command(binary_command, **kwargs)

            env = {**env, **python_setup.extra_env}
            run_command(version_command, env=env)
            run_command(list_command, env=env)
            run_command(bootstrap_cache_key_command, env={**env, "PANTS_BOOTSTRAP_TOOLS": "1"})
            run_binary_command(env=env)
            if "SKIP_PANTSD_TESTS" not in env:
                env_with_pantsd = {**env, "PANTS_ENABLE_PANTSD": "True"}
                run_command(version_command, env=env_with_pantsd)
                run_command(list_command, env=env_with_pantsd)
                run_command(bootstrap_cache_key_command, env={**env, "PANTS_BOOTSTRAP_TOOLS": "1"})
                run_binary_command(env=env_with_pantsd)

    def smoke_test_for_all_python_versions(
        self, *python_versions: PythonVersion, pants_version: str
    ) -> None:
        for python_version in python_versions:
            self.smoke_test(pants_version=pants_version, python_version=python_version)


# We don't require Python 3.6 since it won't be patched to work on macOS 11:
#   https://bugs.python.org/issue43470
PY36 = PythonVersion(3, 6, required=False)
PY37 = PythonVersion(3, 7)
PY38 = PythonVersion(3, 8)


@pytest.fixture
def checker(build_root: Path) -> SmokeTester:
    return SmokeTester(build_root=build_root)


def test_pants_1(checker: SmokeTester) -> None:
    checker.smoke_test(python_version=None, pants_version="1.30.4")
    checker.smoke_test_for_all_python_versions(PY36, PY37, PY38, pants_version="1.30.4")


def test_pants_2(checker: SmokeTester) -> None:
    checker.smoke_test(python_version=None, pants_version="2.3.0")
    checker.smoke_test_for_all_python_versions(PY37, PY38, pants_version="2.3.0")


def test_pants_at_sha(checker: SmokeTester) -> None:
    sha = "e4a00eb2750d00371cfe1d438c872ec3ea926369"
    version = "2.3.0.dev6+gite4a00eb"
    checker.smoke_test(python_version=None, pants_version=version, sha=sha)


def test_pants_at_version(checker: SmokeTester) -> None:
    version = "2.3.0.dev6+gite4a00eb"
    override_version = "2.4.0"
    checker.smoke_test(
        python_version=None, pants_version=version, override_version=override_version
    )


def test_python_alias(checker: SmokeTester) -> None:
    checker.smoke_test(python_version=PY36, pants_version="1.30.4", alias="python3")
    checker.smoke_test(
        python_version=PY37,
        pants_version="2.3.0",
        alias="python",
        bad_aliases={"python3.7": "35", "python3": "27"},
    )


def test_bootstrap_tools_version_checking(checker: SmokeTester) -> None:
    result = subprocess.run(
        ["./pants", "bootstrap-version"],
        check=False,
        cwd=str(checker.build_root),
        env={**os.environ, "PANTS_BOOTSTRAP_TOOLS": "987654321"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1

    assert result.stdout == ""
    assert "is too old for this invocation (with PANTS_BOOTSTRAP_TOOLS=987654321)" in result.stderr
