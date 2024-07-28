from __future__ import annotations

import re
from functools import cached_property

from hatchling.builders.config import BuilderConfig


class PyzConfig(BuilderConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @cached_property
    def interpreter(self) -> str:
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

        return interpreter

    @cached_property
    def main(self) -> str:
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

        return main

    @cached_property
    def compressed(self) -> bool:
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

        return compressed
    
    @cached_property
    def bundle_depenencies(self) -> bool:
        if 'bundle-depenencies' in self.target_config:
            bundle_depenencies = self.target_config['bundle-depenencies']
            if not isinstance(bundle_depenencies, bool):
                message = f'Field `tool.hatch.build.bundle-depenencies` must be a boolean'
                raise TypeError(message)
        else:
            bundle_depenencies = self.build_config.get('bundle-depenencies', True)
            if not isinstance(bundle_depenencies, bool):
                message = f'Field `tool.hatch.build.bundle-depenencies` must be a boolean'
                raise TypeError(message)

        return bundle_depenencies
