"""Scope approval policies to IAM roles/groups and snapshot voting quorum.

Revision ID: 20260827_0012
Revises: 20260825_0011
"""

from alembic import op
import sqlalchemy as sa


revision = '20260827_0012'
down_revision = '20260825_0011'
branch_labels = None
depends_on = None


def _schema() -> str | None:
    return op.get_context().config.attributes.get('database_schema')


def upgrade() -> None:
    with op.batch_alter_table('approval_policies', schema=_schema()) as batch:
        batch.add_column(
            sa.Column(
                'approver_role_ids',
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )
        batch.add_column(
            sa.Column(
                'approver_group_ids',
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )

    # Legacy profile codes never represented IAM authority. Existing policies
    # therefore remain preserved for audit but are made inactive until an
    # administrator explicitly selects eligible Roles/Groups in the new model.
    policies = sa.table(
        'approval_policies',
        sa.column('active', sa.Boolean()),
        schema=_schema(),
    )
    op.execute(policies.update().where(policies.c.active.is_(True)).values(active=False))

    with op.batch_alter_table('expenses', schema=_schema()) as batch:
        batch.add_column(sa.Column('approval_policy_id', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('approval_policy_mode', sa.String(length=20), nullable=True))
        batch.add_column(sa.Column('policy_evaluation_amount', sa.Numeric(12, 2), nullable=True))
        batch.add_column(sa.Column('minimum_votes_required', sa.Integer(), nullable=True))
        batch.create_index('ix_expenses_approval_policy_id', ['approval_policy_id'], unique=False)
        batch.create_check_constraint(
            'ck_expenses_minimum_votes_required_positive',
            'minimum_votes_required IS NULL OR minimum_votes_required >= 1',
        )


def downgrade() -> None:
    with op.batch_alter_table('expenses', schema=_schema()) as batch:
        batch.drop_constraint(
            'ck_expenses_minimum_votes_required_positive',
            type_='check',
        )
        batch.drop_index('ix_expenses_approval_policy_id')
        batch.drop_column('minimum_votes_required')
        batch.drop_column('policy_evaluation_amount')
        batch.drop_column('approval_policy_mode')
        batch.drop_column('approval_policy_id')

    with op.batch_alter_table('approval_policies', schema=_schema()) as batch:
        batch.drop_column('approver_group_ids')
        batch.drop_column('approver_role_ids')
