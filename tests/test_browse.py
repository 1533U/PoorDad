"""Tests for browse products: search (q) and price filter (min_price, max_price)."""
import pytest

from models.product import Product
from models.user import User
from sqlmodel import Session, select

_seller_counter = 0


@pytest.fixture
def seller(session: Session):
    """One user to use as product seller; unique email per test to avoid UNIQUE constraint."""
    global _seller_counter
    _seller_counter += 1
    u = User(name="Test Seller", email=f"seller{_seller_counter}@test.example", password_hash="fake")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


@pytest.fixture
def sample_products(session: Session, seller: User):
    """Add a few products so we can test search and price filter."""
    products = [
        Product(name="Wooden chair", description="Handmade oak chair", price_cents=15000, seller_id=seller.id),
        Product(name="Metal lamp", description="Industrial steel lamp", price_cents=8500, seller_id=seller.id),
        Product(name="Wooden table", description="Solid wood dining table", price_cents=45000, seller_id=seller.id),
    ]
    for p in products:
        session.add(p)
    session.commit()
    for p in products:
        session.refresh(p)
    return products


def test_browse_empty_returns_200(client):
    """GET /products with no params returns 200 and empty state when no products."""
    r = client.get("/products")
    assert r.status_code == 200
    assert b"Browse products" in r.content
    assert b"No products" in r.content or b"product-list" in r.content


def test_browse_with_q_filters_by_name_and_description(client, sample_products):
    """Search q=wood returns products with 'wood' in name or description."""
    r = client.get("/products", params={"q": "wood"})
    assert r.status_code == 200
    assert b"Wooden chair" in r.content
    assert b"Wooden table" in r.content
    assert b"Metal lamp" not in r.content


def test_browse_with_min_price_filters(client, sample_products):
    """min_price in rand filters by price_cents."""
    r = client.get("/products", params={"min_price": 100})  # R100 = 10000 cents
    assert r.status_code == 200
    assert b"Wooden table" in r.content  # R450
    assert b"Wooden chair" in r.content  # R150
    assert b"Metal lamp" not in r.content  # R85


def test_browse_with_max_price_filters(client, sample_products):
    """max_price in rand filters by price_cents."""
    r = client.get("/products", params={"max_price": 100})  # R100
    assert r.status_code == 200
    assert b"Metal lamp" in r.content  # R85
    assert b"Wooden chair" not in r.content
    assert b"Wooden table" not in r.content


def test_browse_min_and_max_price(client, sample_products):
    """Both min and max price narrow results."""
    r = client.get("/products", params={"min_price": 80, "max_price": 200})
    assert r.status_code == 200
    assert b"Wooden chair" in r.content  # R150
    assert b"Metal lamp" in r.content   # R85
    assert b"Wooden table" not in r.content  # R450


def test_browse_min_greater_than_max_returns_422_with_error(client):
    """min_price > max_price returns 422 and error message in page."""
    r = client.get("/products", params={"min_price": 100, "max_price": 50})
    assert r.status_code == 422
    assert b"Min price cannot be greater than max price" in r.content
