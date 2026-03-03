# PoorDad

A small marketplace (Etsy / Moksi-style) for South Africa.

## Aim

PoorDad is a database-centric web app aiming to be a simple marketplace where buyers can browse and purchase and sellers can list products. The focus is South African use, inspired by platforms like Moksi. The project is scoped as a solo MVP: core marketplace features first, with room to grow (payments, search, reviews) later.

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
- View cart, add/remove items, place order (converts cart -> Order + OrderItems in DB).

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

## Done

| Area | What's in place |
|------|------------------|
| **Auth** | Register, login, logout; session cookie; `get_current_user` |
| **Users** | User model; bcrypt password hashing |
| **Products** | Product model (seller relationship, price in cents); full CRUD |
| **Browse** | Search by name/description; filter by min/max price; validation; tests |
| **Detail** | Product page with add-to-cart and owner-only delete |
| **HTMX** | Delete product row without full page reload |
| **Styling** | Centralized CSS with design tokens and component classes |
| **Cart** | Session-based; add/remove; cart count in nav |
| **Orders** | Place order (cart -> DB); "My orders" page |
| **Config** | `SECRET_KEY`, `DATABASE_URL`, `SQL_ECHO` from `.env` via `config.py` |
| **Migrations** | Alembic set up; initial schema + price-to-cents migration |
| **Tests** | pytest + TestClient; 6 browse tests (search, price filter, validation) |

## Still needs work (technical debt)

1. **Input validation** — Most POST routes (register, login, add product) accept anything. Add server-side checks (e.g. non-empty name, positive price, email format) with clear error messages.
2. **No pagination** — Browse loads all products into memory. Add limit/offset as data grows.
3. **Session-only cart** — Cart lives in the cookie; clearing cookies loses it. Consider DB-backed carts for logged-in users.
4. **Styling needs design work** — CSS structure is solid but the visual design is rough: spacing, typography, colour contrast, responsive/mobile layout all need attention.
5. **More tests** — Only browse is tested. Auth, cart, orders, and product CRUD need coverage.

## Next session — pick up here

1. **Tag system** — `Tag` model + `product_tag` link table; assign tags when creating products; filter browse by tag (search and price filter already work).
2. **Product images** — upload or URL; show thumbnail on browse and detail.
3. **Pagination** — paginate browse and order lists.
4. **Validation + more tests** — add validation to remaining POST routes; add tests for auth, cart, orders.
5. **Later** — Real payments (e.g. PayFast), Google sign-in, hosting.
