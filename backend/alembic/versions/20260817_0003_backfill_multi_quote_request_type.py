"""Backfill historical MULTI_QUOTE request types.

Revision ID: 20260817_0003
Revises: 20260817_0002
Create Date: 2026-08-17

Some legacy rows can contain quotation options or be in QUOTATION_VOTING while
`request_type` still contains the old SIMPLE default. That inconsistency makes a
correction form depend on whichever request-type tab happened to be selected in
React before editing. Repair the persisted invariant so the request itself is
the source of truth.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260817_0003'
down_revision = '20260817_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if 'expenses' not in tables or 'quotation_options' not in tables:
        return

    bind.execute(sa.text('''
        UPDATE expenses AS expense
        SET request_type = 'MULTI_QUOTE'
        WHERE COALESCE(expense.request_type, 'SIMPLE') <> 'MULTI_QUOTE'
          AND (
            expense.status::text = 'QUOTATION_VOTING'
            OR EXISTS (
                SELECT 1
                FROM quotation_options AS option
                WHERE option.expense_id = expense.id
                GROUP BY option.expense_id
                HAVING COUNT(*) >= 2
            )
          )
    '''))


def downgrade() -> None:
    # This is a data-repair migration. The previous incorrect request_type value
    # cannot be reconstructed safely after the invariant has been repaired.
    pass
