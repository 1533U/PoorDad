from fastapi import Request
from sqlalchemy import func
from sqlmodel import Session, select

from database import engine
from models.cart import CartItem
from models.user import User

CART_KEY = "cart"
MAX_CART_QUANTITY = 99


def clamp_quantity(quantity: int) -> int:
    try:
        quantity_int = int(quantity)
    except (TypeError, ValueError):
        return 1
    if quantity_int < 1:
        return 1
    if quantity_int > MAX_CART_QUANTITY:
        return MAX_CART_QUANTITY
    return quantity_int


def _session_cart(request: Request) -> list[dict]:
    return request.session.get(CART_KEY) or []


def _set_session_cart(request: Request, items: list[dict]) -> None:
    request.session[CART_KEY] = items


def get_cart(request: Request, session: Session, user: User | None) -> list[dict]:
    if user is not None:
        items = session.exec(select(CartItem).where(CartItem.user_id == user.id)).all()
        return [{"product_id": item.product_id, "quantity": item.quantity} for item in items]
    return _session_cart(request)


def cart_count(request: Request) -> int:
    user_id = request.session.get("user_id")
    if user_id is not None:
        with Session(engine) as session:
            total = session.exec(
                select(func.coalesce(func.sum(CartItem.quantity), 0)).where(CartItem.user_id == user_id)
            ).one()
            return int(total)
    return sum(item.get("quantity", 0) for item in _session_cart(request))


def add_cart_item(
    request: Request,
    session: Session,
    user: User | None,
    product_id: int,
    quantity: int,
) -> None:
    quantity = clamp_quantity(quantity)
    if user is not None:
        existing = session.exec(
            select(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product_id)
        ).first()
        if existing:
            existing.quantity = clamp_quantity(existing.quantity + quantity)
            session.add(existing)
        else:
            session.add(CartItem(user_id=user.id, product_id=product_id, quantity=quantity))
        session.commit()
        return

    cart = _session_cart(request)
    for item in cart:
        if item.get("product_id") == product_id:
            item["quantity"] = clamp_quantity(item.get("quantity", 0) + quantity)
            _set_session_cart(request, cart)
            return
    cart.append({"product_id": product_id, "quantity": quantity})
    _set_session_cart(request, cart)


def update_cart_item(
    request: Request,
    session: Session,
    user: User | None,
    product_id: int,
    quantity: int,
) -> None:
    quantity = min(quantity, MAX_CART_QUANTITY)
    if user is not None:
        existing = session.exec(
            select(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product_id)
        ).first()
        if quantity <= 0:
            if existing:
                session.delete(existing)
        elif existing:
            existing.quantity = quantity
            session.add(existing)
        else:
            session.add(CartItem(user_id=user.id, product_id=product_id, quantity=quantity))
        session.commit()
        return

    cart = _session_cart(request)
    if quantity <= 0:
        cart = [item for item in cart if item.get("product_id") != product_id]
    else:
        found = False
        for item in cart:
            if item.get("product_id") == product_id:
                item["quantity"] = quantity
                found = True
                break
        if not found:
            cart.append({"product_id": product_id, "quantity": quantity})
    _set_session_cart(request, cart)


def remove_cart_item(
    request: Request,
    session: Session,
    user: User | None,
    product_id: int,
) -> None:
    update_cart_item(request, session, user, product_id, 0)


def clear_cart(request: Request, session: Session, user: User | None) -> None:
    if user is not None:
        items = session.exec(select(CartItem).where(CartItem.user_id == user.id)).all()
        for item in items:
            session.delete(item)
        session.commit()
        return
    _set_session_cart(request, [])


def merge_session_cart_into_db(request: Request, session: Session, user_id: int) -> None:
    session_cart = request.session.pop(CART_KEY, None) or []
    if not session_cart:
        return
    for entry in session_cart:
        product_id = entry.get("product_id")
        if product_id is None:
            continue
        quantity = clamp_quantity(entry.get("quantity", 1))
        existing = session.exec(
            select(CartItem).where(CartItem.user_id == user_id, CartItem.product_id == product_id)
        ).first()
        if existing:
            existing.quantity = clamp_quantity(existing.quantity + quantity)
            session.add(existing)
        else:
            session.add(CartItem(user_id=user_id, product_id=product_id, quantity=quantity))
    session.commit()
