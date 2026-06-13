from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class ProductTag(SQLModel, table=True):
    __tablename__ = "product_tag"

    product_id: Optional[int] = Field(default=None, foreign_key="product.id", primary_key=True)
    tag_id: Optional[int] = Field(default=None, foreign_key="tag.id", primary_key=True)


class Tag(SQLModel, table=True):
    __tablename__ = "tag"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)  # stored normalized (lowercased, trimmed)
    products: list["Product"] = Relationship(back_populates="tags", link_model=ProductTag)  # noqa: F821
