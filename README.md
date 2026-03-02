# PoorDad

A small marketplace (Etsy / Moksi-style) for South Africa.

## Aim

PoorDad is a database-centric web app aiming to be a simple marketplace where buyers can browse and purchase and sellers can list products. The focus is South African use, inspired by platforms like Moksi. The project is scoped as a solo MVP: core marketplace features first, with room to grow (payments, search, reviews) later.

## Tech stack

| Layer | Choice |
|-------|--------|
| **Backend** | FastAPI |
| **Templates** | Jinja2 |
| **Interactivity** | HTMX (to be added) |
| **ORM** | SQLModel |
| **Database** | SQLite (dev/MVP), Postgres later (e.g. Supabase) |
| **Auth** | Sessions (Starlette) + bcrypt |
| **Server** | Uvicorn (dev), Gunicorn + Uvicorn (prod) |
| **Config** | Environment variables (`DATABASE_URL`, `SECRET_KEY`) |
| **Frontend styling** | Optional (e.g. Tailwind); to be added |

## Getting started

**Prerequisites:** Python 3.11+

**Set up:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Run the app:**

```bash
uvicorn main:app --reload
```

**Open:** [http://localhost:8000](http://localhost:8000)

## Project structure

```
main.py            FastAPI app, middleware, home route
database.py        SQLite engine, session factory, table creation
models/
  user.py          User model (SQLModel)
routers/
  auth.py          Register, login, logout routes
templates/
  base.html        Shared layout (nav, flash messages)
  home.html        Landing page
  register.html    Registration form
  login.html       Login form
static/            CSS, JS, HTMX (planned)
requirements.txt   Python dependencies
```

## What was built so far (walkthrough)

This section exists so you can review what was set up and why. Go through each file
at your own pace.

### 1. `database.py` — database connection

- Creates a SQLite database file (`poordad.db`) using SQLAlchemy's `create_engine`.
- `get_session()` is a FastAPI **dependency** — every route that needs the database
  receives a session automatically. FastAPI calls this function, gives the route the
  session, and closes it when the request is done.
- `create_db_and_tables()` runs `CREATE TABLE` for every model SQLModel knows about.
  It is called once when the app starts (see `main.py` lifespan).

### 2. `models/user.py` — the User table

- A single SQLModel class that maps to a `user` table in SQLite.
- Fields: `id` (auto-increment primary key), `email` (unique, indexed), `name`,
  `password_hash`, `created_at`.
- `table=True` tells SQLModel this is a real database table (not just a data shape).

### 3. `routers/auth.py` — register, login, logout

- **Register (GET):** shows the form.
- **Register (POST):** reads form fields (`name`, `email`, `password`), checks if
  email already exists, hashes the password with bcrypt, inserts a new User row,
  stores `user_id` in the session cookie, then redirects to `/`.
- **Login (GET):** shows the form.
- **Login (POST):** looks up the user by email, verifies the password hash, sets
  the session, redirects to `/`.
- **Logout (GET):** clears the session cookie, redirects to `/`.
- **`get_current_user()`:** a FastAPI dependency used by any route that needs to
  know who is logged in. Reads `user_id` from the session cookie, looks up the
  user in the DB, returns the User object (or `None` if not logged in).

### 4. `main.py` — app entry point

- **Lifespan:** `create_db_and_tables()` runs on startup so the DB is ready.
- **SessionMiddleware:** enables signed cookies so `request.session` works
  (this is how login state is stored between requests).
- **Router:** `auth_router` is mounted so `/auth/register`, `/auth/login`, and
  `/auth/logout` all work.
- **Home route (`/`):** uses `get_current_user` as a dependency so the template
  can show the user's name or register/login links.

### 5. Templates (Jinja2)

- **`base.html`:** shared HTML shell. Nav bar shows Login/Register when logged out,
  or the user's name + Logout when logged in. Also has a flash-message block for
  errors/success messages. All other templates extend this.
- **`home.html`**, **`register.html`**, **`login.html`:** extend `base.html` and
  fill in the `{% block content %}` with their own HTML.

### 6. Key concepts to understand

- **FastAPI dependencies (`Depends`):** functions that FastAPI calls for you and
  injects into route handlers. `get_session` and `get_current_user` are both
  dependencies.
- **Session cookie:** a signed cookie (via `itsdangerous`) that stores `user_id`.
  The server sets it on login, reads it on every request, clears it on logout.
- **bcrypt:** a one-way hash for passwords. You never store the password itself;
  on login you hash the input and compare.
- **SQLModel:** combines Pydantic (data validation) and SQLAlchemy (database ORM)
  into one class. `User` is both a DB table and a data model.
- **303 redirect:** after a POST (register/login), the server responds with a
  redirect so the browser does a GET to the next page (prevents double-submit on
  refresh).

### Next steps

- Products model + seller CRUD (create, list, browse)
- HTMX for interactive bits (e.g. delete product without full page reload)
- Styling (Tailwind or similar)
