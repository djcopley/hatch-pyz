from hatchling.plugin import hookimpl

from hatch_pyz.plugin import PythonZipappBuilder


@hookimpl
def hatch_register_builder():
    return PythonZipappBuilder
