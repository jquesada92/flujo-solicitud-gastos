"""Align expense request columns with Area/Category terminology.

Revision ID: 20260819_0008
Revises: 20260819_0007
Create Date: 2026-08-19

The public contract and application domain use expense_area / expense_category.
This migration renames the existing request columns in place, preserving all
stored values and avoiding a table rewrite.
"""

from alembic import op


revision = '20260819_0008'
down_revision = '20260819_0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('expenses', 'expense_type', new_column_name='expense_area')
    op.alter_column('expenses', 'expense_subcategory', new_column_name='expense_category')
    op.execute(
        'ALTER INDEX IF EXISTS ix_expenses_expense_type '
        'RENAME TO ix_expenses_expense_area'
    )


def downgrade() -> None:
    op.execute(
        'ALTER INDEX IF EXISTS ix_expenses_expense_area '
        'RENAME TO ix_expenses_expense_type'
    )
    op.alter_column('expenses', 'expense_category', new_column_name='expense_subcategory')
    op.alter_column('expenses', 'expense_area', new_column_name='expense_type')
