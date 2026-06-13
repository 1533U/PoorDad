"""add cart_item

Revision ID: a1b2c3d4e5f6
Revises: 3f9a1c7b2d04
Create Date: 2026-06-13 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "3f9a1c7b2d04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cart_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_cart_item_user_product"),
    )
    op.create_index(op.f("ix_cart_item_user_id"), "cart_item", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_cart_item_user_id"), table_name="cart_item")
    op.drop_table("cart_item")
