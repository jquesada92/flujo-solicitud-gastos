import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class FrontendClosureContractTests(unittest.TestCase):
    def test_closure_delegation_component_is_modular(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'closure-delegation.jsx').read_text(encoding='utf-8')
        self.assertIn('/closure-delegation`', source)
        self.assertIn('delegate_user_id', source)
        self.assertIn('Revocar delegación', source)
        self.assertIn('Delegar cierre/factura', source)
        self.assertIn('Delegar factura', source)

    def test_closure_delegation_component_supports_multiple_entry_points(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'closure-delegation.jsx').read_text(encoding='utf-8')
        self.assertIn('buttonClassName = "secondary nowrap"', source)
        self.assertIn('overlayClassName = "confirm-overlay"', source)
        self.assertIn('type="button" className={buttonClassName}', source)
        self.assertIn('className={overlayClassName}', source)

    def test_legacy_table_uses_backend_resource_capabilities(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('import ClosureDelegationButton from "./closure-delegation.jsx";', vite)
        self.assertIn('x.can_close', vite)
        self.assertIn('x.can_delegate_close', vite)
        self.assertIn('ClosureDelegationButton expense={x} api={api} onChanged={onChanged}', vite)
        self.assertIn('closed invoice correction guard', vite)
        self.assertIn('approved closure guard', vite)

    def test_global_can_close_is_not_the_built_visibility_rule(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('{x.can_close && x.status === "CLOSED"', vite)
        self.assertIn('{x.can_close && ["APPROVED", "QUOTATION_VOTING"].includes(x.status)', vite)
        self.assertNotIn('canClose || filtered.some((item) => item.can_correct)', vite)

    def test_closure_delegation_bridge_is_whitespace_tolerant(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('source.matchAll(pattern)', vite)
        self.assertIn('closure delegation extraction expected 1 row action anchor', vite)
        self.assertIn('row-actions">\\s*', vite)
        self.assertNotIn(
            '<div className="row-actions">\\n                        {x.can_correct && <button',
            vite,
        )


if __name__ == '__main__':
    unittest.main()
