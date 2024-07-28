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
from typing import Any, Callable, Iterable
from zipfile import ZipFile, ZipInfo

from hatchling.builders.config import BuilderConfig
from hatchling.builders.plugin.interface import BuilderInterface, IncludedFile
from hatchling.builders.utils import (
    get_reproducible_timestamp, normalize_file_permissions, normalize_artifact_permissions, set_zip_info_mode,
    replace_file
)

from .config import PyzConfig


class ZipappArchive:
    if sys.platform.startswith('win'):
        shebang_encoding = 'utf-8'
    else:
        shebang_encoding = sys.getfilesystemencoding()

    def __init__(self, *, reproducible: bool, compressed: bool, interpreter: str):
        self.reproducible = reproducible

        raw_fd, self.path = tempfile.mkstemp(suffix='.pyz')
        self.fd = os.fdopen(raw_fd, 'w+b')

        shebang = b'#!' + interpreter.encode(self.shebang_encoding) + b'\n'
        self.fd.write(shebang)

        compression = zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED
        self.zf = ZipFile(self.fd, "w", compression=compression)

    def add_file(self, included_file: IncludedFile) -> None:
        zinfo = ZipInfo.from_file(included_file.path, included_file.distribution_path)
        if zinfo.is_dir():
            raise ValueError("ZipArchive.add_file does not support adding directories")

        if self.reproducible:
            zinfo.date_time = self._reproducible_date_time
            # normalize mode (https://github.com/takluyver/flit/pull/66)
            st_mode = (zinfo.external_attr >> 16) & 0xFFFF
            set_zip_info_mode(zinfo, normalize_file_permissions(st_mode) & 0xFFFF)

        with open(included_file.path, "rb") as src, self.zf.open(zinfo, "w") as dest:
            shutil.copyfileobj(src, dest, 8 * 1024)

    def write_file(self, path: str, data: bytes | str) -> None:
        arcname = path
        if self.reproducible:
            date_time = self._reproducible_date_time
        else:
            date_time = time.localtime(time.time())[:6]
        self.zf.writestr(ZipInfo(os.fspath(arcname), date_time=date_time), data)

    def write_dunder_main(self, module: str, function: str) -> None:
        _dunder_main = "\n".join((
            "# -*- coding: utf-8 -*-",
            f"import {module}",
            f"{module}.{function}()",
        ))
        self.write_file("__main__.py", _dunder_main)

    def add_dependencies(self, dependencies: Iterable[str]) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pip_command = [
                sys.executable, "-m", "pip", "install",
                "--no-input",
                "--disable-pip-version-check",
                "--no-color",
                "--target", tmpdir
            ]
            subprocess.check_call(pip_command + list(dependencies))

            for file in Path(tmpdir).rglob("*"):
                if not file.is_file():
                    continue
                included_file = IncludedFile(file, "", str(file.relative_to(tmpdir)))
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

    def clean(self, directory: str, versions: Iterable[str]) -> None:
        for filename in os.listdir(directory):
            if filename.endswith(".pyz"):
                os.remove(os.path.join(directory, filename))

    def build_standard(self, directory: str, **build_data: Any) -> str:
        project_name = self.normalize_file_name_component(self.metadata.core.raw_name)
        target = Path(directory, f"{project_name}-{self.metadata.version}.pyz")

        module, function = self.config.main.split(":")

        with ZipappArchive(reproducible=self.config.reproducible, compressed=self.config.compressed,
                           interpreter=self.config.interpreter) as pyzapp:
            pyzapp.write_dunder_main(module, function)
            if self.config.bundle_depenencies:
                pyzapp.add_dependencies(self.metadata.core.dependencies)
            for included_file in self.recurse_included_files():
                pyzapp.add_file(included_file)

        replace_file(pyzapp.path, str(target))
        normalize_artifact_permissions(str(target))

        return os.fspath(target)
