from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from cart_helpers import cart_count, get_cart, set_cart
from database import get_session
from models.order import Order, OrderItem
from models.product import Product
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/cart")
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def cart_page(
    request: Request,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    cart = get_cart(request)
    rows = []
    total = 0.0
    for entry in cart:
        product = session.get(Product, entry["product_id"])
        if product is None:
            continue
        qty = entry.get("quantity", 1)
        line = qty * product.price
        total += line
        rows.append({"product": product, "quantity": qty, "line_total": line})
    return templates.TemplateResponse(
        request=request,
        name="cart.html",
        context={"user": user, "cart_rows": rows, "total": total, "cart_count": cart_count(request)},
    )


@router.post("/add/{product_id}")
def add_to_cart(
    request: Request,
    product_id: int,
    quantity: int = Form(1),
    session: Session = Depends(get_session),
):
    product = session.get(Product, product_id)
    if product is None:
        return RedirectResponse(url="/products", status_code=303)
    cart = get_cart(request)
    found = False
    for item in cart:
        if item.get("product_id") == product_id:
            item["quantity"] = item.get("quantity", 0) + quantity
            found = True
            break
    if not found:
        cart.append({"product_id": product_id, "quantity": quantity})
    set_cart(request, cart)
    return RedirectResponse(url="/cart", status_code=303)


@router.post("/update/{product_id}")
def update_cart_item(
    request: Request,
    product_id: int,
    quantity: int = Form(1),
    session: Session = Depends(get_session),
):
    product = session.get(Product, product_id)
    if product is None:
        return RedirectResponse(url="/cart", status_code=303)
    cart = get_cart(request)
    if quantity <= 0:
        cart = [i for i in cart if i.get("product_id") != product_id]
    else:
        found = False
        for item in cart:
            if item.get("product_id") == product_id:
                item["quantity"] = quantity
                found = True
                break
        if not found:
            cart.append({"product_id": product_id, "quantity": quantity})
    set_cart(request, cart)
    return RedirectResponse(url="/cart", status_code=303)


@router.post("/remove/{product_id}")
def remove_from_cart(request: Request, product_id: int):
    cart = [i for i in get_cart(request) if i.get("product_id") != product_id]
    set_cart(request, cart)
    return RedirectResponse(url="/cart", status_code=303)


@router.post("/place-order")
def place_order(
    request: Request,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if user is None:
        return RedirectResponse(url="/auth/login?next=/cart", status_code=303)
    cart = get_cart(request)
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
        qty = max(1, entry.get("quantity", 1))
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=qty,
                unit_price=product.price,
            )
        )
    session.commit()
    set_cart(request, [])
    request.session["flash_message"] = "Order placed. Thank you!"
    request.session["flash_class"] = "success"
    return RedirectResponse(url="/", status_code=303)
