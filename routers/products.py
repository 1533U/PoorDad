from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException
from sqlalchemy import func
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
PRICE_MAX_CAP = 100_000_000.0  # R100m in rand
PRODUCT_NAME_MAX_LEN = 120
PRODUCT_DESCRIPTION_MAX_LEN = 4000
PAGE_SIZE = 12


def _page_url(page: int, q: str, min_price: str, max_price: str) -> str:
    """Build a /products URL for the given page, preserving active filters."""
    params: dict[str, object] = {"page": page}
    if q:
        params["q"] = q
    if min_price:
        params["min_price"] = min_price
    if max_price:
        params["max_price"] = max_price
    return "/products?" + urlencode(params)


def _base_context(request: Request, user: User | None, **extra: object) -> dict[str, object]:
    context: dict[str, object] = {"user": user, "cart_count": cart_count(request)}
    context.update(extra)
    return context


def _parse_price(s: str | None) -> float | None:
    """Parse optional query param to float; empty string or None -> None."""
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        v = float(s)
        return v if 0 <= v <= PRICE_MAX_CAP else None
    except ValueError:
        return None


def _validate_product_input(name: str, description: str, price: float) -> str | None:
    name_clean = name.strip()
    description_clean = description.strip()
    if not name_clean:
        return "Product name is required."
    if len(name_clean) > PRODUCT_NAME_MAX_LEN:
        return "Product name is too long."
    if not description_clean:
        return "Description is required."
    if len(description_clean) > PRODUCT_DESCRIPTION_MAX_LEN:
        return "Description is too long."
    if price <= 0:
        return "Price must be greater than zero."
    if price > PRICE_MAX_CAP:
        return "Price is too high."
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
    page: int = Query(1, ge=1),
):
    q_clean = (q or "").strip()
    min_p = _parse_price(min_price)
    max_p = _parse_price(max_price)
    if min_p is not None and max_p is not None and min_p > max_p:
        return templates.TemplateResponse(
            request=request,
            name="products_browse.html",
            status_code=422,
            context=_base_context(
                request,
                user,
                products=[],
                search_query=q_clean,
                min_price=min_price or "",
                max_price=max_price or "",
                error="Min price cannot be greater than max price.",
                total=0,
                page=1,
                total_pages=1,
                prev_url=None,
                next_url=None,
            ),
        )
    min_cents = int(min_p * 100) if min_p is not None else None
    max_cents = int(max_p * 100) if max_p is not None else None

    filters = []
    if q_clean:
        term = f"%{q_clean}%"
        filters.append(or_(Product.name.ilike(term), Product.description.ilike(term)))
    if min_cents is not None:
        filters.append(Product.price_cents >= min_cents)
    if max_cents is not None:
        filters.append(Product.price_cents <= max_cents)

    count_query = select(func.count()).select_from(Product)
    for condition in filters:
        count_query = count_query.where(condition)
    total = session.exec(count_query).one()

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)

    query = select(Product)
    for condition in filters:
        query = query.where(condition)
    query = query.order_by(Product.created_at.desc()).limit(PAGE_SIZE).offset((page - 1) * PAGE_SIZE)
    products = session.exec(query).all()

    return templates.TemplateResponse(
        request=request,
        name="products_browse.html",
        context=_base_context(
            request,
            user,
            products=products,
            search_query=q_clean,
            min_price=min_price or "",
            max_price=max_price or "",
            error=None,
            total=total,
            page=page,
            total_pages=total_pages,
            prev_url=_page_url(page - 1, q_clean, min_price or "", max_price or "") if page > 1 else None,
            next_url=_page_url(page + 1, q_clean, min_price or "", max_price or "") if page < total_pages else None,
        ),
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
        context=_base_context(request, user, products=products),
    )


@router.get("/new", response_class=HTMLResponse)
def new_product_form(request: Request, user: User | None = Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="products_new.html",
        context=_base_context(request, user),
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
        context=_base_context(request, user, product=product),
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
    error = _validate_product_input(name, description, price)
    if error is not None:
        return templates.TemplateResponse(
            request=request,
            name="products_new.html",
            status_code=422,
            context=_base_context(request, user, flash_message=error, flash_class="error"),
        )
    price_cents = round(price * 100)
    product = Product(
        name=name.strip(),
        description=description.strip(),
        price_cents=price_cents,
        seller_id=user.id,
    )
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

