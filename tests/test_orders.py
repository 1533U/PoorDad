"""Tests for my orders list and pagination."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from models.order import Order, OrderItem
from models.product import Product
from models.user import User
from sqlmodel import Session, select


@pytest.fixture
def many_orders(client, session: Session):
    """More orders than one page (PAGE_SIZE=12) for the logged-in buyer."""
    email = f"buyer-{uuid4().hex}@example.com"
    register = client.post(
        "/auth/register",
        data={"name": "Buyer", "email": email, "password": "123456"},
        follow_redirects=False,
    )
    assert register.status_code == 303
    buyer = session.exec(select(User).where(User.email == email)).one()

    seller = User(name="Seller", email=f"seller-{uuid4().hex}@example.com", password_hash="fake")
    session.add(seller)
    session.commit()
    session.refresh(seller)

    product = Product(
        name="Order Product",
        description="for pagination tests",
        price_cents=1000,
        seller_id=seller.id,
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    base_time = datetime.now(timezone.utc)
    for i in range(15):
        order = Order(buyer_id=buyer.id, created_at=base_time - timedelta(minutes=i))
        session.add(order)
        session.commit()
        session.refresh(order)
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=1,
                unit_price_cents=product.price_cents,
            )
        )
    session.commit()
    return client


def test_orders_first_page_caps_results_and_shows_next(client, many_orders):
    """First page shows PAGE_SIZE orders, total count, and a Next link but no Prev."""
    r = many_orders.get("/orders")
    assert r.status_code == 200
    assert b"15 orders" in r.content
    assert b"Page 1 of 2" in r.content
    assert b"Next" in r.content
    assert b"Prev" not in r.content
    assert r.content.count(b"product-card") == 12


def test_orders_second_page_shows_remainder_and_prev(client, many_orders):
    """Second page shows the remaining orders and a Prev link but no Next."""
    r = many_orders.get("/orders", params={"page": 2})
    assert r.status_code == 200
    assert b"Page 2 of 2" in r.content
    assert b"Prev" in r.content
    assert b"Next" not in r.content
    assert r.content.count(b"product-card") == 3
