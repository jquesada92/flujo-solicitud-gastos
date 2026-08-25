import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class FrontendConfigurationAccessTests(unittest.TestCase):
    def test_inactive_iam_records_disappear_and_can_be_recovered(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        self.assertIn('/api/iam/users/recovery?identity_document=', source)
        self.assertIn('/api/iam/roles/recovery?name=', source)
        self.assertIn('/api/iam/groups/recovery?name=', source)
        self.assertIn('.filter((user) => user.active)', source)
        self.assertIn('roles.filter((role) => role.active)', source)
        self.assertIn('groups.filter((group) => group.active)', source)
        self.assertIn('recovery ? "Reactivar usuario"', source)
        self.assertIn('recovery ? "Reactivar rol"', source)
        self.assertIn('recovery ? "Reactivar grupo"', source)
        main = (REPO_ROOT / 'frontend' / 'src' / 'main.jsx').read_text(encoding='utf-8')
        self.assertIn('/api/users/recovery?identity_document=', main)
        self.assertIn('onBlur={recoverPerson}', main)

    def test_user_list_searches_identity_role_and_group_and_caps_results(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        self.assertIn('const [userQuery, setUserQuery] = useState("")', source)
        self.assertIn('user.identity_document', source)
        self.assertIn('user.first_name', source)
        self.assertIn('user.last_name', source)
        self.assertIn('...assignedRoles.flatMap((role) => [role.name, role.code])', source)
        self.assertIn('...assignedGroups.flatMap((group) => [group.name, group.code])', source)
        self.assertIn('.normalize("NFD")', source)
        self.assertIn('.replace(/\\p{Diacritic}/gu, "")', source)
        self.assertIn('.slice(0, 10)', source)
        self.assertIn('placeholder="Cédula, nombre, apellido, rol o grupo"', source)
        self.assertIn('Mostrando {visibleUsers.length} usuario(s), máximo 10.', source)

    def test_user_cards_show_every_assigned_role_below_the_email(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        css = (REPO_ROOT / 'frontend' / 'src' / 'iam-responsive.css').read_text(encoding='utf-8')
        card_list = source.split('<div className="iam-list iam-user-list">', 1)[1].split(
            '{!visibleUsers.length', 1
        )[0]
        user_main_css = css.split('.iam-user-list .iam-list-main {', 1)[1].split('}', 1)[0]
        user_roles_css = css.split('.iam-user-list .iam-user-roles {', 1)[1].split('}', 1)[0]

        self.assertIn('.filter((role) => (user.role_ids || []).includes(role.id))', card_list)
        self.assertIn('.map((role) => `${role.name}${role.active ? "" : " (inactivo)"}`)', card_list)
        self.assertIn('<small>{user.email}</small>', card_list)
        self.assertIn('assignedRoleNames.length > 0 && <small className="iam-user-roles">', card_list)
        self.assertIn('assignedRoleNames.length === 1 ? "Rol" : "Roles"', card_list)
        self.assertIn('assignedRoleNames.join(" · ")', card_list)
        self.assertLess(card_list.index('<small>{user.email}</small>'), card_list.index('className="iam-user-roles"'))
        self.assertNotIn('user.role_ids[0]', card_list)
        self.assertIn('iamApi("/api/iam/roles?include_inactive=true")', source)
        self.assertNotIn('current.roles.filter((item) => item.id !== savedRole.id)', source)
        self.assertIn('.iam-user-list .iam-list-main {', css)
        self.assertIn('text-align: left;', user_main_css)
        self.assertIn('.iam-user-list .iam-user-roles {', css)
        self.assertIn('overflow-wrap: anywhere;', user_roles_css)
        self.assertIn('text-overflow: clip;', user_roles_css)
        self.assertIn('white-space: normal;', user_roles_css)

    def test_role_editor_exposes_and_explains_active_user_capacity(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        css = (REPO_ROOT / 'frontend' / 'src' / 'iam-responsive.css').read_text(encoding='utf-8')

        self.assertIn('limit_users: false, max_users: ""', source)
        self.assertIn('max_users: form.limit_users ? Number(form.max_users) : null', source)
        self.assertIn('roleBeingEdited?.assigned_user_count || 0', source)
        self.assertIn('Limitar cantidad de usuarios activos', source)
        self.assertIn('Máximo de usuarios activos', source)
        self.assertIn('Los usuarios inactivos conservan el rol, pero no consumen cupo.', source)
        self.assertIn('role.assigned_user_count >= role.max_users', source)
        self.assertIn('" (sin cupo)"', source)
        self.assertIn('className="iam-role-capacity"', source)
        self.assertIn('.iam-role-limit {', css)
        self.assertIn('.iam-role-list-card .iam-list-main .iam-role-capacity {', css)

    def test_iam_password_reset_is_immediate_accessible_and_preserves_role_drafts(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        css = (REPO_ROOT / 'frontend' / 'src' / 'iam-responsive.css').read_text(encoding='utf-8')
        handler = source.split('const regeneratePassword = async (user) => {', 1)[1].split(
            'const protectedGlobalRoles', 1
        )[0]
        security = source.split('<div className="iam-section iam-security-section">', 1)[1].split(
            '<div className="iam-section"><h3>Rol</h3>', 1
        )[0]

        self.assertIn('passwordRequestUserId !== null', handler)
        self.assertIn('user.is_system_account', handler)
        self.assertIn('`/api/users/${user.id}/regenerate-password`', handler)
        self.assertIn('method: "POST"', handler)
        self.assertIn('enlace de un solo uso', handler)
        self.assertIn('actual seguir', handler)
        self.assertNotIn('reload()', handler)
        self.assertIn('<h3>Seguridad</h3>', security)
        self.assertIn('no guarda ni descarta cambios del rol', security)
        self.assertIn('disabled={!selected.active || passwordRequestUserId !== null}', security)
        self.assertIn('aria-busy={passwordRequestUserId === selected.id}', security)
        self.assertIn('role={passwordNotice.type === "error" ? "alert" : "status"}', security)
        self.assertIn('aria-live={passwordNotice.type === "error" ? "assertive" : "polite"}', security)
        self.assertIn('.iam-security-action {', css)
        self.assertIn('white-space: normal;', css.split('.iam-security-action {', 1)[1].split('}', 1)[0])
        self.assertIn('width: 100%;', css.split('@media (max-width: 640px)', 1)[1])

    def test_public_password_reset_route_consumes_token_without_login_or_analytics(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'main.jsx').read_text(encoding='utf-8')
        styles = (REPO_ROOT / 'frontend' / 'src' / 'styles.css').read_text(encoding='utf-8')
        page = source.split('function ResetPasswordPage() {', 1)[1].split(
            '\nfunction StatusBadge', 1
        )[0]

        self.assertIn('new URLSearchParams(window.location.hash.slice(1)).get("token")', source)
        self.assertIn('const PASSWORD_RESET_TOKEN = isPasswordResetPath()', source)
        self.assertNotIn('window.location.search', page)
        self.assertNotIn('window.location.hash', page)
        self.assertIn('fetch(apiUrl("/api/auth/reset-password")', page)
        self.assertIn('headers: { "Content-Type": "application/json" }', page)
        self.assertNotIn('Authorization', page)
        self.assertIn('JSON.stringify({ token: PASSWORD_RESET_TOKEN, new_password: form.new_password })', page)
        self.assertIn('minLength="10"', page)
        self.assertIn('maxLength="128"', page)
        self.assertIn('form.new_password !== form.confirmation', page)
        self.assertIn('localStorage.removeItem("access_token")', page)
        self.assertIn('if (PASSWORD_RESET_TOKEN) window.history.replaceState({}, "", PASSWORD_RESET_PATH);', source)
        self.assertNotIn('window.history.replaceState', page)
        self.assertNotIn('localStorage.setItem("access_token"', page)
        self.assertIn('role="status" aria-live="polite"', page)
        self.assertIn('role="alert" aria-live="assertive"', page)
        self.assertIn('href="/">Volver a iniciar sesi', page)
        self.assertIn('if (!isPasswordResetPath()) injectSpeedInsights();', source)
        self.assertIn('isPasswordResetPath(pathname)', source)
        self.assertIn('!isPasswordResetPath() && <Analytics', source)
        self.assertLess(source.index('const PASSWORD_RESET_TOKEN'), source.index('injectSpeedInsights();'))
        self.assertLess(source.index('window.history.replaceState'), source.index('injectSpeedInsights();'))
        self.assertLess(source.index('window.history.replaceState'), source.index('createRoot(document.getElementById("root"))'))
        self.assertLess(
            source.index('if (passwordResetRoute) return <ResetPasswordPage />;'),
            source.index('if (!user) return <Login onLogin={setUser} />;'),
        )
        self.assertIn('.reset-password-card {', styles)
        self.assertIn('.reset-login-link {', styles)
        self.assertIn('.reset-login-link:focus-visible {', styles)

    def test_audit_labels_cover_password_reset_link_lifecycle(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'main.jsx').read_text(encoding='utf-8')
        self.assertIn('USER_PASSWORD_RESET_LINK_ISSUED:', source)
        self.assertIn('USER_PASSWORD_RESET_COMPLETED:', source)
        self.assertIn('USER_PASSWORD_REGENERATED:', source)

    def test_legacy_password_regeneration_uses_the_same_link_semantics_without_reload(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'main.jsx').read_text(encoding='utf-8')
        handler = source.split('const regeneratePassword = async (user) => {', 1)[1].split(
            'const changedApartments', 1
        )[0]

        self.assertIn('`/api/users/${user.id}/regenerate-password`', handler)
        self.assertIn('method: "POST"', handler)
        self.assertIn('enlace de un solo uso', handler)
        self.assertIn('actual seguir', handler)
        self.assertNotIn('anterior dejar', handler)
        self.assertNotIn('temporal', handler)
        self.assertNotIn('await load()', handler)
        self.assertIn('aria-busy={saving === `password-${u.id}`}', source)

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
        self.assertIn("readJson('/api/iam/roles')", source)
        self.assertIn("readJson('/api/iam/groups?include_inactive=true')", source)
        self.assertNotIn("readJson('/api/iam/positions')", source)
        self.assertIn('/src/config-readonly.js', index)

    def test_access_console_assigns_one_role_and_displays_derived_group(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        self.assertIn('<h3>Rol</h3>', source)
        self.assertIn('const assignableRoles = useMemo(() =>', source)
        self.assertIn('const selectedRoleId = draftRoleIds[0] || "";', source)
        self.assertIn('const setRole = (rawRoleId) => {', source)
        self.assertIn('setDraftRoleIds(nextRoleId ? [nextRoleId] : []);', source)
        self.assertIn('`Miembro — ${selectedRoleGroup.name}`', source)
        self.assertIn('Sin grupo — Rol global', source)
        self.assertIn('Un rol puede existir sin grupo', source.replace('Un grupo puede existir sin roles. Cada rol puede pertenecer como máximo a un grupo', 'Un rol puede existir sin grupo'))
        self.assertNotIn('<h3>Acceso por grupo</h3>', source)
        self.assertNotIn('<h3>Roles globales</h3>', source)
        self.assertNotIn('const toggleGlobalRole = (roleId, checked)', source)

    def test_create_user_name_fields_follow_left_to_right_person_name_order(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        first_name = source.index('<label>Nombre<input required value={form.first_name}')
        middle_name = source.index('<label>Segundo nombre<input value={form.middle_name}')
        last_name = source.index('<label>Apellido<input required value={form.last_name}')
        second_last_name = source.index('<label>Segundo apellido<input value={form.second_last_name}')
        self.assertLess(first_name, middle_name)
        self.assertLess(middle_name, last_name)
        self.assertLess(last_name, second_last_name)

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
        self.assertIn("document.querySelector('#iam-admin-root [data-unsaved=\"true\"]')", source)
        self.assertIn('setPanelRevision((current) => current + 1);', source)
        self.assertIn('key={`groups-${panelRevision}`}', source)
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
        self.assertIn('const canPersistRole = roleDirty && form.name.trim().length >= 2 && roleLimitIsValid;', source)
        self.assertIn('iam-persist-action ${canPersistRole ? "pending" : ""}', source)
        self.assertIn('disabled={!canPersistRole}', source)
        self.assertIn('button.primary:disabled', action_css)
        self.assertIn('.iam-persist-action.pending', action_css)
        self.assertIn('.classification-save-assignment:not(:disabled)', action_css)
        self.assertIn('/src/action-state.css', index)

    def test_role_master_list_uses_clean_single_surface_rows(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        css = (REPO_ROOT / 'frontend' / 'src' / 'iam-responsive.css').read_text(encoding='utf-8')
        self.assertIn('className="iam-card iam-role-list-card"', source)
        self.assertIn('className="iam-button iam-role-select"', source)
        self.assertIn('className="iam-button iam-role-status"', source)
        self.assertNotIn('style={{ textAlign: "left", flex: 1 }}', source)
        self.assertIn('.iam-role-list-card .iam-role-list-item {', css)
        self.assertIn('grid-template-columns: minmax(0, 1fr) auto;', css)
        self.assertIn('.iam-role-list-card .iam-role-select {', css)
        self.assertIn('.iam-role-list-card .iam-list-main small {', css)
        self.assertIn('.iam-role-list-card .iam-role-status {', css)

    def test_iam_detail_content_wraps_without_widening_cards(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        css = (REPO_ROOT / 'frontend' / 'src' / 'iam-responsive.css').read_text(encoding='utf-8')
        self.assertIn('import "./iam-responsive.css";', source)
        self.assertIn('.iam-shell * {', css)
        self.assertIn('box-sizing: border-box;', css)
        self.assertIn('.iam-toolbar {\n  flex-wrap: wrap;', css)
        self.assertIn('.iam-check > span,', css)
        self.assertIn('.iam-effective-summary,', css)
        self.assertIn('overflow-wrap: anywhere;', css)
        self.assertIn('grid-template-columns: repeat(auto-fit, minmax(min(220px, 100%), 1fr));', css)
        self.assertIn('grid-template-columns: repeat(2, minmax(0, 1fr));', css)

    def test_iam_layout_stacks_before_panels_overflow(self):
        css = (REPO_ROOT / 'frontend' / 'src' / 'iam-responsive.css').read_text(encoding='utf-8')
        self.assertIn('@media (min-width: 1025px) and (max-width: 1180px)', css)
        self.assertIn('grid-template-columns: minmax(280px, 320px) minmax(0, 1fr);', css)
        self.assertIn('@media (max-width: 1024px)', css)
        self.assertIn('@media (max-width: 720px)', css)
        self.assertIn('top: 117px;', css)
        self.assertIn('@media (max-width: 640px)', css)
        self.assertIn('padding: 24px 14px 48px;', css)
        self.assertIn('.iam-checks {\n    grid-template-columns: minmax(0, 1fr);', css)
        self.assertIn('@media (max-width: 440px)', css)

    def test_group_assignments_are_staged_until_explicit_save(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        self.assertIn('const [draftRoleIds, setDraftRoleIds] = useState([]);', source)
        self.assertIn('const [draftPermissionCodes, setDraftPermissionCodes] = useState([]);', source)
        self.assertIn('const [draftMemberIds, setDraftMemberIds] = useState([]);', source)
        self.assertIn('const groupDirty = useMemo(() =>', source)
        self.assertIn('!sameCodes(draftPermissionCodes, selected.permission_codes)', source)
        self.assertIn('const saveGroupAssignments = async () => {', source)
        self.assertIn('selected={draftRoleIds}', source)
        self.assertIn('selected={draftPermissionCodes}', source)
        self.assertIn('selected={draftMemberIds}', source)
        self.assertIn('permission_codes: draftPermissionCodes,', source)
        self.assertIn('data-unsaved={groupDirty || newGroupDirty ? "true" : "false"}', source)
        self.assertIn('iam-persist-action ${groupDirty ? "pending" : ""}', source)
        self.assertIn('disabled={!groupDirty || savingAssignments}', source)
        self.assertIn('{savingAssignments ? "Guardando..." : "Guardar cambios"}', source)
        self.assertIn('Hay cambios sin guardar en este grupo.', source)

    def test_group_inheritance_is_visually_separate_from_role_permissions(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        read_only = (REPO_ROOT / 'frontend' / 'src' / 'config-readonly.js').read_text(encoding='utf-8')
        css = (REPO_ROOT / 'frontend' / 'src' / 'iam-inheritance.css').read_text(encoding='utf-8')
        self.assertIn('Permisos propios del rol', source)
        self.assertIn('form.permission_codes.includes(item.code) ? "También heredado" : "Heredado"', source)
        self.assertIn('de {selectedGroup.name}', source)
        self.assertIn('Permisos aportados por este rol', source)
        self.assertIn('const roleCanGrantAccess = !selectedGroup || selectedGroup.active;', source)
        self.assertIn('isItemDisabled={(item) => SYSTEM_ONLY_PERMISSION_CODES.has(item.code)}', source)
        self.assertIn('data-unsaved={roleDirty ? "true" : "false"}', source)
        self.assertIn('Todos los roles vinculados heredan estos permisos', source)
        self.assertIn('Propios: {role.permission_codes.join', source)
        self.assertIn('Permisos base:', read_only)
        self.assertIn('Permisos propios:', read_only)
        self.assertIn('Permisos heredados:', read_only)
        self.assertIn('const roleCanGrantAccess = !group || group.active;', read_only)
        self.assertIn('.iam-inherited', css)
        self.assertIn('.iam-effective-summary', css)


if __name__ == '__main__':
    unittest.main()
