from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from cart_helpers import cart_count
from database import get_session
from models.order import Order
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/orders")
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
@router.get("/my", response_class=HTMLResponse)
def my_orders(
    request: Request,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)
    orders = session.exec(
        select(Order).where(Order.buyer_id == user.id).order_by(Order.created_at.desc())
    ).all()
    order_totals = []
    for order in orders:
        total = sum(item.quantity * item.unit_price for item in order.items)
        order_totals.append({"order": order, "total": total})
    return templates.TemplateResponse(
        request=request,
        name="orders_my.html",
        context={"user": user, "order_totals": order_totals, "cart_count": cart_count(request)},
    )
