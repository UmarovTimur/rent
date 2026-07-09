from sqladmin import ModelView

from src.clients.database.models.product import ProductAddonLink


class ProductAddonLinkAdmin(ModelView, model=ProductAddonLink):
    """Manage parent → child links: which products are attached to a parent and,
    for kits, how many of each child are pre-included (default_quantity > 0).
    default_quantity = 0 means an optional add-on (opt-in on the parent page)."""

    name = "Kit / add-on link"
    name_plural = "Kit / add-on links"

    column_list = [
        ProductAddonLink.parent,
        ProductAddonLink.addon,
        ProductAddonLink.default_quantity,
        ProductAddonLink.sort_order,
    ]
    column_labels = {
        ProductAddonLink.parent: "Parent",
        ProductAddonLink.addon: "Child / add-on",
        ProductAddonLink.default_quantity: "Default qty (0 = optional)",
        ProductAddonLink.sort_order: "Order",
    }
    form_columns = [
        ProductAddonLink.parent,
        ProductAddonLink.addon,
        ProductAddonLink.default_quantity,
        ProductAddonLink.sort_order,
    ]
    form_ajax_refs = {
        "parent": {"fields": ["name"], "order_by": "name"},
        "addon": {"fields": ["name"], "order_by": "name"},
    }
    form_widget_args = {
        "default_quantity": {"step": 1, "min": 0},
        "sort_order": {"step": 1, "min": 0},
    }
