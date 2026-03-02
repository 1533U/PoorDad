from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from models.user import User


class Product(SQLModel, table=True):
    __tablename__ = "product"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    price: float
    image_url: Optional[str] = Field(default=None)
    seller_id: int = Field(foreign_key="user.id")
    seller: Optional[User] = Relationship()
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))