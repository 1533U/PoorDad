"""price and unit_price to cents

Revision ID: 28bb64b2f978
Revises: 86dc1dc02ba9
Create Date: 2026-03-03 21:48:11.985526

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28bb64b2f978'
down_revision: Union[str, Sequence[str], None] = '86dc1dc02ba9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Store price and unit_price as ZAR cents (int) instead of float."""
    # Product: add price_cents, backfill from price, drop price
    op.add_column("product", sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"))
    op.execute("UPDATE product SET price_cents = CAST(ROUND(price * 100) AS INTEGER)")
    op.drop_column("product", "price")
    # OrderItem: add unit_price_cents, backfill from unit_price, drop unit_price
    op.add_column("order_item", sa.Column("unit_price_cents", sa.Integer(), nullable=False, server_default="0"))
    op.execute("UPDATE order_item SET unit_price_cents = CAST(ROUND(unit_price * 100) AS INTEGER)")
    op.drop_column("order_item", "unit_price")


def downgrade() -> None:
    """Revert to float price and unit_price."""
    op.add_column("product", sa.Column("price", sa.Float(), nullable=True))
    op.execute("UPDATE product SET price = price_cents / 100.0")
    op.drop_column("product", "price_cents")
    op.add_column("order_item", sa.Column("unit_price", sa.Float(), nullable=True))
    op.execute("UPDATE order_item SET unit_price = unit_price_cents / 100.0")
    op.drop_column("order_item", "unit_price_cents")
