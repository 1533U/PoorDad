from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from models.order import Order, OrderItem  # noqa: F401 — imported so SQLModel registers tables
from models.product import Product  # noqa: F401 — imported so SQLModel registers the table
from models.user import User  # noqa: F401 — imported so SQLModel registers the table
from cart_helpers import cart_count
from config import SECRET_KEY
from routers.auth import get_current_user, router as auth_router
from routers.cart import router as cart_router
from routers.orders import router as orders_router
from routers.products import router as products_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is managed by Alembic. Run: alembic upgrade head
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request, user: User | None = Depends(get_current_user)):
    flash_message = request.session.pop("flash_message", None)
    flash_class = request.session.pop("flash_class", None)
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "user": user,
            "flash_message": flash_message,
            "flash_class": flash_class,
            "cart_count": cart_count(request),
        },
    )
