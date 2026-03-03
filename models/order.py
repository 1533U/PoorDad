from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from models.product import Product
from models.user import User


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    buyer_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    buyer: Optional[User] = Relationship()
    items: list["OrderItem"] = Relationship(back_populates="order")


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_item"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    product_id: int = Field(foreign_key="product.id")
    quantity: int = Field(ge=1)
    unit_price_cents: int = Field(ge=0)  # ZAR cents at time of order
    order: Optional[Order] = Relationship(back_populates="items")
    product: Optional[Product] = Relationship()
