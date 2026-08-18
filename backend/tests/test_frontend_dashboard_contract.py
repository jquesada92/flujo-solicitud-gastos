import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class FrontendDashboardContractTests(unittest.TestCase):
    def test_pending_rows_open_contextual_modal_instead_of_generic_request_list(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'home-dashboard.jsx').read_text(encoding='utf-8')
        self.assertIn('onClick={() => openAction(item)}', source)
        self.assertIn('/my-actions`', source)
        self.assertIn('PendingActionModal', source)
        self.assertIn('role="dialog"', source)
        self.assertIn('ACCIÓN PENDIENTE', source)

    def test_modal_supports_all_current_user_action_types(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'home-dashboard.jsx').read_text(encoding='utf-8')
        for code in (
            'APPROVAL_DECISION',
            'QUOTATION_VOTE',
            'CLOSE_REQUEST',
            'CORRECT_REQUEST',
        ):
            self.assertIn(code, source)
        self.assertIn('/approval-decision`', source)
        self.assertIn('/quotation-vote`', source)
        self.assertIn('/close`', source)
        self.assertIn('REVISION_REQUESTED', source)
        self.assertIn('Votar por esta opción', source)
        self.assertIn('Subir factura y cerrar', source)

    def test_dashboard_revalidates_actions_after_each_mutation(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'home-dashboard.jsx').read_text(encoding='utf-8')
        self.assertIn('Promise.all([loadDashboard(), loadDetail(selected.request_id)])', source)
        self.assertIn('Ya no tienes acciones pendientes para esta solicitud.', source)

    def test_top_kpis_are_informational_not_buttons(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'home-dashboard.jsx').read_text(encoding='utf-8')
        self.assertIn('<article className="dashboard-kpi attention">', source)
        self.assertIn('<article className="dashboard-kpi">', source)
        self.assertIn('<article className="dashboard-kpi success">', source)
        self.assertNotIn('<button className="dashboard-kpi attention"', source)
        self.assertNotIn('<button className="dashboard-kpi" onClick={onOpenRequests}', source)

    def test_vite_extracts_legacy_components_and_uses_resource_capabilities(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('import HomeDashboard from "./home-dashboard.jsx";', vite)
        self.assertIn('function HomeDashboard({', vite)
        self.assertIn('function App()', vite)
        self.assertIn('could not isolate HomeDashboard', vite)
        self.assertIn('x.can_cancel', vite)
        self.assertIn('x.can_correct', vite)
        self.assertIn('canCreate || revision', vite)
        self.assertIn('Enviar a revisión', vite)


if __name__ == '__main__':
    unittest.main()
