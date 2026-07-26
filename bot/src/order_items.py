"""Shared item-list formatting for bot messages (admin cards, receipt caption,
client order-created message) — grouped by parent/add-on, compact "15к" price
notation. Mirrors frontend/src/utils/price.ts's formatPriceK for consistency
between the bot and the Mini App profile.
"""

import html
import re

_WHITESPACE_RUN = re.compile(r"\s+")


def format_price_k(amount: float | int) -> str:
    n = int(round(amount))
    if abs(n) >= 1_000_000:
        return f"{n:,}".replace(",", " ")
    return f"{round(n / 1000)}к"


def _clean_name(name: str) -> str:
    # Some product names carry an embedded newline (DB data quirk, e.g.
    # "Кастрюля 3.6\r\nJeep") — collapse ANY run of whitespace (space, \r, \n,
    # \r\n together) to a single space for compact list rendering, then escape
    # (parse_mode=HTML — this is client-controlled-ish data via the product
    # catalog, escape defensively regardless).
    collapsed = _WHITESPACE_RUN.sub(" ", str(name)).strip()
    return html.escape(collapsed)


def format_order_items(items: list[dict]) -> str:
    """Group items by parent_order_item_id: a container/parent with add-ons
    renders as a header line (name, plus its own qty/price if it costs
    something) followed by its children indented underneath; a standalone item
    (no add-ons) is just a flat bullet line. Returns the joined text (no
    trailing newline).
    """
    children: dict[int, list[dict]] = {}
    for item in items:
        parent_id = item.get("parent_order_item_id")
        if parent_id is not None:
            children.setdefault(parent_id, []).append(item)

    lines: list[str] = []
    for item in items:
        if item.get("parent_order_item_id") is not None:
            continue  # rendered under its parent below
        name = _clean_name(item.get("product_name") or f"Товар #{item['product_id']}")
        kids = children.get(item.get("order_item_id"))
        if kids:
            own_total = item["unit_price"] * item["quantity"]
            header = name if own_total == 0 else f"{name} ×{item['quantity']} - {format_price_k(own_total)}"
            lines.append(header)
            for child in kids:
                child_name = _clean_name(child.get("product_name") or f"Товар #{child['product_id']}")
                child_total = child["unit_price"] * child["quantity"]
                lines.append(f"   • {child_name} ×{child['quantity']} - {format_price_k(child_total)}")
        else:
            total = item["unit_price"] * item["quantity"]
            lines.append(f"  • {name} ×{item['quantity']} - {format_price_k(total)}")
    return "\n".join(lines)
