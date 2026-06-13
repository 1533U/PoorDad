"""Tests for product image_url: create with image, validation, and detail rendering."""
from uuid import uuid4

from models.product import Product
from sqlmodel import Session, select


def _register(client):
    email = f"seller-{uuid4().hex}@example.com"
    r = client.post(
        "/auth/register",
        data={"name": "Seller", "email": email, "password": "123456"},
        follow_redirects=False,
    )
    assert r.status_code == 303


def test_create_product_with_image_url(client, session: Session):
    _register(client)
    url = "https://example.com/chair.jpg"
    r = client.post(
        "/products/new",
        data={"name": "Chair", "description": "a chair", "price": "150", "image_url": url},
        follow_redirects=False,
    )
    assert r.status_code == 303

    product = session.exec(select(Product).where(Product.name == "Chair")).first()
    assert product is not None and product.image_url == url

    detail = client.get(f"/products/{product.id}")
    assert detail.status_code == 200
    assert url.encode() in detail.content
    assert b"product-image" in detail.content


def test_create_product_blank_image_url_is_allowed(client, session: Session):
    _register(client)
    r = client.post(
        "/products/new",
        data={"name": "NoImage", "description": "no image", "price": "99"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    product = session.exec(select(Product).where(Product.name == "NoImage")).first()
    assert product is not None and product.image_url is None


def test_create_product_rejects_non_http_image_url(client):
    _register(client)
    r = client.post(
        "/products/new",
        data={"name": "Bad", "description": "bad url", "price": "50", "image_url": "ftp://x/y.png"},
    )
    assert r.status_code == 422
    assert b"Image URL must start with http" in r.content


def test_detail_shows_empty_state_without_image(client, session: Session):
    _register(client)
    r = client.post(
        "/products/new",
        data={"name": "Plain", "description": "plain", "price": "10"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    product = session.exec(select(Product).where(Product.name == "Plain")).first()
    detail = client.get(f"/products/{product.id}")
    assert b"No image" in detail.content
