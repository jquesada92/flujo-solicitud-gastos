import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class FrontendRevisionContractTests(unittest.TestCase):
    def test_correction_uses_effective_request_type_for_render_and_payload(self):
        vite_config = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('const effectiveRequestType = draft ? inferredDraftType : requestType;', vite_config)
        self.assertIn('request_type: effectiveRequestType', vite_config)
        self.assertIn('effectiveRequestType === "MULTI_QUOTE" && <div className="full quote-options-editor">', vite_config)
        self.assertIn('effectiveRequestType === "SIMPLE" && <label>', vite_config)
        self.assertIn('draft?.status === "QUOTATION_VOTING"', vite_config)
        self.assertIn('Tipo de solicitud:', vite_config)

    def test_correction_type_selector_remains_creation_only(self):
        vite_config = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('{!draft && <div className="request-type-tabs" role="tablist">', vite_config)
        self.assertIn('El tipo no cambia durante una corrección.', vite_config)


if __name__ == '__main__':
    unittest.main()
