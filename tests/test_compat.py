import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def load_compat_module():
    module_path = Path(__file__).resolve().parents[1] / "denario" / "_compat.py"
    spec = importlib.util.spec_from_file_location("denario_compat", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CompatTests(unittest.TestCase):
    def test_patch_mistralai_for_cmbagent_adds_legacy_top_level_symbols(self):
        compat = load_compat_module()
        fake_mistralai = SimpleNamespace()
        fake_sdk = SimpleNamespace(Mistral=object())
        fake_document = SimpleNamespace(DocumentURLChunk=object())

        modules = {
            "mistralai": fake_mistralai,
            "mistralai.client.sdk": fake_sdk,
            "mistralai.client.models.documenturlchunk": fake_document,
        }

        def fake_import_module(name):
            return modules[name]

        with patch.object(compat.importlib, "import_module", side_effect=fake_import_module):
            compat.patch_mistralai_for_cmbagent()

        self.assertIs(fake_mistralai.Mistral, fake_sdk.Mistral)
        self.assertIs(fake_mistralai.DocumentURLChunk, fake_document.DocumentURLChunk)


if __name__ == "__main__":
    unittest.main()
