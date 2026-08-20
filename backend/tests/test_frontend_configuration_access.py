import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class FrontendConfigurationAccessTests(unittest.TestCase):
    def test_vite_bridge_separates_configuration_read_from_manage(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('isSystemAdmin = user.is_system_account === true', vite)
        self.assertIn('permissionCodes = user.permission_codes || []', vite)
        self.assertIn('canReadConfiguration = isSystemAdmin || permissionCodes.includes("config:read")', vite)
        self.assertIn('canManageAreas = isSystemAdmin || permissionCodes.includes("areas:manage")', vite)
        self.assertIn('canConfigure = isSystemAdmin', vite)
        self.assertIn('canAccessOrganization = canReadConfiguration', vite)
        self.assertIn('data-config-access={canReadConfiguration ? "true" : "false"}', vite)
        self.assertIn('data-config-readonly={canReadConfiguration && !isSystemAdmin ? "true" : "false"}', vite)

    def test_area_menu_is_available_to_configuration_viewer_or_area_manager(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('(canReadConfiguration || canManageAreas) && <button onClick={() => navigateTo("categories")}', vite)
        self.assertIn('tab === "categories" && (canReadConfiguration || canManageAreas) ?', vite)

    def test_read_only_configuration_exposes_users_rules_and_audit(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('canReadConfiguration && <button onClick={() => navigateTo("people")}', vite)
        self.assertIn('canReadConfiguration && <button onClick={() => navigateTo("rules")}', vite)
        self.assertIn('tab === "rules" && canReadConfiguration ?', vite)
        self.assertIn('tab === "audit" && canReadConfiguration ?', vite)

    def test_audit_menu_bridge_is_whitespace_and_newline_tolerant(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        function = vite.split('function replaceAuditMenuVisibility(source) {', 1)[1].split(
            '\n}\n\nfunction replaceConfigurationAccess(source) {', 1
        )[0]
        self.assertIn('\\s*', function)
        self.assertIn('source.matchAll(pattern)', function)
        self.assertIn('matches.length !== 1', function)
        self.assertIn('audit menu extraction expected 1 guard', function)
        self.assertNotIn('replaceRequired(', function)

    def test_access_console_is_injected_for_configuration_readers(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('protectAccessMenuInjection', vite)
        self.assertIn('menu.dataset.configAccess !== "true"', vite)
        self.assertIn('existing?.remove()', vite)
        self.assertIn('iam-admin access menu extraction expected 1 injection guard', vite)

    def test_access_menu_bridge_is_whitespace_tolerant_and_fail_fast(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        function = vite.split('function protectAccessMenuInjection(source) {', 1)[1].split(
            '\n}\n\nfunction modularExpenseFormPlugin()', 1
        )[0]
        self.assertIn('\\s*', function)
        self.assertIn('source.matchAll(pattern)', function)
        self.assertIn('matches.length !== 1', function)
        self.assertNotIn('replaceRequired(', function)
        self.assertNotIn('system-only access menu injection', function)

    def test_area_api_uses_dedicated_write_permission_and_configuration_read(self):
        source = (REPO_ROOT / 'backend' / 'app' / 'api' / 'areas.py').read_text(encoding='utf-8')
        self.assertIn("require_permission('areas:manage')", source)
        self.assertIn("has_permission(db, user.id, 'areas:manage')", source)
        self.assertIn("has_permission(db, user.id, 'config:read')", source)
        self.assertNotIn("require_permission('config:manage')", source)

    def test_read_only_ui_blocks_configuration_mutations_and_has_access_viewer(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'config-readonly.js').read_text(encoding='utf-8')
        index = (REPO_ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')
        self.assertIn("state.permissionCodes.has('config:read')", source)
        self.assertIn("!state.permissionCodes.has('config:manage')", source)
        self.assertIn('!SAFE_METHODS.has(method)', source)
        self.assertIn("'Tienes acceso de solo lectura a Configuración.'", source)
        self.assertIn("readJson('/api/iam/users')", source)
        self.assertIn("readJson('/api/iam/positions')", source)
        self.assertIn('/src/config-readonly.js', index)

    def test_iam_checkboxes_have_larger_click_target_and_visible_selected_state(self):
        css = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.css').read_text(encoding='utf-8')
        self.assertIn('.iam-check input{width:20px;height:20px;min-width:20px;', css)
        self.assertIn('accent-color:#172033', css)
        self.assertIn('.iam-check:has(input:checked)', css)
        self.assertIn('.iam-check:focus-within', css)
        self.assertIn('cursor:pointer', css)

    def test_access_console_reuses_standard_navigation_and_integrated_refresh(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        css = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.css').read_text(encoding='utf-8')
        self.assertIn('document.querySelector(".topbar")', source)
        self.assertIn('topbar.addEventListener("click", handleTopbarClick)', source)
        self.assertIn('window.location.hash = ""', source)
        self.assertIn('className="iam-page-nav"', source)
        self.assertIn('className="iam-button iam-refresh"', source)
        self.assertIn('↻ Recargar', source)
        self.assertNotIn('>Volver</button>', source)
        self.assertIn('.iam-overlay{position:fixed;top:72px;right:0;bottom:0;left:0;z-index:10', css)
        self.assertIn('.iam-shell{width:min(1180px,92vw);margin:0 auto;padding:48px 0 72px}', css)
        self.assertIn('.iam-card{min-width:0;background:#fff;border:1px solid #e3e7ee;border-radius:18px;padding:26px;', css)

    def test_access_user_list_cannot_overflow_status_badges(self):
        css = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.css').read_text(encoding='utf-8')
        self.assertIn('grid-template-columns:minmax(330px,360px) minmax(0,1fr)', css)
        self.assertIn('.iam-list-item{display:flex;width:100%;min-width:0;overflow:hidden;', css)
        self.assertIn('.iam-list-main{flex:1 1 auto;min-width:0;overflow:hidden}', css)
        self.assertIn('text-overflow:ellipsis;white-space:nowrap', css)
        self.assertIn('.iam-list-item>span:last-child{flex:0 0 auto}', css)

    def test_role_save_is_disabled_until_there_are_real_changes(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        action_css = (REPO_ROOT / 'frontend' / 'src' / 'action-state.css').read_text(encoding='utf-8')
        index = (REPO_ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('const roleDirty = useMemo(() => {', source)
        self.assertIn('const canPersistRole = roleDirty && form.name.trim().length >= 2;', source)
        self.assertIn('iam-persist-action ${canPersistRole ? "pending" : ""}', source)
        self.assertIn('disabled={!canPersistRole}', source)
        self.assertIn('button.primary:disabled', action_css)
        self.assertIn('.iam-persist-action.pending', action_css)
        self.assertIn('.classification-save-assignment:not(:disabled)', action_css)
        self.assertIn('/src/action-state.css', index)


if __name__ == '__main__':
    unittest.main()
