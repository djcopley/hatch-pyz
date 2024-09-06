from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterable
from zipfile import ZipFile, ZipInfo

from hatchling.builders.plugin.interface import BuilderInterface, IncludedFile
from hatchling.builders.utils import (
    get_reproducible_timestamp,
    normalize_artifact_permissions,
    normalize_file_permissions,
    replace_file,
    set_zip_info_mode,
)

from hatch_pyz.config import PyzConfig

if TYPE_CHECKING:
    from collections.abc import Sequence
    from hatchling.builders.config import BuilderConfig


class ZipappArchive:
    if sys.platform.startswith("win"):
        shebang_encoding = "utf-8"
    else:
        shebang_encoding = sys.getfilesystemencoding()

    def __init__(self, *, reproducible: bool, compressed: bool, interpreter: str):
        self.reproducible = reproducible

        raw_fd, self.path = tempfile.mkstemp(suffix=".pyz")
        self.fd = os.fdopen(raw_fd, "w+b")

        shebang = b"#!" + interpreter.encode(self.shebang_encoding) + b"\n"
        self.fd.write(shebang)

        compression = zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED
        self.zf = ZipFile(self.fd, "w", compression=compression)

    def add_file(self, included_file: IncludedFile) -> None:
        zinfo = ZipInfo.from_file(included_file.path, included_file.distribution_path)
        if zinfo.is_dir():
            msg = "ZipArchive.add_file does not support adding directories"
            raise ValueError(msg)

        if self.reproducible:
            zinfo.date_time = self._reproducible_date_time
            # normalize mode (https://github.com/takluyver/flit/pull/66)
            st_mode = (zinfo.external_attr >> 16) & 0xFFFF
            set_zip_info_mode(zinfo, normalize_file_permissions(st_mode) & 0xFFFF)

        with open(included_file.path, "rb") as src, self.zf.open(zinfo, "w") as dest:
            # https://github.com/python/mypy/issues/15031
            shutil.copyfileobj(src, dest, 8 * 1024)  # type: ignore[misc]

    def write_file(self, path: str, data: bytes | str) -> None:
        arcname = path
        date_time = self._reproducible_date_time if self.reproducible else time.localtime(time.time())[:6]
        self.zf.writestr(ZipInfo(os.fspath(arcname), date_time=date_time), data)

    def write_dunder_main(self, module: str, function: str) -> None:
        _dunder_main = "\n".join(
            (
                "# -*- coding: utf-8 -*-",
                f"import {module}",
                f"{module}.{function}()",
            )
        )
        self.write_file("__main__.py", _dunder_main)

    def add_dependencies(self, dependencies: Sequence[str]) -> None:
        if not dependencies:
            return
        with tempfile.TemporaryDirectory() as tmpdir:
            pip_command = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-input",
                "--disable-pip-version-check",
                "--no-color",
                "--target",
                tmpdir,
            ]
            subprocess.check_call(pip_command + list(dependencies))

            for root, dirs, files in Path(tmpdir).walk():
                dirs[:] = sorted(d for d in dirs if d != "__pycache__")
                files.sort()
                for file in files:
                    included_file = IncludedFile(str(root / file), "", str(root.relative_to(tmpdir) / file))
                    self.add_file(included_file)

    @cached_property
    def _reproducible_date_time(self):
        return time.gmtime(get_reproducible_timestamp())[0:6]

    def close(self):
        self.zf.close()
        self.fd.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class PythonZipappBuilder(BuilderInterface):
    PLUGIN_NAME = "pyz"

    config: PyzConfig

    @classmethod
    def get_config_class(cls) -> type[BuilderConfig]:
        return PyzConfig

    def get_version_api(self) -> dict[str, Callable[..., str]]:
        return {"standard": self.build_standard}

    def clean(self, directory: str, versions: Iterable[str]) -> None:  # noqa: ARG002
        for filename in os.listdir(directory):
            if filename.endswith(".pyz"):
                os.remove(os.path.join(directory, filename))

    def build_standard(self, directory: str, **build_data: dict[str, Any]) -> str:  # noqa: ARG002
        project_name = self.normalize_file_name_component(self.metadata.core.raw_name)
        target = Path(directory, f"{project_name}-{self.metadata.version}.pyz")

        module, function = self.config.main.split(":")

        with ZipappArchive(
                reproducible=self.config.reproducible,
                compressed=self.config.compressed,
                interpreter=self.config.interpreter,
        ) as pyzapp:
            pyzapp.write_dunder_main(module, function)
            if self.config.bundle_depenencies:
                pyzapp.add_dependencies(self.metadata.core.dependencies)
            for included_file in self.recurse_included_files():
                pyzapp.add_file(included_file)

        replace_file(pyzapp.path, str(target))
        normalize_artifact_permissions(str(target))

        return os.fspath(target)
