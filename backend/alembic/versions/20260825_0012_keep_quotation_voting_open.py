"""Keep multi-quote voting open until invoice closure.

Revision ID: 20260825_0012
Revises: 20260825_0011
"""

from alembic import op
import sqlalchemy as sa


revision = '20260825_0012'
down_revision = '20260825_0011'
branch_labels = None
depends_on = None


def _schema() -> str | None:
    return op.get_context().config.attributes.get('database_schema')


def _tables() -> tuple[sa.Table, sa.Table]:
    metadata = sa.MetaData()
    expense_status = sa.Enum(
        'QUOTATION_VOTING',
        'SUBMITTED',
        'PENDING_APPROVAL',
        'APPROVED',
        'REJECTED',
        'CANCELLED',
        'CLOSED',
        'NEEDS_REVISION',
        name='expensestatus',
        schema=_schema(),
    )
    expenses = sa.Table(
        'expenses',
        metadata,
        sa.Column('id', sa.Integer()),
        sa.Column('request_type', sa.String()),
        sa.Column('status', expense_status),
        sa.Column('selected_quotation_id', sa.Integer()),
        schema=_schema(),
    )
    attachments = sa.Table(
        'expense_attachments',
        metadata,
        sa.Column('id', sa.Integer()),
        sa.Column('expense_id', sa.Integer()),
        sa.Column('document_type', sa.String()),
        schema=_schema(),
    )
    return expenses, attachments


def upgrade() -> None:
    expenses, attachments = _tables()
    status_type = expenses.c.status.type
    has_invoice = sa.exists(sa.select(attachments.c.id).where(
        attachments.c.expense_id == expenses.c.id,
        attachments.c.document_type == 'INVOICE',
    ))
    op.execute(
        expenses.update().where(
            expenses.c.request_type == 'MULTI_QUOTE',
            expenses.c.status == sa.cast('APPROVED', status_type),
            ~has_invoice,
        ).values(status=sa.cast('QUOTATION_VOTING', status_type))
    )


def downgrade() -> None:
    expenses, _ = _tables()
    status_type = expenses.c.status.type
    op.execute(
        expenses.update().where(
            expenses.c.request_type == 'MULTI_QUOTE',
            expenses.c.status == sa.cast('QUOTATION_VOTING', status_type),
            expenses.c.selected_quotation_id.is_not(None),
        ).values(status=sa.cast('APPROVED', status_type))
    )
