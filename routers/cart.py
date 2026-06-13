from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from cart_helpers import (
    add_cart_item,
    cart_count,
    clear_cart,
    clamp_quantity,
    get_cart,
    remove_cart_item,
    update_cart_item,
)
from database import get_session
from models.order import Order, OrderItem
from models.product import Product
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/cart")
templates = Jinja2Templates(directory="templates")


def _base_context(request: Request, user: User | None, **extra: object) -> dict[str, object]:
    context: dict[str, object] = {"user": user, "cart_count": cart_count(request)}
    context.update(extra)
    return context


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def cart_page(
    request: Request,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    cart = get_cart(request, session, user)
    rows = []
    total_cents = 0
    for entry in cart:
        product = session.get(Product, entry["product_id"])
        if product is None:
            continue
        qty = entry.get("quantity", 1)
        line_cents = qty * product.price_cents
        total_cents += line_cents
        rows.append({"product": product, "quantity": qty, "line_total_cents": line_cents})
    return templates.TemplateResponse(
        request=request,
        name="cart.html",
        context=_base_context(request, user, cart_rows=rows, total_cents=total_cents),
    )


@router.post("/add/{product_id}")
def add_to_cart(
    request: Request,
    product_id: int,
    quantity: int = Form(1),
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    product = session.get(Product, product_id)
    if product is None:
        return RedirectResponse(url="/products", status_code=303)
    add_cart_item(request, session, user, product_id, quantity)
    return RedirectResponse(url="/cart", status_code=303)


@router.post("/update/{product_id}")
def update_cart_item_route(
    request: Request,
    product_id: int,
    quantity: int = Form(1),
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    product = session.get(Product, product_id)
    if product is None:
        return RedirectResponse(url="/cart", status_code=303)
    update_cart_item(request, session, user, product_id, quantity)
    return RedirectResponse(url="/cart", status_code=303)


@router.post("/remove/{product_id}")
def remove_from_cart(
    request: Request,
    product_id: int,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    remove_cart_item(request, session, user, product_id)
    return RedirectResponse(url="/cart", status_code=303)


@router.post("/place-order")
def place_order(
    request: Request,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)
    cart = get_cart(request, session, user)
    if not cart:
        return RedirectResponse(url="/cart", status_code=303)
    order = Order(buyer_id=user.id)
    session.add(order)
    session.commit()
    session.refresh(order)
    for entry in cart:
        product = session.get(Product, entry["product_id"])
        if product is None:
            continue
        qty = clamp_quantity(entry.get("quantity", 1))
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=qty,
                unit_price_cents=product.price_cents,
            )
        )
    session.commit()
    clear_cart(request, session, user)
    request.session["flash_message"] = "Order placed. Thank you!"
    request.session["flash_class"] = "success"
    return RedirectResponse(url="/", status_code=303)
