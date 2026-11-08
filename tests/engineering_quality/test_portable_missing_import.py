"""The portable build must reject unresolved explicit internal imports."""
import unittest

from tools.nana_portable_cloud.build import verify_runtime_closure


class PortableMissingImportTest(unittest.TestCase):
    def test_explicit_module_must_exist_and_be_selected(self):
        caller = "src/nana_core/test_only.py"
        dependency = "src/nana_core/example.py"
        assets = [
            "src/nana_core/continuity/hands/server.py",
            "src/nana_core/continuity/hands/browser.py",
            "src/nana_core/continuity/open_agency/skill_runner.py",
        ]
        selected = [caller, *assets]
        sources = {name: "" for name in [*selected, dependency]}
        sources[caller] = "import nana_core.example\n"
        with self.assertRaisesRegex(ValueError, "RUNTIME_IMPORT_MISSING"):
            verify_runtime_closure(selected, selected, sources.__getitem__)
        with self.assertRaisesRegex(ValueError, "RUNTIME_IMPORT_MISSING"):
            verify_runtime_closure(selected, [*selected, dependency], sources.__getitem__)
        verify_runtime_closure([*selected, dependency], [*selected, dependency], sources.__getitem__)

    def test_namespace_package_and_from_attribute_remain_valid(self):
        caller = "src/nana_core/test_only.py"
        namespace_child = "src/nana_core/example/child.py"
        assets = [
            "src/nana_core/continuity/hands/server.py",
            "src/nana_core/continuity/hands/browser.py",
            "src/nana_core/continuity/open_agency/skill_runner.py",
        ]
        names = [caller, namespace_child, *assets]
        sources = {name: "" for name in names}
        sources[caller] = "import nana_core.example\nfrom nana_core.example.child import attribute\n"
        verify_runtime_closure(names, names, sources.__getitem__)
        with self.assertRaisesRegex(ValueError, "RUNTIME_IMPORT_MISSING"):
            verify_runtime_closure([caller, *assets], names, sources.__getitem__)


if __name__ == "__main__":
    unittest.main()
