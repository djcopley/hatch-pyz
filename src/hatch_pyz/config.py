from __future__ import annotations

import re

from hatchling.builders.config import BuilderConfig


class PyzConfig(BuilderConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__interpreter: str | None = None
        self.__main: str | None = None
        self.__compressed: bool = False

    def __str__(self):
        return f"{self.interpreter}, {self.main}, {self.compressed}"

    def __repr__(self):
        return str(self)

    @property
    def interpreter(self) -> str | None:
        if not self.__interpreter:
            if 'interpreter' in self.target_config:
                interpreter = self.target_config['interpreter']
                if not isinstance(interpreter, str):
                    message = f'Field `tool.hatch.build.targets.{self.plugin_name}.interpreter` must be a string'
                    raise TypeError(message)
            else:
                interpreter = self.build_config.get('interpreter', '/usr/bin/env python3')
                if not isinstance(interpreter, str):
                    message = 'Field `tool.hatch.build.interpreter` must be a string'
                    raise TypeError(message)
            self.__interpreter = interpreter

        return self.__interpreter

    @property
    def main(self) -> str | None:
        if not self.__main:
            pattern = re.compile(r"^(([a-zA-Z0-9_]+)\.?)+:([a-zA-Z0-9_]+)$")
            if 'main' in self.target_config:
                main = self.target_config['main']
                if not isinstance(main, str) or not pattern.match(main):
                    message = (f'Field `tool.hatch.build.targets.{self.plugin_name}.main` must be a string '
                               f'and take the form `pkg.module:callable`')
                    raise TypeError(message)
            else:
                main = self.build_config.get('main', None)
                if main is None or not isinstance(main, str) or not pattern.match(main):
                    message = ('Field `tool.hatch.build.main` must be a string '
                               'and take the form `pkg.module:callable`')
                    raise TypeError(message)
            self.__main = main

        return self.__main

    @property
    def compressed(self) -> bool:
        if not self.__compressed:
            if 'compressed' in self.target_config:
                compressed = self.target_config['compressed']
                if not isinstance(compressed, bool):
                    message = f'Field `tool.hatch.build.targets.{self.plugin_name}.compressed` must be a boolean'
                    raise TypeError(message)
            else:
                compressed = self.build_config.get('compressed', True)
                if not isinstance(compressed, bool):
                    message = 'Field `tool.hatch.build.compressed` must be a boolean'
                    raise TypeError(message)

        return self.__compressed
