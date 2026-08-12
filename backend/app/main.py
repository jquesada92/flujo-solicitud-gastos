import logging
import os
import uuid
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, inspect, select, text, update

from app.api import approvals, auth, categories, expenses, rules, users
from app.core.security import hash_password, normalize_email
from app.core.database import Base, SessionLocal, engine
from app.models.entities import ApprovalRule, ExpenseCategory, ExpenseSubcategory, User, UserRole

logging.basicConfig(level=logging.INFO)

DEFAULT_CATEGORIES = {
    'ADMINISTRATION': ('Administración', [('EQUIPMENT','Equipo'),('SUPPLIES','Insumos'),('SERVICES_PROVIDER','Servicios / Proveedor')]),
    'MAINTENANCE': ('Mantenimiento', [('EQUIPMENT','Equipo'),('SUPPLIES','Insumos'),('SERVICES_PROVIDER','Servicios / Proveedor')]),
    'EXTRAORDINARY': ('Extraordinario', [('EQUIPMENT','Equipo')]),
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
    treasurer = normalize_email(os.getenv('TREASURER_EMAIL', 'tesorero@example.com'))
    president = normalize_email(os.getenv('PRESIDENT_EMAIL', 'presidente@example.com'))

    with SessionLocal() as db:
        default_rules = [
            ApprovalRule(
                expense_type='ADMINISTRATION',
                min_amount=Decimal('0.00'),
                max_amount=Decimal('500.00'),
                approver_email=treasurer,
                approver_role='TESORERO',
                step=1,
            ),
            ApprovalRule(
                expense_type='ADMINISTRATION',
                min_amount=Decimal('500.01'),
                max_amount=None,
                approver_email=treasurer,
                approver_role='TESORERO',
                step=1,
            ),
            ApprovalRule(
                expense_type='ADMINISTRATION',
                min_amount=Decimal('500.01'),
                max_amount=None,
                approver_email=president,
                approver_role='PRESIDENTE',
                step=2,
            ),
            ApprovalRule(
                expense_type='MAINTENANCE',
                min_amount=Decimal('0.00'),
                max_amount=None,
                approver_email=treasurer,
                approver_role='TESORERO',
                step=1,
            ),
            ApprovalRule(
                expense_type='MAINTENANCE',
                min_amount=Decimal('0.00'),
                max_amount=None,
                approver_email=president,
                approver_role='PRESIDENTE',
                step=2,
            ),
            ApprovalRule(
                expense_type='EXTRAORDINARY',
                min_amount=Decimal('0.00'),
                max_amount=None,
                approver_email=president,
                approver_role='PRESIDENTE',
                step=1,
            ),
            ApprovalRule(
                expense_type='LEGAL',
                min_amount=Decimal('0.00'),
                max_amount=None,
                approver_email=president,
                approver_role='PRESIDENTE',
                step=1,
            ),
            ApprovalRule(
                expense_type='POOL', min_amount=Decimal('0.00'), max_amount=None,
                approver_email=treasurer, approver_role='TESORERO', step=1,
            ),
            ApprovalRule(
                expense_type='POOL', min_amount=Decimal('0.00'), max_amount=None,
                approver_email=president, approver_role='PRESIDENTE', step=2,
            ),
            ApprovalRule(
                expense_type='GYM', min_amount=Decimal('0.00'), max_amount=None,
                approver_email=treasurer, approver_role='TESORERO', step=1,
            ),
            ApprovalRule(
                expense_type='GYM', min_amount=Decimal('0.00'), max_amount=None,
                approver_email=president, approver_role='PRESIDENTE', step=2,
            ),
            ApprovalRule(
                expense_type='SQUASH_COURT', min_amount=Decimal('0.00'), max_amount=None,
                approver_email=treasurer, approver_role='TESORERO', step=1,
            ),
            ApprovalRule(
                expense_type='SQUASH_COURT', min_amount=Decimal('0.00'), max_amount=None,
                approver_email=president, approver_role='PRESIDENTE', step=2,
            ),
        ]

        # SUPPLIES used to be a top-level category. It is now a subcategory
        # under OPERATING and MAINTENANCE, whose parent rules apply.
        db.execute(update(ApprovalRule).where(ApprovalRule.expense_type == 'SUPPLIES').values(active=False))
        configured_types = set(db.scalars(select(ApprovalRule.expense_type)).all())
        missing_rules = [rule for rule in default_rules if rule.expense_type not in configured_types]
        db.add_all(missing_rules)
        db.commit()


def migrate_schema() -> None:
    """Small idempotent migration for existing MVP databases."""
    columns = {column['name'] for column in inspect(engine).get_columns('expenses')}
    approval_columns = {column['name'] for column in inspect(engine).get_columns('approvals')}
    user_columns = {column['name'] for column in inspect(engine).get_columns('users')}
    with engine.begin() as connection:
        for name, default in (('can_request','FALSE'),('can_approve','FALSE'),('can_view','TRUE'),('can_configure','FALSE')):
            if name not in user_columns:
                connection.execute(text(f'ALTER TABLE users ADD COLUMN {name} BOOLEAN NOT NULL DEFAULT {default}'))
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
            connection.execute(text('CREATE INDEX IF NOT EXISTS ix_approvals_flow_id ON approvals (flow_id)'))
        if 'expense_subcategory' not in columns:
            connection.execute(text('ALTER TABLE expenses ADD COLUMN expense_subcategory VARCHAR(80)'))
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


def seed_admin() -> None:
    email = normalize_email(os.getenv('ADMIN_EMAIL', 'admin@example.com'))
    password = os.getenv('ADMIN_PASSWORD', 'Admin123!')
    name = os.getenv('ADMIN_NAME', 'Administrador')
    with SessionLocal() as db:
        # Guarantee the configured bootstrap administrator even when other
        # users already exist. Existing credentials are never overwritten.
        if db.scalar(select(User.id).where(func.lower(User.email) == email)):
            return
        db.add(User(name=name, email=email, password_hash=hash_password(password), role=UserRole.ADMIN, can_request=True, can_approve=True, can_view=True, can_configure=True))
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    seed_admin()
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
    allow_origins=['http://localhost:3000', 'http://localhost:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(expenses.router, prefix='/api/expenses', tags=['Expenses'])
app.include_router(approvals.router, prefix='/api/approvals', tags=['Approvals'])
app.include_router(rules.router, prefix='/api/rules', tags=['Approval Rules'])
app.include_router(auth.router, prefix='/api/auth', tags=['Authentication'])
app.include_router(users.router, prefix='/api/users', tags=['Users'])
app.include_router(categories.router, prefix='/api/categories', tags=['Categories'])


@app.get('/api/health')
def health():
    return {'status': 'ok'}
