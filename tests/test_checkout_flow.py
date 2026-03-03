from uuid import uuid4

from models.order import Order
from models.product import Product
from models.user import User
from sqlmodel import Session, select


def test_place_order_requires_login(client, session: Session):
    seller = User(name="Seller", email=f"seller-{uuid4().hex}@example.com", password_hash="fake")
    session.add(seller)
    session.commit()
    session.refresh(seller)

    product = Product(
        name="Login Required Product",
        description="test product",
        price_cents=1200,
        seller_id=seller.id,
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    add_response = client.post(f"/cart/add/{product.id}", data={"quantity": "2"}, follow_redirects=False)
    assert add_response.status_code == 303

    place_response = client.post("/cart/place-order", follow_redirects=False)
    assert place_response.status_code == 303
    assert place_response.headers["location"] == "/auth/login?next=/cart"


def test_checkout_flow_places_order_and_clears_cart(client, session: Session):
    seller = User(name="Seller", email=f"seller-{uuid4().hex}@example.com", password_hash="fake")
    session.add(seller)
    session.commit()
    session.refresh(seller)

    product = Product(
        name="Checkout Product",
        description="test checkout product",
        price_cents=1500,
        seller_id=seller.id,
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    add_response = client.post(f"/cart/add/{product.id}", data={"quantity": "2"}, follow_redirects=False)
    assert add_response.status_code == 303

    register_response = client.post(
        "/auth/register",
        data={
            "name": "Buyer",
            "email": f"buyer-{uuid4().hex}@example.com",
            "password": "123456",
        },
        follow_redirects=False,
    )
    assert register_response.status_code == 303

    place_response = client.post("/cart/place-order", follow_redirects=True)
    assert place_response.status_code == 200
    assert b"Order placed. Thank you!" in place_response.content

    orders_response = client.get("/orders")
    assert orders_response.status_code == 200
    assert b"Checkout Product" in orders_response.content
    assert b"Total: R30.00" in orders_response.content

    cart_response = client.get("/cart")
    assert cart_response.status_code == 200
    assert b"Your cart is empty" in cart_response.content

    orders = session.exec(select(Order)).all()
    assert len(orders) == 1
