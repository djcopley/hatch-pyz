from __future__ import annotations

import io
import os
import shutil
import time
import zipapp
from contextlib import contextmanager
from functools import cached_property
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Iterator
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED, ZIP_STORED

from hatchling.builders.config import BuilderConfig
from hatchling.builders.plugin.interface import BuilderInterface
from hatchling.builders.plugin.interface import IncludedFile
from hatchling.builders.utils import get_reproducible_timestamp
from hatchling.builders.utils import normalize_file_permissions
from hatchling.builders.utils import set_zip_info_mode

from .config import PyzConfig
from .utils import atomic_write


class ZipappArchive:
    def __init__(self, zipfd: ZipFile, *, reproducible: bool = True):
        self.zipfd = zipfd
        self.reproducible = reproducible

    def add_file(self, included_file: IncludedFile) -> None:
        # Logic mostly copied from hatchling.builders.wheel.WheelArchive.add_file
        # https://github.com/pypa/hatch/blob/7dac9856d2545393f7dd96d31fc8620dde0dc12d/backend/src/hatchling/builders/wheel.py#L84-L112
        zinfo = ZipInfo.from_file(included_file.path, included_file.distribution_path)
        if zinfo.is_dir():
            raise ValueError(
                "ZipArchive.add_file does not support adding directories"
            )

        if self.reproducible:
            zinfo.date_time = self._reproducible_date_time
            # normalize mode (https://github.com/takluyver/flit/pull/66)
            st_mode = (zinfo.external_attr >> 16) & 0xFFFF
            set_zip_info_mode(zinfo, normalize_file_permissions(st_mode) & 0xFFFF)

        with open(included_file.path, "rb") as src, self.zipfd.open(zinfo, "w") as dest:
            shutil.copyfileobj(src, dest, 8 * 1024)

    def write_file(self, path: str, data: bytes | str) -> None:
        arcname = path
        if self.reproducible:
            date_time = self._reproducible_date_time
        else:
            date_time = time.localtime(time.time())[:6]
        self.zipfd.writestr(ZipInfo(os.fspath(arcname), date_time=date_time), data)

    @cached_property
    def _reproducible_date_time(self):
        return time.gmtime(get_reproducible_timestamp())[0:6]

    @classmethod
    @contextmanager
    def open(cls, dst: str | os.PathLike[str], *, reproducible: bool, compressed: bool) -> Iterator[ZipArchive]:
        with atomic_write(dst) as fp:
            compression = ZIP_DEFLATED if compressed else ZIP_STORED
            with ZipFile(fp, "w", compression=compression) as zipfd:
                yield cls(zipfd, reproducible=reproducible)


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
        self.app.display_debug(f"Directory: {directory}")
        self.app.display_debug(f"Build Data: {build_data}")
        self.app.display_debug(f"Target Config: {self.target_config}")
        self.app.display_debug(f"Config: {self.config}")

        project_name = self.normalize_file_name_component(self.metadata.core.raw_name)
        target = Path(directory, f"{project_name}-{self.metadata.version}.pyz")

        module, function = self.config.main.split(":")
        dunder_main = ("# -*- coding: utf-8 -*-\n"
                       f"import {module}\n"
                       f"{module}.{function}()")

        with ZipappArchive.open(
                target, reproducible=self.config.reproducible, compressed=self.config.compressed
        ) as archive:
            archive.write_file("__main__.py", dunder_main)
            for included_file in self.recurse_included_files():
                self.app.display_debug(f"Included File: {included_file.path}, {included_file.relative_path}, "
                                       f"{included_file.distribution_path}")
                archive.add_file(included_file)

        temp = io.BytesIO()
        zipapp.create_archive(target, temp, self.config.interpreter)

        with open(target, "wb") as dest:
            dest.write(temp.getvalue())

        return os.fspath(target)
