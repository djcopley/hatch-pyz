from hatch_pyz.builder import PythonZipappBuilder
from hatch_pyz.hooks import hatch_register_builder


def test_hooks():
    assert hatch_register_builder() == PythonZipappBuilder
