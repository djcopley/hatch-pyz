from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest


@pytest.fixture(scope='session')
def plugin_dir():
    with TemporaryDirectory() as d:
        directory = Path(d, 'plugin')
        shutil.copytree(
            Path.cwd(), directory
        )

        yield directory.resolve()


@pytest.fixture
def new_project(tmp_path, plugin_dir):
    project_dir = tmp_path / 'my-app'
    project_dir.mkdir()

    project_file = project_dir / 'pyproject.toml'
    project_file.write_text(
        f"""\
[build-system]
requires = ["hatchling", "hatch-pyz @ {plugin_dir.as_uri()}"]
build-backend = "hatchling.build"

[project]
name = "my-app"
version = "0.1.0"

[tool.hatch.build.targets.pyz]
main = "my_app.main:main"
""",
        encoding='utf-8',
    )
    app_dir = project_dir / "src" / "my_app"
    app_dir.mkdir(exist_ok=True, parents=True)
    app_init = app_dir / "__init__.py"
    app_init.touch(exist_ok=True)

    return project_dir


@pytest.mark.slow
def test_integration(new_project):
    os.chdir(new_project)
    subprocess.check_call(["hatch", "build", "-t", "pyz"])
