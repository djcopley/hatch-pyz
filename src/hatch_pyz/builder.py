from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterable, TypeAlias
from zipfile import ZipFile, ZipInfo

from hatchling.builders.plugin.interface import BuilderInterface, IncludedFile
from hatchling.builders.utils import (
    get_reproducible_timestamp,
    normalize_archive_path,
    normalize_artifact_permissions,
    normalize_file_permissions,
    replace_file,
    set_zip_info_mode,
)

from hatch_pyz.config import PyzConfig

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from hatchling.builders.config import BuilderConfig

TIME_TUPLE: TypeAlias = tuple[int, int, int, int, int, int]


def pip_install(dependencies: Sequence[str], target_directory: str) -> None:
    pip_command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--no-input",
        "--disable-pip-version-check",
        "--no-color",
        "--target",
        target_directory,
    ]
    subprocess.check_call(pip_command + list(dependencies))


class ZipappArchive:
    if sys.platform.startswith("win"):
        shebang_encoding = "utf-8"
    else:
        shebang_encoding = sys.getfilesystemencoding()

    def __init__(self, *, reproducible: bool, compressed: bool, interpreter: str):
        self.reproducible = reproducible
        self.compression = zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED

        raw_fd, self.path = tempfile.mkstemp(suffix=".pyz")
        self.fd = os.fdopen(raw_fd, "w+b")

        shebang = b"#!" + interpreter.encode(self.shebang_encoding) + b"\n"
        self.fd.write(shebang)

        self.zf = ZipFile(self.fd, "w", compression=self.compression)

    @staticmethod
    def get_reproducible_time_tuple() -> TIME_TUPLE:
        from datetime import datetime, timezone

        d = datetime.fromtimestamp(get_reproducible_timestamp(), timezone.utc)
        return d.year, d.month, d.day, d.hour, d.minute, d.second

    def add_file(self, included_file: IncludedFile) -> None:
        relative_path = normalize_archive_path(included_file.distribution_path)
        file_stat = os.stat(included_file.path)

        if self.reproducible:
            zip_info = zipfile.ZipInfo(relative_path, self.get_reproducible_time_tuple())

            # https://github.com/takluyver/flit/pull/66
            new_mode = normalize_file_permissions(file_stat.st_mode)
            set_zip_info_mode(zip_info, new_mode)
            if stat.S_ISDIR(file_stat.st_mode):
                zip_info.external_attr |= 0x10
        else:
            zip_info = zipfile.ZipInfo.from_file(included_file.path, relative_path)

        zip_info.compress_type = self.compression

        with open(included_file.path, "rb") as in_file, self.zf.open(zip_info, "w") as out_file:
            while True:
                chunk = in_file.read(16384)
                if not chunk:
                    break
                out_file.write(chunk)

    def write_file(self, path: str, data: bytes | str) -> None:
        arcname = path
        date_time = self.get_reproducible_time_tuple() if self.reproducible else time.localtime(time.time())[:6]
        zinfo = ZipInfo(os.fspath(arcname), date_time=date_time)
        self.zf.writestr(zinfo, data, compress_type=self.compression)

    def write_dunder_main(self, module: str, function: str) -> None:
        _dunder_main = "\n".join(
            (
                "# -*- coding: utf-8 -*-",
                f"import {module}",
                f"{module}.{function}()",
            )
        )
        self.write_file("__main__.py", _dunder_main)

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

    @contextmanager
    def bundle_dependencies(self, dependencies: Sequence[str]) -> Iterator[None]:
        if not dependencies:
            yield
            return

        with tempfile.TemporaryDirectory() as target_directory:
            pip_install(dependencies, target_directory)

            for root, dirs, files in Path(target_directory).walk():
                dirs[:] = sorted(d for d in dirs if d != "__pycache__")
                files.sort()
                for file in files:
                    self.config.force_include[str(root / file)] = str(root.relative_to(target_directory) / file)

            yield

    def build_standard(self, directory: str, **build_data: dict[str, Any]) -> str:  # noqa: ARG002
        project_name = self.normalize_file_name_component(self.metadata.core.raw_name)
        target = Path(directory, f"{project_name}-{self.metadata.version}.pyz")

        module, function = self.config.main.split(":")
        bundled_dependencies = (
            self.bundle_dependencies(self.metadata.core.dependencies)
            if self.config.bundle_depenencies
            else nullcontext()
        )

        with ZipappArchive(
            reproducible=self.config.reproducible,
            compressed=self.config.compressed,
            interpreter=self.config.interpreter,
        ) as pyzapp, bundled_dependencies:
            pyzapp.write_dunder_main(module, function)
            for included_file in self.recurse_included_files():
                pyzapp.add_file(included_file)

        replace_file(pyzapp.path, str(target))
        normalize_artifact_permissions(str(target))

        return os.fspath(target)
