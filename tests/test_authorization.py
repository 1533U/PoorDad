"""Authorization and negative-case tests. See docs/user-stories.md for the story IDs."""
from uuid import uuid4

from models.product import Product
from models.user import User
from sqlmodel import Session, select


def _register(client, email: str | None = None) -> str:
    """Register a fresh user; the client session is now authenticated as them."""
    email = email or f"user-{uuid4().hex}@example.com"
    r = client.post(
        "/auth/register",
        data={"name": "User", "email": email, "password": "123456"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    return email


def _make_user_with_product(session: Session) -> tuple[User, Product]:
    user = User(name="Owner", email=f"owner-{uuid4().hex}@example.com", password_hash="fake")
    session.add(user)
    session.commit()
    session.refresh(user)
    product = Product(name="Thing", description="d", price_cents=1000, seller_id=user.id)
    session.add(product)
    session.commit()
    session.refresh(product)
    return user, product


# ACC-1
def test_duplicate_email_is_rejected(client):
    email = f"dupe-{uuid4().hex}@example.com"
    _register(client, email)
    r = client.post(
        "/auth/register",
        data={"name": "Other", "email": email, "password": "123456"},
        follow_redirects=False,
    )
    assert r.status_code == 409
    assert b"Email already registered" in r.content


# ACC-2
def test_login_with_wrong_password_fails(client):
    email = f"login-{uuid4().hex}@example.com"
    _register(client)  # ensures an account-like flow; create a known user below
    client.post(
        "/auth/register",
        data={"name": "Known", "email": email, "password": "correct-horse"},
        follow_redirects=False,
    )
    r = client.post(
        "/auth/login",
        data={"email": email, "password": "wrong-password"},
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert b"Invalid email or password" in r.content


# LIST-2
def test_owner_can_delete_own_product(client, session: Session):
    email = _register(client)
    owner = session.exec(select(User).where(User.email == email)).one()
    product = Product(name="Mine", description="d", price_cents=2000, seller_id=owner.id)
    session.add(product)
    session.commit()
    session.refresh(product)

    r = client.post(f"/products/{product.id}/delete", follow_redirects=False)
    assert r.status_code == 303
    session.expunge_all()  # the route committed in its own session; reload from DB
    assert session.get(Product, product.id) is None


# LIST-2
def test_other_user_cannot_delete_product_via_post(client, session: Session):
    _owner, product = _make_user_with_product(session)
    _register(client)  # logged in as a different user
    r = client.post(f"/products/{product.id}/delete", follow_redirects=False)
    assert r.status_code == 404
    session.expunge_all()
    assert session.get(Product, product.id) is not None


# LIST-2
def test_other_user_cannot_delete_product_via_htmx(client, session: Session):
    _owner, product = _make_user_with_product(session)
    _register(client)
    r = client.delete(f"/products/{product.id}")
    assert r.status_code == 404
    session.expunge_all()
    assert session.get(Product, product.id) is not None


# LIST-2
def test_delete_missing_product_returns_404(client):
    _register(client)
    r = client.post("/products/999999/delete", follow_redirects=False)
    assert r.status_code == 404


# LIST-2
def test_guest_htmx_delete_is_unauthorized(client, session: Session):
    _owner, product = _make_user_with_product(session)
    r = client.delete(f"/products/{product.id}")  # no login
    assert r.status_code == 401
    session.expunge_all()
    assert session.get(Product, product.id) is not None


# GUARD-1
def test_guest_redirected_from_seller_pages(client):
    for path in ("/products/my", "/products/new", "/orders"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 303, path
        assert r.headers["location"] == "/auth/login", path


# GUARD-1
def test_guest_cannot_create_product(client, session: Session):
    r = client.post(
        "/products/new",
        data={"name": "Sneaky", "description": "d", "price": "10"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/auth/login"
    assert session.exec(select(Product).where(Product.name == "Sneaky")).first() is None


# CART-1
def test_place_order_with_empty_cart_creates_nothing(client):
    _register(client)
    r = client.post("/cart/place-order", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/cart"
    orders = client.get("/orders")
    assert b"no orders yet" in orders.content


# CART-2
def test_orders_are_scoped_to_the_logged_in_user(client, session: Session):
    seller, product = _make_user_with_product(session)

    # Buyer A places an order.
    _register(client)
    client.post(f"/cart/add/{product.id}", data={"quantity": "1"}, follow_redirects=False)
    place = client.post("/cart/place-order", follow_redirects=False)
    assert place.status_code == 303

    a_orders = client.get("/orders")
    assert b"Order #" in a_orders.content

    # Buyer B (fresh login) sees none of A's orders.
    _register(client)
    b_orders = client.get("/orders")
    assert b"Order #" not in b_orders.content
    assert b"no orders yet" in b_orders.content
