from fastapi import Request

CART_KEY = "cart"


def get_cart(request: Request) -> list[dict]:
    return request.session.get(CART_KEY) or []


def set_cart(request: Request, items: list[dict]) -> None:
    request.session[CART_KEY] = items


def cart_count(request: Request) -> int:
    return sum(item.get("quantity", 0) for item in get_cart(request))
