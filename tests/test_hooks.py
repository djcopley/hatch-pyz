from hatch_pyz.hooks import hatch_register_builder
from hatch_pyz.plugin import PythonZipappBuilder


def test_hooks():
    assert hatch_register_builder() == PythonZipappBuilder
