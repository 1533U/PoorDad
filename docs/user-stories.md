# User stories

The marketplace behaviour, framed as user stories with acceptance criteria and
the tests that lock each one in. IDs are referenced from test docstrings so the
mapping stays honest. Keep this in sync when behaviour changes (see the
"keep it clean" working agreement).

## Accounts & auth

### ACC-1 — Register and sign in
**As** a visitor, **I want** to register with name/email/password **so that** I can buy and sell.
- Valid details create an account and log me in (303 → `/`).
- Email is normalized (trimmed, lowercased) and must be unique.
- Invalid input (blank name, bad email, short password) is rejected with a message.

_Tests:_ `test_validation.py::test_register_rejects_blank_name`,
`test_validation.py::test_register_normalizes_email`,
`test_authorization.py::test_duplicate_email_is_rejected`.

### ACC-2 — Sign-in is guarded
**As** a registered user, **I want** wrong credentials rejected **so that** my account is safe.
- Wrong password does not log me in and shows "Invalid email or password."

_Tests:_ `test_authorization.py::test_login_with_wrong_password_fails`.

## Listings

### LIST-1 — Create a listing
**As** a signed-in user, **I want** to list a product (name, description, price, optional tags + image) **so that** others can buy it.
- Price entered in rand, stored as cents; must be > 0.
- Tags are normalized + deduped; `image_url` must be http/https if given.

_Tests:_ `test_validation.py::test_create_product_rejects_zero_price`,
`test_tags.py::*`, `test_images.py::*`.

### LIST-2 — Only owners delete their listings
**As** a seller, **I want** only I can delete my products **so that** others cannot tamper with my shop.
- Owner can delete their own product (form POST and HTMX DELETE).
- A different user deleting my product gets 404 and the product survives.
- Deleting a missing product returns 404.
- A guest using the HTMX delete endpoint gets 401.

_Tests:_ `test_authorization.py::test_owner_can_delete_own_product`,
`test_authorization.py::test_other_user_cannot_delete_product_via_post`,
`test_authorization.py::test_other_user_cannot_delete_product_via_htmx`,
`test_authorization.py::test_delete_missing_product_returns_404`,
`test_authorization.py::test_guest_htmx_delete_is_unauthorized`.

## Browse & discovery

### BROWSE-1 — Find products
**As** a visitor, **I want** to browse, search, filter by price/tag, and page through results.

_Tests:_ `test_browse.py::*`, `test_tags.py::test_browse_filters_by_tag`.

## Seller-only areas

### GUARD-1 — Seller pages require sign-in
**As** the system, **I want** seller-only routes to require auth **so that** guests are redirected.
- `GET /products/my`, `GET /products/new`, and `GET /orders` redirect guests to login (303).
- `POST /products/new` by a guest does not create a product (303 → login).

_Tests:_ `test_authorization.py::test_guest_redirected_from_seller_pages`,
`test_authorization.py::test_guest_cannot_create_product`.

## Cart & checkout

### CART-1 — Build a cart and check out
**As** a buyer, **I want** to add to a session cart and place an order **so that** I have an order record.
- Quantities are clamped to a sane range.
- Placing an order requires sign-in; an empty cart places nothing.
- After checkout the cart is cleared.

_Tests:_ `test_validation.py::test_cart_*`,
`test_checkout_flow.py::test_place_order_requires_login`,
`test_checkout_flow.py::test_checkout_flow_places_order_and_clears_cart`,
`test_authorization.py::test_place_order_with_empty_cart_creates_nothing`.

### CART-2 — Orders are private
**As** a buyer, **I want** to see only my own orders **so that** my purchases stay private.

_Tests:_ `test_authorization.py::test_orders_are_scoped_to_the_logged_in_user`.
