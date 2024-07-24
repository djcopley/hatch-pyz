from hatchling.plugin import hookimpl

from .plugin import PythonZipappBuilder


@hookimpl
def hatch_register_builder():
    return PythonZipappBuilder
