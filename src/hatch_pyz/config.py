from __future__ import annotations

import os
import re
import sys
from functools import cached_property
from typing import NamedTuple

from hatchling.builders.config import BuilderConfig


class FileSelectionOptions(NamedTuple):
    include: list[str]
    exclude: list[str]
    packages: list[str]
    only_include: list[str]


class PyzConfig(BuilderConfig):
    @cached_property
    def default_file_selection_options(self) -> FileSelectionOptions:
        include = self.target_config.get("include", self.build_config.get("include", []))
        exclude = self.target_config.get("exclude", self.build_config.get("exclude", []))
        packages = self.target_config.get("packages", self.build_config.get("packages", []))
        only_include = self.target_config.get("only-include", self.build_config.get("only-include", []))

        if include or packages or only_include:
            return FileSelectionOptions(include, exclude, packages, only_include)

        project_names: set[str] = set()
        for project_name in (
            self.builder.normalize_file_name_component(self.builder.metadata.core.raw_name),
            self.builder.normalize_file_name_component(self.builder.metadata.core.name),
        ):
            if os.path.isfile(os.path.join(self.root, project_name, "__init__.py")):
                normalized_project_name = self.get_raw_fs_path_name(self.root, project_name)
                return FileSelectionOptions([], exclude, [normalized_project_name], [])

            if os.path.isfile(os.path.join(self.root, "src", project_name, "__init__.py")):
                normalized_project_name = self.get_raw_fs_path_name(os.path.join(self.root, "src"), project_name)
                return FileSelectionOptions([], exclude, [f"src/{normalized_project_name}"], [])

            module_file = f"{project_name}.py"
            if os.path.isfile(os.path.join(self.root, module_file)):
                return FileSelectionOptions([], exclude, [], [module_file])

            from glob import glob

            possible_namespace_packages = glob(os.path.join(self.root, "*", project_name, "__init__.py"))
            if len(possible_namespace_packages) == 1:
                relative_path = os.path.relpath(possible_namespace_packages[0], self.root)
                namespace = relative_path.split(os.sep)[0]
                return FileSelectionOptions([], exclude, [namespace], [])
            project_names.add(project_name)

        project_names_text = " or ".join(sorted(project_names))
        message = (
            f"Unable to determine which files to ship inside the wheel using the following heuristics: "
            f"https://hatch.pypa.io/latest/plugins/builder/wheel/#default-file-selection\n\n"
            f"The most likely cause of this is that there is no directory that matches the name of your "
            f"project ({project_names_text}).\n\n"
            f"At least one file selection option must be defined in the `tool.hatch.build.targets.pyz` "
            f"table, see: https://hatch.pypa.io/latest/config/build/\n\n"
            f"As an example, if you intend to ship a directory named `foo` that resides within a `src` "
            f"directory located at the root of your project, you can define the following:\n\n"
            f"[tool.hatch.build.targets.pyz]\n"
            f'packages = ["src/foo"]'
        )
        raise ValueError(message)

    def default_include(self) -> list[str]:
        return self.default_file_selection_options.include

    def default_exclude(self) -> list[str]:
        return self.default_file_selection_options.exclude

    def default_packages(self) -> list[str]:
        return self.default_file_selection_options.packages

    def default_only_include(self) -> list[str]:
        return self.default_file_selection_options.only_include

    @cached_property
    def interpreter(self) -> str:
        if "interpreter" in self.target_config:
            interpreter = self.target_config["interpreter"]
            if not isinstance(interpreter, str):
                message = f"Field `tool.hatch.build.targets.{self.plugin_name}.interpreter` must be a string"
                raise TypeError(message)
        else:
            interpreter = self.build_config.get("interpreter", "/usr/bin/env python3")
            if not isinstance(interpreter, str):
                message = "Field `tool.hatch.build.interpreter` must be a string"
                raise TypeError(message)

        return interpreter

    @cached_property
    def main(self) -> str:
        pattern = re.compile(r"^(([a-zA-Z0-9_]+)\.?)+:([a-zA-Z0-9_]+)$")
        if "main" in self.target_config:
            main = self.target_config["main"]
            if not isinstance(main, str) or not pattern.match(main):
                message = (
                    f"Field `tool.hatch.build.targets.{self.plugin_name}.main` must be a string "
                    f"and take the form `pkg.module:callable`"
                )
                raise TypeError(message)
        else:
            main = self.build_config.get("main", None)
            if main is None or not isinstance(main, str) or not pattern.match(main):
                message = "Field `tool.hatch.build.main` must be a string " "and take the form `pkg.module:callable`"
                raise TypeError(message)

        return main

    @cached_property
    def compressed(self) -> bool:
        if "compressed" in self.target_config:
            compressed = self.target_config["compressed"]
            if not isinstance(compressed, bool):
                message = f"Field `tool.hatch.build.targets.{self.plugin_name}.compressed` must be a boolean"
                raise TypeError(message)
        else:
            compressed = self.build_config.get("compressed", True)
            if not isinstance(compressed, bool):
                message = "Field `tool.hatch.build.compressed` must be a boolean"
                raise TypeError(message)

        return compressed

    @cached_property
    def bundle_depenencies(self) -> bool:
        if "bundle-dependencies" in self.target_config:
            bundle_depenencies = self.target_config["bundle-dependencies"]
            if not isinstance(bundle_depenencies, bool):
                message = "Field `tool.hatch.build.bundle-depenencies` must be a boolean"
                raise TypeError(message)
        else:
            bundle_depenencies = self.build_config.get("bundle-depenencies", True)
            if not isinstance(bundle_depenencies, bool):
                message = "Field `tool.hatch.build.bundle-depenencies` must be a boolean"
                raise TypeError(message)

        return bundle_depenencies

    if sys.platform in {"darwin", "win32"}:

        @staticmethod
        def get_raw_fs_path_name(directory: str, name: str) -> str:
            normalized = name.casefold()
            entries = os.listdir(directory)
            for entry in entries:
                if entry.casefold() == normalized:
                    return entry

            return name

    else:

        @staticmethod
        def get_raw_fs_path_name(directory: str, name: str) -> str:  # noqa: ARG004
            return name
