from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlmodel import Session, select

from cart_helpers import cart_count
from database import get_session
from models.order import Order
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/orders")
templates = Jinja2Templates(directory="templates")

PAGE_SIZE = 12


def _page_url(page: int) -> str:
    return "/orders?" + urlencode({"page": page})


def _base_context(request: Request, user: User | None, **extra: object) -> dict[str, object]:
    context: dict[str, object] = {"user": user, "cart_count": cart_count(request)}
    context.update(extra)
    return context


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def my_orders(
    request: Request,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
    page: int = Query(1, ge=1),
):
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)

    buyer_filter = Order.buyer_id == user.id
    total = session.exec(select(func.count()).select_from(Order).where(buyer_filter)).one()

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)

    orders = session.exec(
        select(Order)
        .where(buyer_filter)
        .order_by(Order.created_at.desc())
        .limit(PAGE_SIZE)
        .offset((page - 1) * PAGE_SIZE)
    ).all()
    order_totals = []
    for order in orders:
        total_cents = sum(item.quantity * item.unit_price_cents for item in order.items)
        order_totals.append({"order": order, "total_cents": total_cents})
    return templates.TemplateResponse(
        request=request,
        name="orders_my.html",
        context=_base_context(
            request,
            user,
            order_totals=order_totals,
            total=total,
            page=page,
            total_pages=total_pages,
            prev_url=_page_url(page - 1) if page > 1 else None,
            next_url=_page_url(page + 1) if page < total_pages else None,
        ),
    )
