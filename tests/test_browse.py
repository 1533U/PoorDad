"""Tests for browse products: search (q) and price filter (min_price, max_price)."""
import pytest
from uuid import uuid4

from models.product import Product
from models.user import User
from sqlmodel import Session, select

@pytest.fixture
def seller(session: Session):
    """One user to use as product seller; unique email per test to avoid UNIQUE constraint."""
    u = User(name="Test Seller", email=f"seller-{uuid4().hex}@test.example", password_hash="fake")
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


@pytest.fixture
def many_products(session: Session, seller: User):
    """More products than one page (PAGE_SIZE=12) to exercise pagination."""
    products = [
        Product(name=f"Item {i:02d}", description="paginated", price_cents=1000 + i, seller_id=seller.id)
        for i in range(15)
    ]
    for p in products:
        session.add(p)
    session.commit()
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


def test_browse_first_page_caps_results_and_shows_next(client, many_products):
    """First page shows PAGE_SIZE cards, total count, and a Next link but no Prev."""
    r = client.get("/products")
    assert r.status_code == 200
    assert b"15 products" in r.content
    assert b"Page 1 of 2" in r.content
    assert b"Next" in r.content
    assert b"Prev" not in r.content
    assert r.content.count(b"product-card") == 12


def test_browse_second_page_shows_remainder_and_prev(client, many_products):
    """Second page shows the remaining cards and a Prev link but no Next."""
    r = client.get("/products", params={"page": 2})
    assert r.status_code == 200
    assert b"Page 2 of 2" in r.content
    assert b"Prev" in r.content
    assert b"Next" not in r.content
    assert r.content.count(b"product-card") == 3


def test_browse_pagination_preserves_filters(client, many_products):
    """Pagination links keep the active search query."""
    r = client.get("/products", params={"q": "paginated"})
    assert r.status_code == 200
    assert b"15 products" in r.content
    assert b"q=paginated" in r.content  # next link preserves the filter
