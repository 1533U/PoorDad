"""Tests for product tags: create-with-tags, normalization, browse filter, and display."""
from uuid import uuid4

from models.product import Product
from models.tag import Tag
from models.user import User
from sqlmodel import Session, select


def _register(client, *, password: str = "123456"):
    email = f"seller-{uuid4().hex}@example.com"
    r = client.post(
        "/auth/register",
        data={"name": "Seller", "email": email, "password": password},
        follow_redirects=False,
    )
    assert r.status_code == 303
    return email


def test_create_product_normalizes_and_dedupes_tags(client, session: Session):
    _register(client)
    r = client.post(
        "/products/new",
        data={"name": "Mug", "description": "ceramic mug", "price": "120", "tags": "Handmade, ceramics ,  handmade,"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    product = session.exec(select(Product).where(Product.name == "Mug")).first()
    assert product is not None
    names = sorted(t.name for t in product.tags)
    assert names == ["ceramics", "handmade"]  # lowercased, trimmed, deduped


def test_browse_filters_by_tag(client, session: Session):
    seller = User(name="S", email=f"s-{uuid4().hex}@example.com", password_hash="fake")
    session.add(seller)
    session.commit()
    session.refresh(seller)

    handmade = Tag(name="handmade")
    session.add(handmade)
    session.commit()
    session.refresh(handmade)

    tagged = Product(name="Woven Basket", description="d", price_cents=5000, seller_id=seller.id, tags=[handmade])
    untagged = Product(name="Plastic Bin", description="d", price_cents=3000, seller_id=seller.id)
    session.add(tagged)
    session.add(untagged)
    session.commit()

    r = client.get("/products", params={"tag": "handmade"})
    assert r.status_code == 200
    assert b"Woven Basket" in r.content
    assert b"Plastic Bin" not in r.content
    assert b"1 product" in r.content


def test_browse_unknown_tag_returns_empty(client, session: Session):
    seller = User(name="S", email=f"s-{uuid4().hex}@example.com", password_hash="fake")
    session.add(seller)
    session.commit()
    session.refresh(seller)
    session.add(Product(name="Thing", description="d", price_cents=1000, seller_id=seller.id))
    session.commit()

    r = client.get("/products", params={"tag": "nonexistent"})
    assert r.status_code == 200
    assert b"No products" in r.content


def test_product_detail_shows_tags(client, session: Session):
    seller = User(name="S", email=f"s-{uuid4().hex}@example.com", password_hash="fake")
    session.add(seller)
    session.commit()
    session.refresh(seller)

    tag = Tag(name="vintage")
    product = Product(name="Old Clock", description="d", price_cents=9900, seller_id=seller.id, tags=[tag])
    session.add(product)
    session.commit()
    session.refresh(product)

    r = client.get(f"/products/{product.id}")
    assert r.status_code == 200
    assert b"vintage" in r.content
    assert b"?tag=vintage" in r.content  # tag is a clickable filter link
