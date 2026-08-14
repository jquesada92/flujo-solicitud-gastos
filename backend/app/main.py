import logging
import os
import uuid
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, inspect, select, text, update

from app.api import approvals, audit, auth, categories, expenses, rules, users
from app.core.security import hash_password, normalize_email
from app.core.rate_limit import (
    authenticated_subject,
    consume_user_request,
    policy_for_request,
)
from app.core.privacy import analytics_identifier
from app.core.database import Base, SessionLocal, engine
from app.models.entities import AccessProfile, ApprovalPolicy, ApprovalPolicyChangeEvent, ApprovalRule, Expense, ExpenseCategory, ExpenseSubcategory, User, UserRole

logging.basicConfig(level=logging.INFO)


def validate_runtime_security() -> None:
    production = os.getenv('ENVIRONMENT', '').lower() == 'production' or os.getenv('RENDER', '').lower() == 'true'
    if not production:
        return
    errors = []
    secret_key = os.getenv('SECRET_KEY', '')
    analytics_key = os.getenv('ANALYTICS_HASH_KEY', '')
    admin_password = os.getenv('ADMIN_PASSWORD', '')
    origins = cors_origins()
    if len(secret_key) < 32 or secret_key == 'development-only-change-me':
        errors.append('SECRET_KEY must contain at least 32 characters')
    if len(analytics_key) < 32 or analytics_key == secret_key:
        errors.append('ANALYTICS_HASH_KEY must be a separate value of at least 32 characters')
    if len(admin_password) < 12 or admin_password == 'Admin123!':
        errors.append('ADMIN_PASSWORD must contain at least 12 characters')
    if not origins or '*' in origins or any(not origin.startswith('https://') for origin in origins):
        errors.append('CORS_ALLOWED_ORIGINS must contain only explicit HTTPS origins')
    if errors:
        raise RuntimeError('Unsafe production configuration: ' + '; '.join(errors))


def cors_origins() -> list[str]:
    configured = os.getenv('CORS_ALLOWED_ORIGINS', '')
    origins = [origin.strip().rstrip('/') for origin in configured.split(',') if origin.strip()]
    return origins or ['http://localhost:3000', 'http://localhost:5173']

DEFAULT_CATEGORIES = {
    'ADMINISTRATION': ('Administración', [('EQUIPMENT','Equipo'),('SUPPLIES','Insumos'),('SERVICES_PROVIDER','Servicios / Proveedor')]),
    'MAINTENANCE': ('Mantenimiento', [('EQUIPMENT','Equipo'),('SUPPLIES','Insumos'),('SERVICES_PROVIDER','Servicios / Proveedor')]),
    'EXTRAORDINARY': ('Extraordinario', [('GENERAL','General')]),
    'LEGAL': ('Legal', [('CONSULTING','Consultorías'),('PROCEDURES','Trámites'),('LITIGATION','Demandas')]),
    'POOL': ('Piscina', [('EQUIPMENT','Equipo'),('SUPPLIES','Insumos'),('SERVICES_PROVIDER','Servicios / Proveedor')]),
    'GYM': ('Gimnasio', [('EQUIPMENT','Equipo'),('SUPPLIES','Insumos'),('SERVICES_PROVIDER','Servicios / Proveedor')]),
    'SQUASH_COURT': ('Cancha de squash', [('EQUIPMENT','Equipo'),('SUPPLIES','Insumos'),('SERVICES_PROVIDER','Servicios / Proveedor')]),
}


def seed_categories() -> None:
    with SessionLocal() as db:
        for code, (name, subs) in DEFAULT_CATEGORIES.items():
            category = db.scalar(select(ExpenseCategory).where(ExpenseCategory.code == code))
            if not category:
                category = ExpenseCategory(code=code, name=name); db.add(category); db.flush()
            existing = set(db.scalars(select(ExpenseSubcategory.code).where(ExpenseSubcategory.category_id == category.id)).all())
            db.add_all(ExpenseSubcategory(category_id=category.id, code=subcode, name=subname) for subcode, subname in subs if subcode not in existing)
        db.commit()


