"""add tags

Revision ID: 3f9a1c7b2d04
Revises: 28bb64b2f978
Create Date: 2026-06-13 11:25:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3f9a1c7b2d04'
down_revision: Union[str, Sequence[str], None] = '28bb64b2f978'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tag and product_tag (many-to-many) tables."""
    op.create_table(
        'tag',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tag_name'), 'tag', ['name'], unique=True)
    op.create_table(
        'product_tag',
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['product.id'], ),
        sa.ForeignKeyConstraint(['tag_id'], ['tag.id'], ),
        sa.PrimaryKeyConstraint('product_id', 'tag_id'),
    )


def downgrade() -> None:
    """Drop product_tag and tag tables."""
    op.drop_table('product_tag')
    op.drop_index(op.f('ix_tag_name'), table_name='tag')
    op.drop_table('tag')
