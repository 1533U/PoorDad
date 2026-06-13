"""Tests for DB-backed cart persistence and guest session cart."""
from uuid import uuid4

from models.cart import CartItem
from models.product import Product
from models.user import User
from sqlmodel import Session, select


def _make_product(session: Session) -> Product:
    seller = User(name="Seller", email=f"seller-{uuid4().hex}@example.com", password_hash="fake")
    session.add(seller)
    session.commit()
    session.refresh(seller)
    product = Product(
        name="Cart Product",
        description="test",
        price_cents=1500,
        seller_id=seller.id,
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


def _register(client, email: str | None = None) -> str:
    email = email or f"buyer-{uuid4().hex}@example.com"
    response = client.post(
        "/auth/register",
        data={"name": "Buyer", "email": email, "password": "123456"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return email


def _login(client, email: str) -> None:
    response = client.post(
        "/auth/login",
        data={"email": email, "password": "123456"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_guest_session_cart_still_works(client, session: Session):
    """Guests without an account keep a session cart."""
    product = _make_product(session)
    add = client.post(f"/cart/add/{product.id}", data={"quantity": "2"}, follow_redirects=False)
    assert add.status_code == 303

    cart = client.get("/cart")
    assert cart.status_code == 200
    assert b"Cart Product" in cart.content
    assert b"Total: R30.00" in cart.content


def test_db_cart_survives_logout_and_login(client, session: Session):
    """Signed-in users keep cart items across logout and login."""
    product = _make_product(session)
    email = _register(client)

    add = client.post(f"/cart/add/{product.id}", data={"quantity": "2"}, follow_redirects=False)
    assert add.status_code == 303
    buyer = session.exec(select(User).where(User.email == email)).one()
    assert len(session.exec(select(CartItem).where(CartItem.user_id == buyer.id)).all()) == 1

    logout = client.get("/auth/logout", follow_redirects=False)
    assert logout.status_code == 303

    cart_after_logout = client.get("/cart")
    assert b"Your cart is empty" in cart_after_logout.content

    _login(client, email)

    cart_after_login = client.get("/cart")
    assert cart_after_login.status_code == 200
    assert b"Cart Product" in cart_after_login.content
    assert b"Total: R30.00" in cart_after_login.content


def test_register_merges_guest_session_cart_into_db(client, session: Session):
    """Registering after browsing as a guest moves session cart items into the DB cart."""
    product = _make_product(session)

    add = client.post(f"/cart/add/{product.id}", data={"quantity": "1"}, follow_redirects=False)
    assert add.status_code == 303

    email = _register(client)
    buyer = session.exec(select(User).where(User.email == email)).one()
    items = session.exec(select(CartItem).where(CartItem.user_id == buyer.id)).all()
    assert len(items) == 1
    assert items[0].product_id == product.id
    assert items[0].quantity == 1

    cart = client.get("/cart")
    assert b"Cart Product" in cart.content
