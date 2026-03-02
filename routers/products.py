from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException
from sqlmodel import Session, select

from cart_helpers import cart_count
from database import get_session
from models.product import Product
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/products")
templates = Jinja2Templates(directory="templates")


def require_user(user: User | None = Depends(get_current_user)):
    if user is None:
        return None
    return user


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def browse_products(
    request: Request,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    products = session.exec(
        select(Product).order_by(Product.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="products_browse.html",
        context={"user": user, "products": products, "cart_count": cart_count(request)},
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
    product = Product(name=name, description=description, price=price, seller_id=user.id)
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

