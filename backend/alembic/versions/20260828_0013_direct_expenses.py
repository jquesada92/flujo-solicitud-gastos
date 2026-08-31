"""Add independent direct-expense records for NO_APPROVAL bands.

Revision ID: 20260828_0013
Revises: 20260827_0012
"""

from alembic import op
import sqlalchemy as sa


revision = '20260828_0013'
down_revision = '20260827_0012'
branch_labels = None
depends_on = None


def _schema() -> str | None:
    return op.get_context().config.attributes.get('database_schema')


def _fk(table: str, column: str) -> str:
    schema = _schema()
    return f'{schema}.{table}.{column}' if schema else f'{table}.{column}'


def upgrade() -> None:
    op.create_table(
        'direct_expenses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('record_id', sa.String(length=36), nullable=False),
        sa.Column('display_id', sa.String(length=40), nullable=False),
        sa.Column('expense_area', sa.String(length=80), nullable=False),
        sa.Column('supplier', sa.String(length=200), nullable=False),
        sa.Column('item_description', sa.Text(), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column(
            'requester_user_id',
            sa.Integer(),
            sa.ForeignKey(_fk('users', 'id'), ondelete='RESTRICT'),
            nullable=False,
        ),
        sa.Column('requester_analytics_id', sa.String(length=64), nullable=True),
        sa.Column('requester_email', sa.String(length=255), nullable=False),
        sa.Column('invoice_original_name', sa.String(length=255), nullable=False),
        sa.Column('invoice_stored_name', sa.String(length=255), nullable=False),
        sa.Column('invoice_content_type', sa.String(length=100), nullable=False),
        sa.Column('invoice_size', sa.Integer(), nullable=False),
        # Historical identity only: deleting or editing a policy must not
        # delete or reinterpret an already-recorded direct expense.
        sa.Column('approval_policy_id', sa.Integer(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint('amount > 0', name='ck_direct_expenses_amount_positive'),
        sa.CheckConstraint(
            'invoice_size > 0',
            name='ck_direct_expenses_invoice_size_positive',
        ),
        sa.UniqueConstraint('record_id', name='uq_direct_expenses_record_id'),
        sa.UniqueConstraint('display_id', name='uq_direct_expenses_display_id'),
        sa.UniqueConstraint(
            'invoice_stored_name',
            name='uq_direct_expenses_invoice_stored_name',
        ),
        schema=_schema(),
    )
    op.create_index(
        'ix_direct_expenses_expense_area',
        'direct_expenses',
        ['expense_area'],
        unique=False,
        schema=_schema(),
    )
    op.create_index(
        'ix_direct_expenses_approval_policy_id',
        'direct_expenses',
        ['approval_policy_id'],
        unique=False,
        schema=_schema(),
    )
    op.create_index(
        'ix_direct_expenses_requester_created',
        'direct_expenses',
        ['requester_user_id', 'created_at'],
        unique=False,
        schema=_schema(),
    )


def downgrade() -> None:
    op.drop_index(
        'ix_direct_expenses_requester_created',
        table_name='direct_expenses',
        schema=_schema(),
    )
    op.drop_index(
        'ix_direct_expenses_approval_policy_id',
        table_name='direct_expenses',
        schema=_schema(),
    )
    op.drop_index(
        'ix_direct_expenses_expense_area',
        table_name='direct_expenses',
        schema=_schema(),
    )
    op.drop_table('direct_expenses', schema=_schema())
