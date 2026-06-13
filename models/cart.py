from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from models.product import Product
from models.user import User


class CartItem(SQLModel, table=True):
    __tablename__ = "cart_item"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_cart_item_user_product"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    product_id: int = Field(foreign_key="product.id")
    quantity: int = Field(ge=1)
    user: Optional[User] = Relationship()
    product: Optional[Product] = Relationship()
