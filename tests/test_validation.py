from uuid import uuid4

from models.product import Product
from models.user import User
from sqlmodel import Session, select


def _register(client, *, name: str, email: str, password: str, follow_redirects: bool = True):
    return client.post(
        "/auth/register",
        data={"name": name, "email": email, "password": password},
        follow_redirects=follow_redirects,
    )


def _create_product(session: Session, *, seller_id: int, price_cents: int = 1000) -> Product:
    product = Product(
        name=f"Test Product {uuid4().hex[:8]}",
        description="Validation test product",
        price_cents=price_cents,
        seller_id=seller_id,
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


def test_register_rejects_blank_name(client):
    response = _register(
        client,
        name="   ",
        email=f"user-{uuid4().hex}@example.com",
        password="123456",
    )
    assert response.status_code == 422
    assert b"Name is required" in response.content


def test_register_normalizes_email(client, session: Session):
    raw_email = f"  Mixed-{uuid4().hex}@Example.COM  "
    response = _register(client, name="Alice", email=raw_email, password="123456", follow_redirects=False)
    assert response.status_code == 303

    stored = session.exec(
        select(User).where(User.email == raw_email.strip().lower())
    ).first()
    assert stored is not None


def test_create_product_rejects_zero_price(client):
    _register(
        client,
        name="Seller",
        email=f"seller-{uuid4().hex}@example.com",
        password="123456",
    )
    response = client.post(
        "/products/new",
        data={"name": "Item", "description": "desc", "price": "0"},
    )
    assert response.status_code == 422
    assert b"Price must be greater than zero" in response.content


def test_cart_add_negative_quantity_clamps_to_one(client, session: Session):
    seller = User(name="Seller", email=f"seller-{uuid4().hex}@example.com", password_hash="fake")
    session.add(seller)
    session.commit()
    session.refresh(seller)

    product = _create_product(session, seller_id=seller.id, price_cents=1000)

    response = client.post(f"/cart/add/{product.id}", data={"quantity": "-4"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Total: R10.00" in response.content


def test_cart_update_quantity_clamps_to_max(client, session: Session):
    seller = User(name="Seller", email=f"seller-{uuid4().hex}@example.com", password_hash="fake")
    session.add(seller)
    session.commit()
    session.refresh(seller)

    product = _create_product(session, seller_id=seller.id, price_cents=1000)

    client.post(f"/cart/add/{product.id}", data={"quantity": "1"}, follow_redirects=False)
    response = client.post(f"/cart/update/{product.id}", data={"quantity": "1000"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Total: R990.00" in response.content
