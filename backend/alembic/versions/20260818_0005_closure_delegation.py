"""Add per-request closure/invoice delegation.

Revision ID: 20260818_0005
Revises: 20260818_0004
Create Date: 2026-08-18

Closure and invoice management is a resource-level responsibility. The original
requester may delegate that responsibility to one active user for a specific
request. Historical delegations are preserved by revocation metadata.

The legacy ``requests:close`` permission is retained for audit/compatibility but
marked inactive because it no longer authorizes closure or invoice mutation.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260818_0005'
down_revision = '20260818_0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if not {'expenses', 'users'} <= tables:
        return

    if 'expense_closure_delegations' not in tables:
        op.create_table(
            'expense_closure_delegations',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column(
                'expense_id',
                sa.Integer(),
                sa.ForeignKey('expenses.id', ondelete='CASCADE'),
                nullable=False,
            ),
            sa.Column(
                'delegate_user_id',
                sa.Integer(),
                sa.ForeignKey('users.id', ondelete='RESTRICT'),
                nullable=False,
            ),
            sa.Column(
                'delegated_by_user_id',
                sa.Integer(),
                sa.ForeignKey('users.id', ondelete='RESTRICT'),
                nullable=False,
            ),
            sa.Column('delegated_by_email', sa.String(length=255), nullable=False),
            sa.Column(
                'created_at',
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                'revoked_by_user_id',
                sa.Integer(),
                sa.ForeignKey('users.id', ondelete='RESTRICT'),
                nullable=True,
            ),
            sa.Column('revoked_by_email', sa.String(length=255), nullable=True),
        )
        op.create_index(
            'ix_expense_closure_delegations_expense',
            'expense_closure_delegations',
            ['expense_id'],
        )
        op.create_index(
            'ix_expense_closure_delegations_delegate',
            'expense_closure_delegations',
            ['delegate_user_id'],
        )
        op.create_index(
            'uq_expense_closure_delegation_active',
            'expense_closure_delegations',
            ['expense_id'],
            unique=True,
            postgresql_where=sa.text('revoked_at IS NULL'),
            sqlite_where=sa.text('revoked_at IS NULL'),
        )

    tables = set(sa.inspect(bind).get_table_names())
    if 'permissions' in tables:
        bind.execute(sa.text('''
            UPDATE permissions
            SET active = FALSE,
                name = 'Cerrar solicitudes (legacy)',
                description = 'Retirado como autoridad runtime: cierre/factura se autoriza por solicitante, system_accounts o delegación por solicitud.'
            WHERE code = 'requests:close'
        '''))


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if 'permissions' in tables:
        bind.execute(sa.text('''
            UPDATE permissions
            SET active = TRUE,
                name = 'Cerrar solicitudes'
            WHERE code = 'requests:close'
        '''))
    if 'expense_closure_delegations' in tables:
        op.drop_table('expense_closure_delegations')
