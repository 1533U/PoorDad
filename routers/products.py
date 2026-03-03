from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException
from sqlmodel import Session, select
from sqlmodel import or_

from cart_helpers import cart_count
from database import get_session
from models.product import Product
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/products")
templates = Jinja2Templates(directory="templates")

SEARCH_QUERY_MAX_LEN = 200
PRICE_MIN_DEFAULT = 0.0
PRICE_MAX_CAP = 100_000_000.0  # R1m in rand


def _parse_price(s: str | None) -> float | None:
    """Parse optional query param to float; empty string or None -> None."""
    if s is None or (isinstance(s, str) and not s.strip()):
        return None
    try:
        v = float(s.strip())
        return v if 0 <= v <= PRICE_MAX_CAP else None
    except ValueError:
        return None


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def browse_products(
    request: Request,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
    q: str | None = Query(None, max_length=SEARCH_QUERY_MAX_LEN),
    min_price: str | None = Query(None),
    max_price: str | None = Query(None),
):
    min_p = _parse_price(min_price)
    max_p = _parse_price(max_price)
    if min_p is not None and max_p is not None and min_p > max_p:
        return templates.TemplateResponse(
            request=request,
            name="products_browse.html",
            status_code=422,
            context={
                "user": user,
                "products": [],
                "cart_count": cart_count(request),
                "search_query": q or "",
                "min_price": min_price or "",
                "max_price": max_price or "",
                "error": "Min price cannot be greater than max price.",
            },
        )
    query = select(Product).order_by(Product.created_at.desc())
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.where(
            or_(
                Product.name.ilike(term),
                Product.description.ilike(term),
            )
        )
    min_cents = int(min_p * 100) if min_p is not None else None
    max_cents = int(max_p * 100) if max_p is not None else None
    if min_cents is not None:
        query = query.where(Product.price_cents >= min_cents)
    if max_cents is not None:
        query = query.where(Product.price_cents <= max_cents)
    products = session.exec(query).all()
    return templates.TemplateResponse(
        request=request,
        name="products_browse.html",
        context={
            "user": user,
            "products": products,
            "cart_count": cart_count(request),
            "search_query": q or "",
            "min_price": min_price or "",
            "max_price": max_price or "",
            "error": None,
        },
    )


@router.get("/my", response_class=HTMLResponse)
def my_products(
    request: Request,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)
    products = session.exec(
        select(Product).where(Product.seller_id == user.id).order_by(Product.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="products_my.html",
        context={"user": user, "products": products, "cart_count": cart_count(request)},
    )


@router.get("/new", response_class=HTMLResponse)
def new_product_form(request: Request, user: User | None = Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="products_new.html",
        context={"user": user, "cart_count": cart_count(request)},
    )


@router.get("/{product_id}", response_class=HTMLResponse)
def product_detail(
    request: Request,
    product_id: int,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return templates.TemplateResponse(
        request=request,
        name="products_detail.html",
        context={"user": user, "product": product, "cart_count": cart_count(request)},
    )


@router.post("/new")
def create_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)
    price_cents = max(0, round(price * 100))
    product = Product(name=name, description=description, price_cents=price_cents, seller_id=user.id)
    session.add(product)
    session.commit()
    return RedirectResponse(url="/products/my", status_code=303)


@router.post("/{product_id}/delete")
def delete_product_post(
    product_id: int,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)
    product = session.get(Product, product_id)
    if product is None or product.seller_id != user.id:
        raise HTTPException(status_code=404, detail="Product not found")
    session.delete(product)
    session.commit()
    return RedirectResponse(url="/products", status_code=303)


@router.delete("/{product_id}", response_class=HTMLResponse)
def delete_product(
    request: Request,
    product_id: int,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if user is None:
        return HTMLResponse(status_code=401, content="Unauthorized")
    product = session.get(Product, product_id)
    if product is None or product.seller_id != user.id:
        return HTMLResponse(status_code=404, content="Not found")
    session.delete(product)
    session.commit()
    return HTMLResponse(content="")

