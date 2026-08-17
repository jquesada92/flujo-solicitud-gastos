"""Protect technical system accounts from financial permissions.

Revision ID: 20260817_0002
Revises: 20260817_0001
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa

revision = '20260817_0002'
down_revision = '20260817_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if 'system_accounts' not in inspector.get_table_names():
        op.create_table(
            'system_accounts',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('account_type', sa.String(length=50), nullable=False, server_default='TECHNICAL_ADMIN'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('user_id', name='uq_system_accounts_user_id'),
        )
        op.create_index('ix_system_accounts_user_id', 'system_accounts', ['user_id'], unique=True)

    bind = op.get_bind()
    bind.execute(sa.text('''
        INSERT INTO system_accounts (user_id, account_type)
        SELECT id, 'TECHNICAL_ADMIN'
        FROM users
        WHERE role::text = 'ADMIN'
        ON CONFLICT (user_id) DO NOTHING
    '''))


def downgrade() -> None:
    op.drop_table('system_accounts')