def seed_rules() -> None:
    with SessionLocal() as db:
        legacy_policy = db.scalar(select(ApprovalPolicy).where(ApprovalPolicy.name == 'Aprobación de toda la Junta Directiva'))
        if legacy_policy:
            legacy_policy.name = 'Aprobación de todo el Organigrama directivo'
        # Approval recipients are resolved from the portal's active board
        # assignments. Legacy rules tied to fixed email addresses stay disabled.
        db.execute(update(ApprovalRule).values(active=False))
        real_policy = db.scalar(select(ApprovalPolicy.id).where(~ApprovalPolicy.name.like('[PRUEBA]%')).limit(1))
        if not real_policy:
            policy = ApprovalPolicy(
                name='Aprobación de todo el Organigrama directivo',
                expense_type='ALL',
                min_amount=Decimal('0.00'),
                max_amount=None,
                approval_mode='ALL',
                approver_profile_codes=['PRESIDENTE', 'VICEPRESIDENTE', 'TESORERO', 'VOCERO'],
                active=True,
            )
            db.add(policy); db.flush()
            admin = db.scalar(select(User).where(User.role == UserRole.ADMIN).order_by(User.id))
            state = {'name': policy.name, 'expense_type': 'ALL', 'min_amount': '0.00',
                     'max_amount': None, 'approval_mode': 'ALL',
                     'approver_profile_codes': policy.approver_profile_codes, 'active': True}
            if admin:
                db.add(ApprovalPolicyChangeEvent(event_type='POLICY_CREATED', policy_id=policy.id,
                    policy_name=policy.name, actor_user_id=admin.id, actor_email='Sistema',
                    changed_fields=list(state), before_state=None, after_state=state))
            for demo_policy in db.scalars(select(ApprovalPolicy).where(
                    ApprovalPolicy.name.like('[PRUEBA]%'), ApprovalPolicy.active.is_(True))).all():
                demo_policy.active = False
        db.commit()


