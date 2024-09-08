from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

import pytest
import tomli_w

from hatch_pyz.plugin import PythonZipappBuilder

if TYPE_CHECKING:
    from pathlib import Path


def make_files(root: Path, files: list[str]) -> None:
    for file in files:
        path = root / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()


@pytest.fixture
def pyz_builder_factory(tmp_path) -> Callable:
    default_config: dict[str, Any] = {
        "project": {
            "name": "my-app",
            "version": "0.0.1",
        },
        "tool": {"hatch": {"build": {"targets": {"pyz": {"main": "my_app.app:main"}}}}},
    }

    def _make_project(
        config: dict | None = None,
        dependencies: list | None = None,
        optional_dependencies: dict | None = None,
        force_include: dict | None = None,
        files: list[str] | None = None,
        **build_conf: dict,
    ) -> PythonZipappBuilder:
        if not config:
            config = default_config
        if dependencies:
            config["project"]["dependencies"] = dependencies
        if optional_dependencies:
            config["project"]["optional-dependencies"] = optional_dependencies

        if build_conf:
            config["tool"]["hatch"]["build"]["targets"]["pyz"].update(build_conf)
        if force_include:
            config["tool"]["hatch"]["build"]["force-include"] = force_include

        builder = PythonZipappBuilder(str(tmp_path), config=config)

        pyproject = tmp_path / "pyproject.toml"
        with open(pyproject, mode="wb") as file:
            tomli_w.dump(config, file)

        if not files:
            files = [
                "README.md",
                "docs/guide1.rst",
                "docs/guide2.rst",
                "src/my_app/__init__.py",
                "src/my_app/app.py",
                "src/my_app/logger.py",
                "tests/test_app.py",
                "scripts/something.sh",
            ]

        make_files(root=tmp_path, files=files)

        return builder

    return _make_project
