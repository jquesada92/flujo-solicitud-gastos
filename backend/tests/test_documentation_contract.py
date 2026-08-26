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

        constitution_match = re.search(r'\*\*Versión:\*\*\s*(\d+\.\d+\.\d+)', constitution)
        self.assertIsNotNone(constitution_match)
        version = constitution_match.group(1)
        for name, source in (('README.md', readme), ('PROMPT_RECONSTRUCCION.md', prompt)):
            with self.subTest(document=name):
                self.assertIn(f'Constitución vigente: **{version}**', source)
        self.assertRegex(changelog, rf'(?m)^## {re.escape(version)}\s+—')

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
            'backend/app/api/request_actions.py',
            'backend/app/api/document_actions.py',
            'backend/app/api/iam_users.py',
            'backend/app/api/iam_access_policy.py',
            'backend/app/core/security.py',
            'backend/scripts/run_tests.py',
            'frontend/src/main.jsx',
            'frontend/src/expense-form.jsx',
            'frontend/src/home-dashboard.jsx',
            'frontend/src/iam-admin.jsx',
            'frontend/src/iam-responsive.css',
            'frontend/src/mobile-layout.css',
            'frontend/src/auth-route-guard.js',
            'frontend/src/request-governor.js',
            'frontend/vite.config.js',
            'docs/CURRENT_PRODUCT_CONTRACT.md',
            'docs/DOCUMENTATION_POLICY.md',
            'docs/GUIA_USUARIO_FINAL.md',
            'docs/KNOWN_RISKS.md',
            'docs/VALIDACION_LOCAL.md',
            'docs/VALIDACION_PRODUCCION.md',
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
            'ausencia de política no desactiva IAM',
            'ApprovalPolicy.approver_profile_codes',
            'solicitud nueva sin ronda iniciable no se persiste',
            'nunca dejar una fila `Expense` huérfana',
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
            ),
            REPO_ROOT / 'README.md': (
                '### Layout móvil',
                'frontend/src/mobile-layout.css',
            ),
            REPO_ROOT / 'PROMPT_RECONSTRUCCION.md': (
                'tabla operativa de Solicitudes como tarjetas etiquetadas',
                'objetivos táctiles de al menos 44 px',
            ),
            REPO_ROOT / 'docs' / 'CURRENT_PRODUCT_CONTRACT.md': (
                'Contrato responsive global',
                'sin overflow horizontal de página',
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

    def test_workflow_support_docs_cannot_restore_legacy_approver_authority(self):
        required_fragments = {
            REPO_ROOT / 'README.md': (
                'la única autoridad es `requests:approve` efectivo',
                'solicitud nueva sin ronda iniciable no queda persistida',
            ),
            REPO_ROOT / 'docs' / 'CONFIGURATION_ACCESS.md': (
                '`approver_profile_codes`',
                'metadata legacy y no selecciona, agrega ni autoriza participantes',
            ),
            REPO_ROOT / 'docs' / 'DOCUMENTATION_POLICY.md': (
                'Flujo, aprobadores o atomicidad de solicitudes',
                'backend/tests/test_request_flow_creation.py',
            ),
            REPO_ROOT / 'docs' / 'KNOWN_RISKS.md': (
                'Perfiles legacy visibles en Reglas',
                'no reintroducir filtros por nombre de perfil',
            ),
            REPO_ROOT / 'docs' / 'VALIDACION_LOCAL.md': (
                '`SIMPLE` sin `ApprovalPolicy`',
                'sin `Expense`, `ExpenseAttachment` ni archivo físico huérfano',
            ),
        }
        for document, fragments in required_fragments.items():
            source = re.sub(r'\s+', ' ', read(document))
            for fragment in fragments:
                with self.subTest(document=document.name, fragment=fragment):
                    self.assertIn(fragment, source)

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
