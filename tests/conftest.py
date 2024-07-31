import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest


@pytest.fixture(scope='session')
def plugin_dir():
    with TemporaryDirectory() as d:
        directory = Path(d, 'plugin')
        shutil.copytree(
            Path.cwd(), directory, ignore=shutil.ignore_patterns('.git')
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
requires = ["hatchling", "hatch-plugin-name @ {plugin_dir.as_uri()}"]
build-backend = "hatchling.build"

[project]
name = "my-app"
version = "0.1.0"
""",
        encoding='utf-8',
    )