def migrate_schema() -> None:
    """Small idempotent migration for existing MVP databases."""
    columns = {column['name'] for column in inspect(engine).get_columns('expenses')}
    approval_columns = {column['name'] for column in inspect(engine).get_columns('approvals')}
    user_columns = {column['name'] for column in inspect(engine).get_columns('users')}
    profile_columns = {column['name'] for column in inspect(engine).get_columns('access_profiles')}
    with engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO apartments (apartment_number, floor, letter, is_rental)
            SELECT floor::text || letter, floor, letter, FALSE
            FROM generate_series(6, 21) AS floor
            CROSS JOIN unnest(ARRAY['A','B','C','D','E','F','G','H']) AS letter
            ON CONFLICT (apartment_number) DO NOTHING
        """))
        for name, default in (('can_request','FALSE'),('can_approve','FALSE'),('can_view','TRUE'),('can_configure','FALSE'),('must_change_password','FALSE')):
            if name not in user_columns:
                connection.execute(text(f'ALTER TABLE users ADD COLUMN {name} BOOLEAN NOT NULL DEFAULT {default}'))
        if 'session_version' not in user_columns:
            connection.execute(text('ALTER TABLE users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 1'))
        if 'last_activity_at' not in user_columns:
            connection.execute(text('ALTER TABLE users ADD COLUMN last_activity_at TIMESTAMPTZ'))
        if 'title' not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN title VARCHAR(40) NOT NULL DEFAULT 'PROPIETARIO'"))
            connection.execute(text("UPDATE users SET title = CASE WHEN role='ADMIN' THEN 'ADMIN_SISTEMA' WHEN role='APPROVER' THEN 'VOCERO' WHEN role='REQUESTER' THEN 'ADMINISTRADORA' ELSE 'PROPIETARIO' END"))
        if 'apartment_number' not in user_columns:
            connection.execute(text('ALTER TABLE users ADD COLUMN apartment_number VARCHAR(30)'))
            connection.execute(text('CREATE INDEX IF NOT EXISTS ix_users_apartment_number ON users (apartment_number)'))
        for name in ('first_name', 'middle_name', 'last_name', 'second_last_name'):
            if name not in user_columns:
                connection.execute(text(f'ALTER TABLE users ADD COLUMN {name} VARCHAR(70)'))
        if 'identity_document' not in user_columns:
            connection.execute(text('ALTER TABLE users ADD COLUMN identity_document VARCHAR(50)'))
            connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_users_identity_document ON users (identity_document) WHERE identity_document IS NOT NULL'))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_identity_document_normalized ON users (upper(trim(identity_document))) WHERE identity_document IS NOT NULL AND trim(identity_document) <> ''"))
        if 'analytics_id' not in user_columns:
            connection.execute(text('ALTER TABLE users ADD COLUMN analytics_id VARCHAR(64)'))
            connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_users_analytics_id ON users (analytics_id) WHERE analytics_id IS NOT NULL'))
        if 'phone' not in user_columns:
            connection.execute(text('ALTER TABLE users ADD COLUMN phone VARCHAR(30)'))
        if 'person_type' not in user_columns:
            connection.execute(text("DO $$ BEGIN CREATE TYPE persontype AS ENUM ('OWNER','CO_OWNER','CONCIERGE','ADMINISTRATOR','SYSTEM_ADMIN'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"))
            connection.execute(text('ALTER TABLE users ADD COLUMN person_type persontype'))
            connection.execute(text("UPDATE users SET person_type = CASE WHEN role='ADMIN' THEN 'SYSTEM_ADMIN'::persontype WHEN title='ADMINISTRADORA' THEN 'ADMINISTRATOR'::persontype WHEN title IN ('MANTENIMIENTO','CONSERJE') THEN 'CONCIERGE'::persontype ELSE 'OWNER'::persontype END"))
        if 'updated_at' not in user_columns:
            connection.execute(text('ALTER TABLE users ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT now()'))
        connection.execute(text("""
            INSERT INTO user_apartments (user_id, apartment_number, ownership_role)
            SELECT id, upper(apartment_number), 'OWNER' FROM users
            WHERE apartment_number ~ '^([6-9]|1[0-9]|2[01])[A-H]$'
            ON CONFLICT (user_id, apartment_number) DO NOTHING
        """))
        connection.execute(text('DROP INDEX IF EXISTS uq_users_single_active_officer'))
        connection.execute(text("UPDATE access_profiles SET name='Administrador' WHERE code='ADMINISTRADORA' AND name='Administradora'"))
        connection.execute(text("UPDATE access_profiles SET name='Vocal' WHERE code='VOCERO' AND name='Vocero'"))
        if 'has_user_limit' not in profile_columns:
            connection.execute(text('ALTER TABLE access_profiles ADD COLUMN has_user_limit BOOLEAN NOT NULL DEFAULT FALSE'))
        if 'max_users' not in profile_columns:
            connection.execute(text('ALTER TABLE access_profiles ADD COLUMN max_users INTEGER'))
        connection.execute(text("UPDATE access_profiles SET has_user_limit=TRUE, max_users=1 WHERE code IN ('PRESIDENTE','VICEPRESIDENTE','TESORERO') AND has_user_limit=FALSE"))
        connection.execute(text('''
            CREATE OR REPLACE FUNCTION enforce_access_profile_user_limit()
            RETURNS trigger AS $$
            DECLARE configured_limit INTEGER;
            DECLARE assigned_count INTEGER;
            BEGIN
                IF NEW.active = FALSE OR NEW.title = 'ADMIN_SISTEMA' THEN RETURN NEW; END IF;
                PERFORM pg_advisory_xact_lock(hashtext(NEW.title));
                SELECT CASE WHEN has_user_limit THEN max_users ELSE NULL END INTO configured_limit
                FROM access_profiles WHERE code = NEW.title;
                IF configured_limit IS NULL THEN RETURN NEW; END IF;
                SELECT count(*) INTO assigned_count FROM users
                WHERE title = NEW.title AND active = TRUE AND id <> NEW.id;
                IF assigned_count >= configured_limit THEN
                    RAISE EXCEPTION 'access profile % reached its active user limit of %', NEW.title, configured_limit;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        '''))
        connection.execute(text('DROP TRIGGER IF EXISTS users_access_profile_limit ON users'))
        connection.execute(text('''
            CREATE TRIGGER users_access_profile_limit
            BEFORE INSERT OR UPDATE OF title, active ON users
            FOR EACH ROW EXECUTE FUNCTION enforce_access_profile_user_limit()
        '''))
        connection.execute(text("UPDATE users SET can_request=TRUE, can_approve=TRUE, can_view=TRUE, can_configure=TRUE WHERE role='ADMIN'"))
        connection.execute(text("UPDATE users SET can_request=TRUE WHERE role='REQUESTER'"))
        connection.execute(text("UPDATE users SET can_approve=TRUE WHERE role='APPROVER'"))
        connection.execute(text("ALTER TYPE expensestatus ADD VALUE IF NOT EXISTS 'CANCELLED'"))
        connection.execute(text("ALTER TYPE expensestatus ADD VALUE IF NOT EXISTS 'CLOSED'"))
        connection.execute(text("ALTER TYPE expensestatus ADD VALUE IF NOT EXISTS 'NEEDS_REVISION'"))
        connection.execute(text("ALTER TYPE approvalstatus ADD VALUE IF NOT EXISTS 'REVISION_REQUESTED'"))
        connection.execute(text("ALTER TYPE approvalstatus ADD VALUE IF NOT EXISTS 'EXPIRED'"))
        if 'flow_id' not in approval_columns:
            connection.execute(text('ALTER TABLE approvals ADD COLUMN flow_id VARCHAR(36)'))
            connection.execute(text('UPDATE approvals SET flow_id = expenses.flow_id FROM expenses WHERE approvals.expense_id = expenses.id'))
            connection.execute(text('ALTER TABLE approvals ALTER COLUMN flow_id SET NOT NULL'))
        if 'created_at' not in approval_columns:
            connection.execute(text('ALTER TABLE approvals ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now()'))
            connection.execute(text('CREATE INDEX IF NOT EXISTS ix_approvals_flow_id ON approvals (flow_id)'))
        if 'expense_subcategory' not in columns:
            connection.execute(text('ALTER TABLE expenses ADD COLUMN expense_subcategory VARCHAR(80)'))
        if 'requester_analytics_id' not in columns:
            connection.execute(text('ALTER TABLE expenses ADD COLUMN requester_analytics_id VARCHAR(64)'))
            connection.execute(text('CREATE INDEX IF NOT EXISTS ix_expenses_requester_analytics_id ON expenses (requester_analytics_id)'))
        if 'request_id' not in columns:
            connection.execute(text('ALTER TABLE expenses ADD COLUMN request_id VARCHAR(36)'))
        if 'flow_id' not in columns:
            connection.execute(text('ALTER TABLE expenses ADD COLUMN flow_id VARCHAR(36)'))
        if 'display_id' not in columns:
            connection.execute(text('ALTER TABLE expenses ADD COLUMN display_id VARCHAR(40)'))
        if 'item_url' not in columns:
            connection.execute(text('ALTER TABLE expenses ADD COLUMN item_url VARCHAR(2048)'))
        if 'revised_from_request_id' not in columns:
            connection.execute(text('ALTER TABLE expenses ADD COLUMN revised_from_request_id VARCHAR(36)'))
        for name, definition in (
            ('cancelled_at', 'TIMESTAMP'), ('cancelled_by', 'VARCHAR(255)'),
            ('cancellation_reason', 'TEXT'), ('closed_at', 'TIMESTAMP'),
            ('closed_by', 'VARCHAR(255)'), ('closure_notes', 'TEXT'),
        ):
            if name not in columns:
                connection.execute(text(f'ALTER TABLE expenses ADD COLUMN {name} {definition}'))

        existing = connection.execute(text('SELECT id, request_id, flow_id FROM expenses')).mappings().all()
        for expense in existing:
            connection.execute(
                text('UPDATE expenses SET request_id = :request_id, flow_id = :flow_id WHERE id = :id'),
                {
                    'id': expense['id'],
                    'request_id': expense['request_id'] or str(uuid.uuid4()),
                    'flow_id': expense['flow_id'] or str(uuid.uuid4()),
                },
            )
        groups = connection.execute(text('SELECT DISTINCT expense_type, EXTRACT(YEAR FROM created_at)::int AS year FROM expenses')).mappings().all()
        prefixes = {'ADMINISTRATION':'ADM','MAINTENANCE':'MAN','EXTRAORDINARY':'EXT','LEGAL':'LEG','POOL':'PIS','GYM':'GYM','SQUASH_COURT':'SQU'}
        for group in groups:
            category, year = group['expense_type'], group['year']
            rows = connection.execute(text('SELECT id FROM expenses WHERE expense_type=:category AND EXTRACT(YEAR FROM created_at)=:year ORDER BY id'), {'category': category, 'year': year}).mappings().all()
            prefix = prefixes.get(category, category[:3].upper()).ljust(3, 'X')[:3]
            for sequence, row in enumerate(rows, 1):
                connection.execute(text('UPDATE expenses SET display_id=:display_id WHERE id=:id'), {'display_id': f'{prefix}-{year}-{sequence:011d}', 'id': row['id']})
            counter_key = f'{category}:{year}'
            connection.execute(text('''INSERT INTO category_counters (category,last_value) VALUES (:category,:value)
                ON CONFLICT (category) DO UPDATE SET last_value=GREATEST(category_counters.last_value, EXCLUDED.last_value)'''), {'category': counter_key, 'value': len(rows)})
        connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_expenses_request_id ON expenses (request_id)'))
        connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_expenses_flow_id ON expenses (flow_id)'))
        connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_expenses_display_id ON expenses (display_id)'))
        connection.execute(text('CREATE INDEX IF NOT EXISTS ix_expenses_revised_from ON expenses (revised_from_request_id)'))
        connection.execute(text('ALTER TABLE expenses ALTER COLUMN request_id SET NOT NULL'))
        connection.execute(text('ALTER TABLE expenses ALTER COLUMN flow_id SET NOT NULL'))
        connection.execute(text('ALTER TABLE expenses ALTER COLUMN display_id SET NOT NULL'))
        connection.execute(text("UPDATE expenses SET expense_type = 'ADMINISTRATION' WHERE expense_type = 'OPERATING'"))
        connection.execute(text("UPDATE approval_rules SET expense_type = 'ADMINISTRATION' WHERE expense_type = 'OPERATING'"))
        attachment_columns = {column['name'] for column in inspect(engine).get_columns('expense_attachments')}
        if 'document_type' not in attachment_columns:
            connection.execute(text("ALTER TABLE expense_attachments ADD COLUMN document_type VARCHAR(40) NOT NULL DEFAULT 'QUOTATION'"))
        approval_columns = {column['name'] for column in inspect(engine).get_columns('approvals')}
        if 'approval_mode' not in approval_columns:
            connection.execute(text("ALTER TABLE approvals ADD COLUMN approval_mode VARCHAR(20) NOT NULL DEFAULT 'SEQUENTIAL'"))
        connection.execute(text('''
            CREATE OR REPLACE FUNCTION reject_approval_step_event_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'approval_step_events is append-only';
            END;
            $$ LANGUAGE plpgsql
        '''))
        connection.execute(text('DROP TRIGGER IF EXISTS approval_step_events_immutable ON approval_step_events'))
        connection.execute(text('''
            CREATE TRIGGER approval_step_events_immutable
            BEFORE UPDATE OR DELETE ON approval_step_events
            FOR EACH ROW EXECUTE FUNCTION reject_approval_step_event_mutation()
        '''))
        connection.execute(text('''
            CREATE OR REPLACE FUNCTION reject_user_change_event_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'user_change_events is append-only';
            END;
            $$ LANGUAGE plpgsql
        '''))
        connection.execute(text('DROP TRIGGER IF EXISTS user_change_events_immutable ON user_change_events'))
        connection.execute(text('''
            CREATE TRIGGER user_change_events_immutable
            BEFORE UPDATE OR DELETE ON user_change_events
            FOR EACH ROW EXECUTE FUNCTION reject_user_change_event_mutation()
        '''))
        connection.execute(text('DROP TRIGGER IF EXISTS access_profile_change_events_immutable ON access_profile_change_events'))
        connection.execute(text('''
            CREATE TRIGGER access_profile_change_events_immutable
            BEFORE UPDATE OR DELETE ON access_profile_change_events
            FOR EACH ROW EXECUTE FUNCTION reject_user_change_event_mutation()
        '''))
        connection.execute(text('DROP TRIGGER IF EXISTS approval_policy_change_events_immutable ON approval_policy_change_events'))
        connection.execute(text('''
            CREATE TRIGGER approval_policy_change_events_immutable
            BEFORE UPDATE OR DELETE ON approval_policy_change_events
            FOR EACH ROW EXECUTE FUNCTION reject_user_change_event_mutation()
        '''))


def seed_admin() -> None:
    email = normalize_email(os.getenv('ADMIN_EMAIL', 'admin@example.com'))
    password = os.getenv('ADMIN_PASSWORD', 'Admin123!')
    name = os.getenv('ADMIN_NAME', 'Administrador del sistema')
    with SessionLocal() as db:
        # Guarantee the configured bootstrap administrator even when other
        # users already exist. Existing credentials are never overwritten.
        if db.scalar(select(User.id).where(func.lower(User.email) == email)):
            return
        db.add(User(name=name, email=email, analytics_id=analytics_identifier(None, email),
                    password_hash=hash_password(password), role=UserRole.ADMIN, title='ADMIN_SISTEMA',
                    can_request=True, can_approve=True, can_view=True, can_configure=True))
        db.commit()


def backfill_analytics_ids() -> None:
    with SessionLocal() as db:
        users_by_email = {}
        for user in db.scalars(select(User)).all():
            if not user.analytics_id:
                user.analytics_id = analytics_identifier(user.identity_document, user.email)
            users_by_email[user.email.lower()] = user
        db.flush()
        for expense in db.scalars(select(Expense).where(Expense.requester_analytics_id.is_(None))).all():
            requester = users_by_email.get(expense.requested_by.lower())
            if requester:
                expense.requester_analytics_id = requester.analytics_id
        db.commit()


def seed_access_profiles() -> None:
    defaults = [
        ('PRESIDENTE', 'Presidente', True, True, True, False),
        ('VICEPRESIDENTE', 'Vicepresidente', True, True, True, False),
        ('TESORERO', 'Tesorero', True, True, True, False),
        ('VOCERO', 'Vocal', True, True, True, False),
        ('ADMINISTRADORA', 'Administrador', True, False, True, False),
        ('MANTENIMIENTO', 'Mantenimiento', True, False, True, False),
        ('CONSERJE', 'Conserje', True, False, True, False),
        ('PROPIETARIO', 'Propietario', False, False, True, False),
    ]
    with SessionLocal() as db:
        existing = set(db.scalars(select(AccessProfile.code)).all())
        db.add_all(AccessProfile(code=code, name=name, can_request=req, can_approve=approve,
                                 can_view=view, can_configure=configure,
                                 has_user_limit=code in {'PRESIDENTE','VICEPRESIDENTE','TESORERO'},
                                 max_users=1 if code in {'PRESIDENTE','VICEPRESIDENTE','TESORERO'} else None)
                   for code, name, req, approve, view, configure in defaults if code not in existing)
        db.flush()
        profiles = {profile.code: profile for profile in db.scalars(select(AccessProfile)).all()}
        for user in db.scalars(select(User).where(User.role != UserRole.ADMIN)).all():
            profile = profiles.get(user.title)
            if profile:
                user.can_request, user.can_approve = profile.can_request, profile.can_approve
                user.can_view, user.can_configure = profile.can_view, profile.can_configure
                user.role = UserRole.APPROVER if profile.can_approve else UserRole.REQUESTER if profile.can_request else UserRole.VIEWER
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_runtime_security()
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    seed_admin()
    backfill_analytics_ids()
    seed_access_profiles()
    seed_categories()
    seed_rules()
    yield


app = FastAPI(
    title='PH Expense Approval API',
    version='0.1.0',
    lifespan=lifespan,
    docs_url='/api/docs',
    openapi_url='/api/openapi.json',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.middleware('http')
async def limit_authenticated_users(request, call_next):
    excluded = {'/api/health', '/api/auth/login', '/api/auth/activity'}
    if request.method != 'OPTIONS' and request.url.path.startswith('/api/') and request.url.path not in excluded:
        subject = authenticated_subject(request.headers.get('authorization'))
        if subject:
            policy = policy_for_request(request.method, request.url.path)
            allowed, remaining, retry_after = consume_user_request(subject, policy)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={'detail': f'Máximo {policy.limit} acciones de tipo {policy.name} por minuto'},
                    headers={'Retry-After': str(retry_after)},
                )
            request.state.rate_limit_remaining = remaining
            request.state.rate_limit_policy = policy
    response = await call_next(request)
    if hasattr(request.state, 'rate_limit_remaining'):
        policy = request.state.rate_limit_policy
        response.headers['X-RateLimit-Policy'] = policy.name
        response.headers['X-RateLimit-Limit'] = str(policy.limit)
        response.headers['X-RateLimit-Remaining'] = str(request.state.rate_limit_remaining)
        response.headers['X-RateLimit-Window'] = str(policy.window_seconds)
    return response


@app.middleware('http')
async def protect_sensitive_responses(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
    return response

app.include_router(expenses.router, prefix='/api/expenses', tags=['Expenses'])
app.include_router(approvals.router, prefix='/api/approvals', tags=['Approvals'])
app.include_router(rules.router, prefix='/api/rules', tags=['Approval Rules'])
app.include_router(auth.router, prefix='/api/auth', tags=['Authentication'])
app.include_router(users.router, prefix='/api/users', tags=['Users'])
app.include_router(categories.router, prefix='/api/categories', tags=['Categories'])
app.include_router(audit.router, prefix='/api/audit', tags=['Audit'])


@app.get('/api/health')
def health():
    return {'status': 'ok'}
