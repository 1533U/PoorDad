import bcrypt as _bcrypt
import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from cart_helpers import cart_count
from database import get_session
from models.user import User

router = APIRouter(prefix="/auth")
templates = Jinja2Templates(directory="templates")

NAME_MAX_LEN = 100
EMAIL_MAX_LEN = 254
PASSWORD_MIN_LEN = 6
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_current_user(request: Request, session: Session = Depends(get_session)):
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return session.get(User, user_id)


def _base_context(request: Request, user: User | None = None, **extra: object) -> dict[str, object]:
    context: dict[str, object] = {"user": user, "cart_count": cart_count(request)}
    context.update(extra)
    return context


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_registration(name: str, email: str, password: str) -> str | None:
    name_clean = name.strip()
    email_clean = _normalize_email(email)
    if not name_clean:
        return "Name is required."
    if len(name_clean) > NAME_MAX_LEN:
        return "Name is too long."
    if not email_clean:
        return "Email is required."
    if len(email_clean) > EMAIL_MAX_LEN or not EMAIL_RE.match(email_clean):
        return "Enter a valid email address."
    if len(password) < PASSWORD_MIN_LEN:
        return f"Password must be at least {PASSWORD_MIN_LEN} characters."
    return None


def _validate_login(email: str, password: str) -> str | None:
    email_clean = _normalize_email(email)
    if not email_clean or not password:
        return "Email and password are required."
    if len(email_clean) > EMAIL_MAX_LEN or not EMAIL_RE.match(email_clean):
        return "Enter a valid email address."
    return None


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context=_base_context(request),
    )


@router.post("/register")
def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    error = _validate_registration(name, email, password)
    if error is not None:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            status_code=422,
            context=_base_context(request, flash_message=error, flash_class="error"),
        )
    name_clean = name.strip()
    email_clean = _normalize_email(email)
    existing = session.exec(select(User).where(User.email == email_clean)).first()
    if existing:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            status_code=409,
            context=_base_context(
                request,
                flash_message="Email already registered.",
                flash_class="error",
            ),
        )

    hashed = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
    user = User(name=name_clean, email=email_clean, password_hash=hashed)
    session.add(user)
    session.commit()
    session.refresh(user)

    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=_base_context(request),
    )


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    error = _validate_login(email, password)
    if error is not None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            status_code=422,
            context=_base_context(request, flash_message=error, flash_class="error"),
        )
    user = session.exec(select(User).where(User.email == _normalize_email(email))).first()
    if not user or not _bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context=_base_context(
                request,
                flash_message="Invalid email or password.",
                flash_class="error",
            ),
        )

    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
