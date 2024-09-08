from hatchling.plugin import hookimpl

from hatch_pyz.builder import PythonZipappBuilder


@hookimpl
def hatch_register_builder():
    return PythonZipappBuilder
