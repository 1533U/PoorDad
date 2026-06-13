# PoorDad

A small marketplace (Etsy / Moksi-style) for South Africa.

## Aim

PoorDad is a database-centric web app aiming to be a simple marketplace where buyers can browse and purchase and sellers can list products. The focus is South African use, inspired by platforms like Moksi. The project is scoped as a solo MVP: core marketplace features first, with room to grow (payments, search, reviews) later.

### MVP definition (v1)

- Any registered user can buy **and** sell — no separate seller role or onboarding.
- Browse, search, and filter products; manage your own listings.
- Session cart → checkout creates an **order record only** (payment arranged offline for now).
- Buyers see order history; sellers see their listings.

### Non-goals (for now)

Payments, OAuth sign-in, multi-vendor payouts, advanced search/recommendations, and hosting/ops optimization. See [Scope guardrails](#scope-guardrails-important) for the full defer list.

## Tech stack

| Layer | Choice |
|-------|--------|
| **Backend** | FastAPI |
| **Templates** | Jinja2 |
| **Interactivity** | HTMX |
| **ORM** | SQLModel |
| **Database** | SQLite (dev/MVP), Postgres later (e.g. Supabase) |
| **Migrations** | Alembic |
| **Auth** | Sessions (Starlette) + bcrypt |
| **Config** | `python-dotenv` (`.env` -> `config.py`) |
| **Testing** | pytest + FastAPI TestClient |
| **Server** | Uvicorn (dev), Gunicorn + Uvicorn (prod) |
| **Frontend styling** | `static/css/app.css` — CSS variables + component classes; one file to retheme |

## Getting started

**Prerequisites:** Python 3.11+

**Set up:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit .env and set a real SECRET_KEY
```

**Create the database (first time, or after cloning):**

```bash
alembic upgrade head
```

**Run the app:**

```bash
uvicorn main:app --reload
```

**Open:** [http://localhost:8000](http://localhost:8000)

**Run tests:**

```bash
pytest tests/ -v
```

### Database migrations (Alembic)

Schema is managed by Alembic (the app does not create tables on startup).

| Situation | What to run |
|-----------|-------------|
| **New project or fresh DB** | `alembic upgrade head` |
| **Existing DB from before Alembic** | `alembic stamp head` (once), then `alembic upgrade head` for future changes |
| **After changing a model** | `alembic revision --autogenerate -m "description"`, review the file, then `alembic upgrade head` |
| **Undo last migration** | `alembic downgrade -1` |
| **Check current revision** | `alembic current` |
| **See history** | `alembic history` |

## Project structure

```
main.py                 FastAPI app, lifespan, home route, includes all routers
config.py               Loads .env; exports SECRET_KEY, DATABASE_URL, SQL_ECHO
database.py             SQLite engine, get_session dependency
cart_helpers.py          Session-based cart utilities (get/set/count)
.env.example            Example env vars; copy to .env
alembic/                Migration scripts; env.py uses config + SQLModel.metadata
models/
  user.py               User model
  product.py            Product model (seller_id -> User, price_cents)
  order.py              Order + OrderItem models (unit_price_cents)
routers/
  auth.py               Register, login, logout, get_current_user
  products.py           Browse (search + price filter), my products, new, detail, delete
  cart.py               Cart page, add/remove items, place order
  orders.py             My orders page
templates/
  base.html             Layout, nav, HTMX script
  home.html             Landing page
  register.html         Registration form
  login.html            Login form
  products_browse.html  Product list with search/filter form and results
  products_my.html      Seller's list + HTMX delete
  products_new.html     Add product form
  products_detail.html  Single product, add to cart, delete if owner
  cart.html             Shopping cart with totals and place-order button
  orders_my.html        Placed orders with items and totals
static/
  css/app.css           All styles (CSS variables + component classes)
tests/
  conftest.py           Pytest fixtures: test DB, client, session
  test_browse.py        Browse: search (q), price filter, validation (6 tests)
requirements.txt        Python dependencies
```

## What was built (walkthrough)

Go through each file at your own pace. This section explains what exists and why.

### 1. `config.py` + `.env`

- Calls `load_dotenv()` then reads `SECRET_KEY`, `DATABASE_URL`, `SQL_ECHO` from the environment.
- Defaults: SQLite file `poordad.db`, SQL echo off, placeholder secret key.
- `.env` is gitignored; `.env.example` shows what to set.

### 2. `database.py`

- Creates the SQLAlchemy engine from `config.DATABASE_URL` with `echo=SQL_ECHO`.
- `get_session()` is a FastAPI dependency that yields a DB session per request.
- Schema is managed by Alembic only (not `create_all`).

### 3. Models

- **User:** `id`, `email` (unique, indexed), `name`, `password_hash`, `created_at`.
- **Product:** `id`, `name`, `description`, `price_cents` (ZAR cents as int), `image_url`, `seller_id` -> User, `created_at`. Uses `Relationship()` to load seller.
- **Order + OrderItem:** Order has `buyer_id` -> User. OrderItem has `order_id`, `product_id`, `quantity`, `unit_price_cents` (cents at time of purchase). One-to-many relationship via `back_populates`.

### 4. `routers/auth.py`

- Register (GET/POST), login (GET/POST), logout (GET).
- Passwords hashed with bcrypt; session cookie stores `user_id`.
- `get_current_user()` dependency: reads session, returns User or None.

### 5. `routers/products.py`

- **Browse (GET `/products`):** search by name/description (`q`), filter by `min_price`/`max_price` (rand, converted to cents). Validates min <= max.
- **My products (GET `/products/my`):** seller's own products.
- **New product (GET/POST `/products/new`):** form; price entered in rand, stored as cents.
- **Detail (GET `/products/{id}`):** full view, "Add to cart", "Delete" if owner.
- **Delete:** POST route (form) + DELETE route (HTMX).

### 6. `routers/cart.py`

- Cart stored in session cookie (no DB table).
- View cart, add/remove items, place order (converts cart → Order + OrderItems in DB; payment is offline/out of scope for v1).

### 7. `routers/orders.py`

- My orders: lists logged-in user's orders with items and totals.

### 8. Templates

- `base.html`: shared layout, nav, flash messages, HTMX script.
- All others extend `base.html` and fill `{% block content %}`.
- Prices displayed as `price_cents / 100` formatted to 2 decimal places.

### 9. Key concepts

- **`Depends`:** FastAPI injects `get_session` and `get_current_user` into route handlers.
- **Session cookie:** signed via `itsdangerous`; stores `user_id`.
- **bcrypt:** one-way password hashing.
- **SQLModel:** ORM + validation in one class; `table=True` = real DB table.
- **303 redirect:** after POST, redirect to GET (prevents double-submit).
- **Alembic:** versioned schema changes; migration scripts in `alembic/versions/`.
- **Cents for money:** prices stored as int (ZAR cents) to avoid float rounding.

---

## Current status (Jun 2026)

The project is in a strong MVP state and runs end-to-end:

- User registration/login/logout with session auth.
- Product browse/create/detail/delete.
- Search + min/max price filtering on browse.
- Session cart with add/update/remove and quantity clamping.
- Checkout flow (cart → order + order items; no payment gateway) and "My orders".
- Input validation on auth and product creation paths.
- Alembic migrations managing schema.
- Tests for browse, validation, and checkout flow (13 passing).

Latest local test run:

```bash
.venv/bin/pytest tests/ -q
# 13 passed
```

## Remaining work (real technical debt)

1. **Pagination**
   Browse and orders pages still load full result sets.
2. **Tagging/filter UX**
   No tag/category model yet.
3. **Image URL UX**
   `image_url` exists on Product, but needs validation, thumbnail rendering, and empty-state handling (uploads/storage deferred).
4. **Cart persistence model**
   Session cart is acceptable for MVP, but DB-backed carts improve resilience.
5. **Authorization and edge cases**
   Continue tightening route-level checks and user-facing error paths.
6. **Test depth**
   Good start, but still light on negative cases and authorization matrix tests.
7. **UI polish**
   Styling framework exists, but responsive/mobile and visual polish need iteration.

## Suggested next milestones (small and learnable)

Do these in order to keep scope controlled:

1. **Pagination first**  
   Add `page` + `page_size` on browse (then orders). This teaches query shaping and UI state.
2. **Tag model second**  
   Add `Tag` and product-tag link table, then filter by tag in browse.
3. **Image URL UX third**  
   Validate existing `image_url` field, render thumbnails, handle missing images.
4. **Authorization/test pass fourth**  
   Add focused tests for "who can do what" and invalid input scenarios.

## Scope guardrails (important)

Same boundaries as [Non-goals](#non-goals-for-now) — repeated here as a planning reminder. Explicitly defer:

- Payments (PayFast, Yoco, etc.)
- OAuth / Google sign-in
- Multi-vendor payouts
- Advanced search / recommendations
- Hosting / ops optimization

Those are post-MVP concerns. Keep this repo as a learning marketplace core.

## If you are using this as a learning project

- Prefer one small vertical slice per session (feature + test + doc update).
- Avoid adding new systems until current features are understandable.
- Treat README as a live status board: update it after each feature.
