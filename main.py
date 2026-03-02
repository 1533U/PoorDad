from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from database import create_db_and_tables
from models.user import User  # noqa: F401 — imported so SQLModel registers the table
from routers.auth import get_current_user, router as auth_router

SECRET_KEY = "change-me-before-deploying"


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.include_router(auth_router)

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request, user: User | None = Depends(get_current_user)):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"user": user},
    )
