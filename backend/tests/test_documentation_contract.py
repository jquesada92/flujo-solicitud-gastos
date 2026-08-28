import re
import unittest
from pathlib import Path
from urllib.parse import unquote


REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / 'backend' / 'alembic' / 'versions'

ROOT_DOCUMENTS = (
    REPO_ROOT / 'AGENTS.md',
    REPO_ROOT / 'CHANGELOG.md',
    REPO_ROOT / 'PROMPT_RECONSTRUCCION.md',
    REPO_ROOT / 'README.md',
    REPO_ROOT / '.specify' / 'memory' / 'constitution.md',
)

MARKDOWN_LINK = re.compile(r'(?<!!)\[[^\]]+\]\(([^)]+)\)')
REVISION = re.compile(r"(?m)^revision\s*=\s*['\"]([^'\"]+)['\"]")
DOWN_REVISION = re.compile(
    r"(?m)^down_revision\s*=\s*(?:['\"]([^'\"]+)['\"]|None)"
)


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def active_env_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in read(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip()
    return values


def normative_markdown_files() -> list[Path]:
    files = set(ROOT_DOCUMENTS)
    files.update((REPO_ROOT / 'docs').glob('*.md'))
    files.update((REPO_ROOT / 'specs').glob('**/*.md'))
    return sorted(files)


class DocumentationContractTests(unittest.TestCase):
    def test_relative_markdown_links_resolve(self):
        failures: list[str] = []
        for document in normative_markdown_files():
            for line_number, line in enumerate(read(document).splitlines(), 1):
                for match in MARKDOWN_LINK.finditer(line):
                    raw_target = match.group(1).strip()
                    if raw_target.startswith(('#', 'http://', 'https://', 'mailto:')):
                        continue
                    target_without_anchor = raw_target.split('#', 1)[0].strip()
                    if not target_without_anchor:
                        continue
                    if target_without_anchor.startswith('<') and target_without_anchor.endswith('>'):
                        target_without_anchor = target_without_anchor[1:-1]
                    target = (document.parent / unquote(target_without_anchor)).resolve()
                    if not target.exists():
                        relative_document = document.relative_to(REPO_ROOT)
                        failures.append(
                            f'{relative_document}:{line_number} -> {raw_target}'
                        )
        self.assertEqual(failures, [], 'Enlaces Markdown locales rotos:\n' + '\n'.join(failures))

    def test_constitution_version_is_synchronized(self):
        constitution = read(REPO_ROOT / '.specify' / 'memory' / 'constitution.md')
        readme = read(REPO_ROOT / 'README.md')
        prompt = read(REPO_ROOT / 'PROMPT_RECONSTRUCCION.md')
        changelog = read(REPO_ROOT / 'CHANGELOG.md')
        history = read(REPO_ROOT / 'docs' / 'HISTORY.md')
        guide = read(REPO_ROOT / 'docs' / 'GUIA_USUARIO_FINAL.md')

        constitution_match = re.search(r'\*\*Versión:\*\*\s*(\d+\.\d+\.\d+)', constitution)
        self.assertIsNotNone(constitution_match)
        version = constitution_match.group(1)
        for name, source in (('README.md', readme), ('PROMPT_RECONSTRUCCION.md', prompt)):
            with self.subTest(document=name):
                self.assertIn(f'Constitución vigente: **{version}**', source)
        self.assertRegex(changelog, rf'(?m)^## {re.escape(version)}\s+—')
        self.assertIn(f'Constitución {version}', guide)
        self.assertIn(f'La Constitución evoluciona a {version}', history)
        for spec_path in (
            REPO_ROOT / 'specs' / '020-mobile-layout' / 'spec.md',
            REPO_ROOT / 'specs' / '021-scoped-approval-rules' / 'spec.md',
            REPO_ROOT / 'specs' / '022-direct-expense-registration' / 'spec.md',
        ):
            with self.subTest(document=spec_path.name, spec=spec_path.parent.name):
                self.assertIn(f'**Constitución:** {version}', read(spec_path))

    def test_alembic_chain_has_one_documented_head(self):
        migrations: dict[str, tuple[str | None, Path]] = {}
        for path in VERSIONS_DIR.glob('*.py'):
            source = read(path)
            revision_match = REVISION.search(source)
            down_match = DOWN_REVISION.search(source)
            self.assertIsNotNone(revision_match, path.name)
            self.assertIsNotNone(down_match, path.name)
            revision = revision_match.group(1)
            self.assertNotIn(revision, migrations, f'Revisión duplicada: {revision}')
            migrations[revision] = (down_match.group(1), path)

        referenced = {down for down, _ in migrations.values() if down is not None}
        missing_parents = sorted(referenced - migrations.keys())
        self.assertEqual(missing_parents, [], f'down_revision inexistente: {missing_parents}')
        heads = sorted(set(migrations) - referenced)
        self.assertEqual(len(heads), 1, f'Se esperaba un head Alembic, encontrados: {heads}')
        head = heads[0]

        canonical_docs = (
            REPO_ROOT / '.specify' / 'memory' / 'constitution.md',
            REPO_ROOT / 'PROMPT_RECONSTRUCCION.md',
            REPO_ROOT / 'README.md',
            REPO_ROOT / 'docs' / 'NEON_SETUP.md',
            REPO_ROOT / 'docs' / 'VALIDACION_LOCAL.md',
        )
        for document in canonical_docs:
            with self.subTest(document=document.name):
                source = read(document)
                self.assertIn(head, source)
                expected_revision_lines = re.findall(
                    r'alembic (?:heads|current)[^\n]*\n\s*#(?:\s*esperado:)?\s*'
                    r'(\d{8}_\d{4})',
                    source,
                )
                for documented_revision in expected_revision_lines:
                    self.assertEqual(
                        documented_revision,
                        head,
                        f'Resultado Alembic obsoleto en {document.name}',
                    )

    def test_documented_source_paths_exist(self):
        required_paths = (
            'AGENTS.md',
            '.github/workflows/ci.yml',
            '.github/workflows/deploy-production.yml',
            '.github/workflows/reusable-ci.yml',
            'backend/app/services/iam_service.py',
            'backend/app/services/approval_engine.py',
            'backend/app/services/approval_policy_service.py',
            'backend/app/api/request_actions.py',
            'backend/app/api/document_actions.py',
            'backend/app/api/direct_expenses.py',
            'backend/app/api/iam_users.py',
            'backend/app/api/iam_access_policy.py',
            'backend/app/core/security.py',
            'backend/scripts/run_tests.py',
            'frontend/src/main.jsx',
            'frontend/src/expense-form.jsx',
            'frontend/src/direct-expense-form.jsx',
            'frontend/src/home-dashboard.jsx',
            'frontend/src/iam-admin.jsx',
            'frontend/src/iam-responsive.css',
            'frontend/src/mobile-layout.css',
            'frontend/src/auth-route-guard.js',
            'frontend/src/request-governor.js',
            'frontend/vite.config.js',
            'docs/CURRENT_PRODUCT_CONTRACT.md',
            'docs/DIRECT_EXPENSES.md',
            'docs/DOCUMENTATION_POLICY.md',
            'docs/GUIA_USUARIO_FINAL.md',
            'docs/KNOWN_RISKS.md',
            'docs/VALIDACION_LOCAL.md',
            'docs/VALIDACION_PRODUCCION.md',
            'specs/021-scoped-approval-rules/spec.md',
            'specs/022-direct-expense-registration/spec.md',
        )
        missing = [path for path in required_paths if not (REPO_ROOT / path).exists()]
        self.assertEqual(missing, [], f'Rutas de soporte inexistentes: {missing}')

    def test_ai_guardrails_cover_high_risk_operations(self):
        agents = read(REPO_ROOT / 'AGENTS.md').lower()
        required_guardrails = (
            'git reset --hard',
            'git clean',
            'force push',
            'docker compose down -v',
            'alembic downgrade',
            'email_mode=console',
            'deploy production',
            'system_accounts',
            'backups/',
            '*.dump',
            '.env',
            'producción',
        )
        for guardrail in required_guardrails:
            with self.subTest(guardrail=guardrail):
                self.assertIn(guardrail, agents)

        gitignore = read(REPO_ROOT / '.gitignore').splitlines()
        self.assertIn('backups/', gitignore)
        self.assertIn('*.dump', gitignore)

    def test_ai_guardrails_preserve_current_access_and_reset_contracts(self):
        agents = read(REPO_ROOT / 'AGENTS.md')
        agents_compact = re.sub(r'\s+', ' ', agents)
        policy = read(REPO_ROOT / 'docs' / 'DOCUMENTATION_POLICY.md')

        access_fragments = (
            'RolePermission ∪ GroupPermission',
            'sin `DENY`',
            'role_ids[0]',
            'Role.max_users',
            'Usuarios activos asignados',
            'bloqueo transaccional',
            'rutas legacy',
        )
        reset_fragments = (
            'password_reset_version',
            '/reset-password#token=',
            'Usuario activo no técnico',
            'no debe aplicar ni descartar el borrador IAM',
        )
        workflow_fragments = (
            'requests:approve`, excluyendo al Solicitante',
            'Sin política aplicable se conserva el fallback IAM global',
            '`approver_profile_codes` no autorizan',
            'solicitud nueva sin ronda iniciable no se persiste',
            'nunca dejar una fila `Expense` huérfana',
            '`NO_APPROVAL` es una modalidad de política',
            'sin crear `Expense`, ronda, voto ni acción pendiente',
        )
        for fragment in access_fragments + reset_fragments + workflow_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, agents_compact)

        self.assertIn('Matriz mínima de impacto', policy)
        self.assertIn('test_documentation_contract.py', policy)
        self.assertIn('no puede omitir una fuente', policy)

    def test_mobile_layout_contract_is_synchronized(self):
        required_fragments = {
            REPO_ROOT / '.specify' / 'memory' / 'constitution.md': (
                '## 18. Experiencia móvil',
                'desde 320 px',
                '1180, 1024, 640, 440, 390 y 320 px',
                '**Registro directo** conserva Área, monto, proveedor, factura, ítem, bandas',
                '320, 360, 390, 412, 440, 600, 640, 768, 820 y 1024 px',
            ),
            REPO_ROOT / 'README.md': (
                '### Layout móvil',
                'frontend/src/mobile-layout.css',
                'frontend/src/direct-expense-form.css',
                'La matriz específica es 320, 360, 390, 412, 440, 600, 640, 768, 820 y 1024 px',
            ),
            REPO_ROOT / 'PROMPT_RECONSTRUCCION.md': (
                'tabla operativa de Solicitudes como tarjetas etiquetadas',
                'objetivos táctiles de al menos 44 px',
                'frontend/src/direct-expense-form.css',
                'Valida en Chrome a 320, 360, 390, 412, 440, 600, 640, 768, 820 y 1024 px',
            ),
            REPO_ROOT / 'docs' / 'CURRENT_PRODUCT_CONTRACT.md': (
                'Contrato responsive global',
                'sin overflow horizontal de página',
                'La matriz específica de aceptación es 320, 360, 390, 412, 440, 600, 640, 768, 820 y 1024 px',
            ),
            REPO_ROOT / 'docs' / 'FRONTEND_RUNTIME.md': (
                '`direct-expense-form.css`',
                'De 320 a 720 px, introducción, formulario y resumen de bandas se apilan',
                'La matriz específica cubre 320, 360, 390, 412, 440, 600, 640, 768, 820 y 1024 px',
                'la pantalla actual no renderiza un panel de historial',
            ),
            REPO_ROOT / 'docs' / 'DIRECT_EXPENSES.md': (
                '## Layout para teléfonos y tabletas',
                'inputs, selects y botones miden al menos 44 px',
                '320, 360, 390, 412, 440, 600, 640, 768, 820 y 1024 px',
            ),
            REPO_ROOT / 'docs' / 'GUIA_USUARIO_FINAL.md': (
                'teléfonos de 320 a 720 px',
                'tabletas de 768, 820 y 1024 px',
                'controles táctiles miden al menos 44 px',
            ),
            REPO_ROOT / 'docs' / 'DOCUMENTATION_POLICY.md': (
                'runtime frontend y guía de usuario aplicable',
                'frontend/src/direct-expense-form.css',
            ),
            REPO_ROOT / 'specs' / '020-mobile-layout' / 'spec.md': (
                '### Registro directo en teléfonos y tabletas',
                'en tabletas de 768, 820 y 1024 px',
            ),
            REPO_ROOT / 'specs' / '020-mobile-layout' / 'plan.md': (
                'para Registro directo ampliar la matriz a 320, 360, 390, 412, 440, 600, 640, 768, 820 y 1024 px',
            ),
            REPO_ROOT / 'specs' / '020-mobile-layout' / 'checklists' / 'acceptance.md': (
                'Registro directo no tiene overflow ni recortes',
                '320, 360, 390, 412, 440, 600, 640, 768, 820 y 1024 px',
            ),
            REPO_ROOT / 'specs' / '022-direct-expense-registration' / 'spec.md': (
                '### Layout para teléfonos y tabletas',
                'La aceptación visual específica se ejecuta en 320, 360, 390, 412, 440, 600, 640, 768, 820 y 1024 px',
            ),
            REPO_ROOT / 'AGENTS.md': (
                '`mobile-layout.css` es la capa responsive transversal',
                'ni ocultar datos/acciones para evitar overflow',
            ),
        }
        for document, fragments in required_fragments.items():
            source = re.sub(r'\s+', ' ', read(document))
            for fragment in fragments:
                with self.subTest(document=document.name, fragment=fragment):
                    self.assertIn(fragment, source)

    def test_scoped_rules_and_direct_expenses_are_synchronized(self):
        required_fragments = {
            REPO_ROOT / '.specify' / 'memory' / 'constitution.md': (
                'El Solicitante no puede cerrar anticipadamente este fallback',
                'responde `409` sin guardar factura ni fijar ganador',
                'no inserta `Expense`, aprobación, invitación, voto, acción pendiente ni estado de Solicitud',
            ),
            REPO_ROOT / 'README.md': (
                'targets solo acotan Usuarios que ya tienen `requests:approve` efectivo',
                '`MULTI_QUOTE` evalúa el máximo de todas sus opciones',
                'solicitud nueva sin ronda iniciable no queda persistida',
                '`NO_APPROVAL` no admite targets ni abre una ronda',
                'nunca crea `Expense`, Solicitud, aprobación, voto o acción pendiente',
                'un `POST` de cierre del Solicitante responde `409` sin guardar factura ni fijar ganador',
            ),
            REPO_ROOT / 'PROMPT_RECONSTRUCCION.md': (
                'un `POST` de cierre debe responder `409` sin guardar factura ni fijar ganador',
                'No crees `Expense`, aprobación, invitación, voto, acción pendiente, `flow_id` ni estado',
            ),
            REPO_ROOT / 'docs' / 'CURRENT_PRODUCT_CONTRACT.md': (
                'un `POST` de cierre responde `409` sin guardar factura ni fijar ganador',
                'No crea `Expense`, Solicitud, ronda, voto, acción pendiente ni estado',
            ),
            REPO_ROOT / 'docs' / 'CONFIGURATION_ACCESS.md': (
                '`approver_profile_codes`',
                'únicamente como metadata física legacy',
                'Un Grupo incluye Usuarios asignados a cualquiera de sus Roles activos',
                '`NO_APPROVAL` se muestra como **No requiere aprobación**',
            ),
            REPO_ROOT / 'docs' / 'DOCUMENTATION_POLICY.md': (
                'Flujo, aprobadores o atomicidad de solicitudes',
                'backend/tests/test_request_flow_creation.py',
                'backend/tests/test_direct_expenses.py',
            ),
            REPO_ROOT / 'docs' / 'VALIDACION_LOCAL.md': (
                '`SIMPLE` sin `ApprovalPolicy`',
                'sin `Expense`, `ExpenseAttachment` ni archivo físico huérfano',
                '`NO_APPROVAL` fuera de banda',
                'otro Usuario no puede listar/descargarlo',
                'el `POST` de cierre del Solicitante antes de `APPROVED` responde `409` sin factura ni ganador',
                '320, 360, 390, 412, 440, 600, 640, 768, 820 y 1024 px',
            ),
            REPO_ROOT / 'docs' / 'DIRECT_EXPENSES.md': (
                '`NO_APPROVAL` no es un tipo ni un estado de Solicitud',
                'nunca crea `Expense`, aprobación, invitación, voto, acción pendiente o `flow_id`',
                'La fila y la factura forman una unidad',
                '## Layout para teléfonos y tabletas',
                'la pantalla actual no renderiza un panel de historial',
            ),
            REPO_ROOT / 'docs' / 'MULTI_QUOTE_VOTING.md': (
                'cualquier `POST` de cierre responde `409` sin guardar factura ni fijar `selected_quotation_id`',
            ),
            REPO_ROOT / 'docs' / 'FASTAPI_ARCHITECTURE.md': (
                'El fallback sin política no satisface esa condición',
                'el `POST` de cierre responde `409` sin guardar factura ni fijar ganador',
            ),
            REPO_ROOT / 'docs' / 'GUIA_USUARIO_FINAL.md': (
                'Pulsa **Registrar gasto y factura**',
                'la pantalla actual no muestra un panel de historial',
            ),
            REPO_ROOT / 'docs' / 'REQUEST_TRACKING.md': (
                'la pantalla actual de **Registro directo** confirma el ID creado, pero no renderiza ese listado',
            ),
            REPO_ROOT / 'specs' / '021-scoped-approval-rules' / 'spec.md': (
                '`max(QuotationOption.amount)`',
                'Seleccionar un Grupo expande todos sus Roles activos',
                'Sin política aplicable se invita a todos los Usuarios activos',
                'Se exige el voto de los `N` invitados',
                'el Solicitante no puede cerrar desde `QUOTATION_VOTING`',
            ),
            REPO_ROOT / 'specs' / '021-scoped-approval-rules' / 'plan.md': (
                'cubrir por HTTP que el Solicitante recibe `409`',
            ),
            REPO_ROOT / 'specs' / '021-scoped-approval-rules' / 'checklists' / 'acceptance.md': (
                'un `POST` de cierre del Solicitante desde `QUOTATION_VOTING` responde 409 sin factura ni ganador seleccionado',
            ),
            REPO_ROOT / 'specs' / '022-direct-expense-registration' / 'spec.md': (
                '`requests:create`',
                'no crea `Expense`, `Approval`, `QuotationVotingInvitation`, voto, acción',
                'un Usuario ordinario lista únicamente sus propios registros',
            ),
            REPO_ROOT / 'specs' / '022-direct-expense-registration' / 'plan.md': (
                'Validar el navegador en 320, 360, 390, 412, 440, 600, 640, 768, 820 y 1024 px',
            ),
            REPO_ROOT / 'specs' / '022-direct-expense-registration' / 'checklists' / 'acceptance.md': (
                'no crea `Expense`, aprobación, invitación, voto, acción pendiente ni estado de Solicitud',
                'navegador a 320, 360, 390, 412, 440, 600, 640, 768, 820 y 1024 px',
            ),
        }
        for document, fragments in required_fragments.items():
            source = re.sub(r'\s+', ' ', read(document))
            for fragment in fragments:
                with self.subTest(document=document.name, fragment=fragment):
                    self.assertIn(fragment, source)

        stale_history_claims = {
            REPO_ROOT / 'docs' / 'FRONTEND_RUNTIME.md': 'formulario, resumen de bandas e historial',
            REPO_ROOT / 'docs' / 'GUIA_USUARIO_FINAL.md': 'queda en el historial de esta pantalla',
            REPO_ROOT / 'docs' / 'REQUEST_TRACKING.md': 'Los gastos directos se consultan en **Registro directo**',
        }
        for document, stale_fragment in stale_history_claims.items():
            with self.subTest(document=document.name, stale_fragment=stale_fragment):
                self.assertNotIn(stale_fragment, read(document))

    def test_environment_examples_use_current_safe_defaults(self):
        backend_examples = (
            REPO_ROOT / 'backend' / '.env.example',
            REPO_ROOT / 'backend' / '.env.preview.example',
        )
        for path in backend_examples:
            source = read(path)
            values = active_env_values(path)
            with self.subTest(example=path.name):
                self.assertNotIn('flujos_de_aprobacion', source)
                self.assertEqual(values.get('DATABASE_SCHEMA'), 'administracion')
                self.assertEqual(values.get('EMAIL_MODE'), 'console')

        obsolete_variables = (
            'DEFAULT_PAGE_SIZE',
            'MAX_PAGE_SIZE',
            'SEARCH_MIN_CHARS',
            'QUERY_TIMEOUT_MS',
        )
        configuration_sources = (
            REPO_ROOT / 'backend' / '.env.example',
            REPO_ROOT / 'backend' / '.env.preview.example',
            REPO_ROOT / 'render.yaml',
        )
        for path in configuration_sources:
            source = read(path)
            for variable in obsolete_variables:
                with self.subTest(source=path.name, obsolete=variable):
                    self.assertNotIn(variable, source)

        root_example = read(REPO_ROOT / '.env.example')
        self.assertNotIn('Neon DEV', root_example)
        self.assertIn('propio PostgreSQL', root_example)

        render = read(REPO_ROOT / 'render.yaml')
        self.assertRegex(render, r'(?m)^\s+- key: EMAIL_MODE\s*\n\s+value: brevo$')

        frontend_example = read(REPO_ROOT / 'frontend' / '.env.example')
        self.assertNotIn('SECRET_KEY=', frontend_example)
        self.assertNotIn('PASSWORD=', frontend_example)
        self.assertIn('Todo valor VITE_* es público', frontend_example)

    def test_readme_routes_development_and_production_safely(self):
        readme = read(REPO_ROOT / 'README.md')
        docs_index = read(REPO_ROOT / 'docs' / 'README.md')
        constitution = read(REPO_ROOT / '.specify' / 'memory' / 'constitution.md')

        self.assertIn('(AGENTS.md)', readme)
        self.assertIn('(docs/VALIDACION_LOCAL.md)', readme)
        self.assertIn('(docs/VALIDACION_PRODUCCION.md)', readme)
        self.assertIn('(docs/GUIA_USUARIO_FINAL.md)', readme)
        self.assertIn('(docs/KNOWN_RISKS.md)', readme)
        self.assertNotIn('git switch main', readme)
        self.assertIn('python.exe -m scripts.run_tests', readme)
        self.assertNotIn('unittest discover -s tests', readme)
        self.assertIn('(VALIDACION_PRODUCCION.md)', docs_index)
        self.assertIn('(GUIA_USUARIO_FINAL.md)', docs_index)
        self.assertIn('(KNOWN_RISKS.md)', docs_index)
        self.assertNotRegex(constitution, r'(?m)^\\\.venv\\Scripts\\python\.exe')

    def test_preview_script_requires_safe_public_configuration(self):
        script = read(REPO_ROOT / 'scripts' / 'start-preview.ps1')
        preview_values = active_env_values(REPO_ROOT / 'backend' / '.env.preview.example')
        compose_values = active_env_values(REPO_ROOT / '.env.preview.example')

        self.assertTrue(preview_values['ADMIN_EMAIL'].startswith('REPLACE_'))
        self.assertTrue(preview_values['ADMIN_PASSWORD'].startswith('REPLACE_'))
        self.assertEqual(compose_values.get('LOCAL_EMAIL_MODE'), 'console')
        for required_fragment in (
            "StartsWith('REPLACE_')",
            "-Name 'LOCAL_PUBLIC_URL'",
            "-Name 'LOCAL_CORS_ALLOWED_ORIGINS'",
            "-Name 'LOCAL_EMAIL_MODE' -Value 'console'",
        ):
            with self.subTest(fragment=required_fragment):
                self.assertIn(required_fragment, script)

    def test_backend_runner_isolated_from_private_dotenv(self):
        runner = read(REPO_ROOT / 'backend' / 'scripts' / 'run_tests.py')
        self.assertIn("Settings.model_config['env_file'] = None", runner)
        self.assertIn("'DATABASE_URL': 'sqlite+pysqlite:///:memory:'", runner)
        self.assertIn("'EMAIL_MODE': 'console'", runner)

        for document in (
            REPO_ROOT / 'AGENTS.md',
            REPO_ROOT / 'README.md',
            REPO_ROOT / 'PROMPT_RECONSTRUCCION.md',
            REPO_ROOT / 'docs' / 'VALIDACION_LOCAL.md',
        ):
            with self.subTest(document=document.name):
                self.assertIn('scripts.run_tests', read(document))

    def test_production_workflow_remains_explicitly_gated(self):
        workflow = read(REPO_ROOT / '.github' / 'workflows' / 'deploy-production.yml')
        pull_request_ci = read(REPO_ROOT / '.github' / 'workflows' / 'ci.yml')
        reusable_ci = read(REPO_ROOT / '.github' / 'workflows' / 'reusable-ci.yml')
        self.assertIn('workflow_dispatch:', workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("confirm_deploy == 'DEPLOY'", workflow)
        self.assertGreaterEqual(workflow.count('environment: production'), 3)
        self.assertIn('uses: ./.github/workflows/reusable-ci.yml', pull_request_ci)
        for gate in (
            'python -m scripts.run_tests',
            'python -m compileall -q app scripts',
            'npm audit --omit=dev --audit-level=moderate',
            'Verify modular expense form is present in the built bundle',
            'Smoke test backend entrypoint and operational module imports',
        ):
            with self.subTest(gate=gate):
                self.assertIn(gate, reusable_ci)


if __name__ == '__main__':
    unittest.main()
