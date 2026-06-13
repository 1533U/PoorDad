# PoorDad

A small marketplace (Etsy / Moksi-style) for South Africa.

## Aim

PoorDad is a database-centric web app aiming to be a simple marketplace where buyers can browse and purchase and sellers can list products. The focus is South African use, inspired by platforms like Moksi. The project is scoped as a solo MVP: core marketplace features first, with room to grow (payments, search, reviews) later.

### MVP definition (v1)

- Any registered user can buy **and** sell — no separate seller role or onboarding.
- Browse, search, and filter products; manage your own listings.
- DB-backed cart for signed-in users (session cart for guests until login/register); checkout creates an **order record only** (payment arranged offline for now).
- Buyers see order history; sellers see their listings.

### Non-goals (for now)

Payments, OAuth sign-in, multi-vendor payouts, advanced search/recommendations, and hosting/ops optimization. See [Scope guardrails](#scope-guardrails-important) for the full defer list.

### Working agreement (keep it clean)

The standing plan is **less is more**: favor removing the unnecessary over adding. No dead code, no half-built features on `main`, no build artifacts (DBs, caches, `.env`) in git, tests stay green, and this README stays in sync with the code after every change. These rules are enforced for the AI agent in `.cursor/rules/keep-it-clean.mdc`.

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
cart_helpers.py          Cart utilities: DB cart for signed-in users, session cart for guests
.env.example            Example env vars; copy to .env
alembic/                Migration scripts; env.py uses config + SQLModel.metadata
models/
  user.py               User model
  product.py            Product model (seller_id -> User, price_cents, tags)
  order.py              Order + OrderItem models (unit_price_cents)
  cart.py               CartItem model (user_id + product_id + quantity)
  tag.py                Tag + ProductTag link model (many-to-many with Product)
routers/
  auth.py               Register, login, logout, get_current_user
  products.py           Browse (search + price + tag filter + pagination), my products, new (with tags), detail, delete
  cart.py               Cart page, add/remove items, place order
  orders.py             My orders page (paginated)
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
  orders_my.html        Placed orders with items, totals, and pagination
static/
  css/app.css           All styles (CSS variables + component classes)
tests/
  conftest.py           Pytest fixtures: test DB, client, session
  test_browse.py        Browse: search (q), price filter, validation, pagination
  test_tags.py          Tags: create/normalize, browse tag filter, detail display
  test_images.py        Images: create with URL, validation, detail render + empty state
  test_validation.py    Auth + product input validation, cart quantity clamping
  test_checkout_flow.py Cart → order checkout flow and login requirement
  test_cart.py          DB cart persistence and guest session cart
  test_orders.py        Orders list pagination
  test_authorization.py Authorization matrix + negative cases (maps to user stories)
docs/
  user-stories.md       User stories + acceptance criteria, mapped to tests
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
- **Product:** `id`, `name`, `description`, `price_cents` (ZAR cents as int), `image_url` (optional, validated http/https), `seller_id` -> User, `created_at`. Uses `Relationship()` to load seller and tags.
- **Order + OrderItem:** Order has `buyer_id` -> User. OrderItem has `order_id`, `product_id`, `quantity`, `unit_price_cents` (cents at time of purchase). One-to-many relationship via `back_populates`.
- **CartItem:** `user_id` + `product_id` + `quantity`; one row per product per signed-in user. Guests use a session cookie cart until login/register merges it into the DB.
- **Tag + ProductTag:** `Tag` has a unique, indexed `name` (stored normalized — lowercased and trimmed). `ProductTag` is the many-to-many link table; `Product.tags` loads tags via `link_model`.

### 4. `routers/auth.py`

- Register (GET/POST), login (GET/POST), logout (GET).
- Passwords hashed with bcrypt; session cookie stores `user_id`.
- `get_current_user()` dependency: reads session, returns User or None.

### 5. `routers/products.py`

- **Browse (GET `/products`):** search by name/description (`q`), filter by `min_price`/`max_price` (rand, converted to cents) and by `tag`. Validates min <= max. Paginated at 12 per page (`page` query param) with prev/next links that preserve active filters.
- **My products (GET `/products/my`):** seller's own products.
- **New product (GET/POST `/products/new`):** form; price entered in rand, stored as cents; optional comma-separated tags and an optional validated `image_url`.
- **Detail (GET `/products/{id}`):** full view, "Add to cart", "Delete" if owner.
- **Delete:** POST route (form) + DELETE route (HTMX).

### 6. `routers/cart.py`

- Cart stored in the DB for signed-in users; guests use the session cookie until login/register merges items into the DB.
- View cart, add/remove items, place order (converts cart → Order + OrderItems in DB; payment is offline/out of scope for v1).

### 7. `routers/orders.py`

- My orders: lists logged-in user's orders with items and totals. Paginated at 12 per page (`page` query param) with prev/next links and a result count.

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
- Pagination on browse (12 per page) with prev/next links, a result count, and filters preserved across pages.
- Tags: products carry many-to-many tags (entered comma-separated on create, normalized + deduped); browse filters by tag via clickable chips.
- Product images: optional `image_url` (validated http/https) with thumbnails on browse, a full image on detail, and a "No image" empty state.
- DB-backed cart for signed-in users (survives logout/login); guests keep a session cart until they sign in.
- UI: CSS-variable theme in `static/css/app.css`; responsive nav with grouped links (mobile stacks without JS).
- Checkout flow (cart → order + order items; no payment gateway) and "My orders" (paginated at 12 per page).
- Input validation on auth and product creation paths.
- Authorization enforced: only owners delete their listings; orders are private to the buyer; seller-only pages require sign-in.
- Alembic migrations managing schema.
- Behaviour captured as [user stories](docs/user-stories.md), each mapped to tests.
- Tests for browse, validation, pagination, tags, images, authorization, checkout flow, cart persistence, and orders pagination (40 passing).

Latest local test run:

```bash
.venv/bin/pytest tests/ -q
# 40 passed
```

## Remaining work (real technical debt)

The original MVP debt list (orders pagination, DB-backed cart, UI polish) is cleared. The
UI is now consistent and responsive: a single CSS-variable theme in `static/css/app.css`
`:root`, a responsive nav, a shared `.field` input class, and product rows that stack on
narrow screens. Further polish should be driven by real usage, not added speculatively.

> Note: product images use a remote `image_url` (no upload/storage). File uploads remain out of scope for the MVP.

## Suggested next milestones (small and learnable)

No urgent debt remains. Good next slices, only when there's a real need:

- **Dark theme** — add a `[data-theme="dark"]` block overriding the `:root` tokens (no component changes needed).
- **Order detail page** — a per-order view if buyers want a permalink/receipt.

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
