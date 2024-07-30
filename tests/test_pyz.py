from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from tests.conftest import make_files

if TYPE_CHECKING:
    from hatch_pyz.plugin import PythonZipappBuilder


def md5_file_digest(path: str | Path) -> bytes:
    hasher = hashlib.md5()
    hasher.update(Path(path).read_bytes())
    return hasher.digest()


def test_clean(pyz_builder_factory):
    builder: PythonZipappBuilder = pyz_builder_factory()
    build_dir = Path(builder.config.directory)
    build_dir.mkdir()

    other_artifact = build_dir / "my-app.tar.gz"
    other_artifact.touch()
    zip_app = build_dir / "my-app.pyz"
    zip_app.touch()

    builder.clean(str(build_dir), ["standard"])

    assert other_artifact.exists()
    assert not zip_app.exists()


def test_build_standard(pyz_builder_factory):
    builder: PythonZipappBuilder = pyz_builder_factory()
    build_dir = Path(builder.config.directory)
    build_dir.mkdir()

    builder.build_standard(str(build_dir))

    artifact_path = next(build_dir.iterdir())
    assert artifact_path.name == "my_app-0.0.1.pyz"
    assert artifact_path.read_bytes().startswith(b"#!/usr/bin/env python")
    with zipfile.ZipFile(artifact_path, "r") as zf:
        assert set(zf.namelist()) == {
            "__main__.py",
            "my_app/__init__.py",
            "my_app/app.py",
            "my_app/logger.py",
        }
        assert zf.read("__main__.py") == b"# -*- coding: utf-8 -*-\nimport my_app.app\nmy_app.app.main()"


def test_build_standard_reproducible(pyz_builder_factory):
    builder: PythonZipappBuilder = pyz_builder_factory()
    build_dir = Path(builder.config.directory)
    build_dir.mkdir()

    artifact_path = builder.build_standard(str(builder.config.directory))
    hash1 = md5_file_digest(artifact_path)
    builder.clean(str(builder.config.directory), ["standard"])
    artifact_path = builder.build_standard(str(builder.config.directory))
    hash2 = md5_file_digest(artifact_path)

    assert hash1 == hash2


@pytest.mark.parametrize("compressed,compression_type", [(False, zipfile.ZIP_STORED), (True, zipfile.ZIP_DEFLATED)])
def test_build_standard_compressed(compressed, compression_type, pyz_builder_factory):
    builder: PythonZipappBuilder = pyz_builder_factory(
        compressed=compressed,
    )
    build_dir = Path(builder.config.directory)
    build_dir.mkdir()

    artifact_path = builder.build_standard(str(build_dir))
    with zipfile.ZipFile(artifact_path, 'r') as zf:
        for info in zf.infolist():
            assert info.compress_type == compression_type


def test_build_standard_bundled_dependencies(pyz_builder_factory):
    dependencies = ["flask", "jinja2", "flask-socketio"]
    builder: PythonZipappBuilder = pyz_builder_factory(dependencies=dependencies)
    build_dir = Path(builder.config.directory)
    build_dir.mkdir()

    with patch("hatch_pyz.plugin.pip_install") as mock_pip_install:
        mock_pip_install.side_effect = lambda dependencies, target_dir: make_files(Path(target_dir), dependencies)
        artifact_path = builder.build_standard(str(build_dir))

    with zipfile.ZipFile(artifact_path, "r") as zf:
        assert set(zf.namelist()) == {
            "__main__.py",
            "my_app/__init__.py",
            "my_app/app.py",
            "my_app/logger.py",
            "flask",
            "flask-socketio",
            "jinja2",
        }
