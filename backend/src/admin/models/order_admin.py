from sqladmin import ModelView

from src.clients.database.models.order import Order, OrderItem


class OrderAdmin(ModelView, model=Order):
    column_list = [
        Order.order_id,
        Order.status,
        Order.first_name,
        Order.phone,
        Order.address,
        Order.total_price,
        Order.payment_option,
        Order.order_date,
        Order.comment,
    ]
    column_editable_list = [Order.status]
    form_columns = [
        Order.status,
        Order.first_name,
        Order.phone,
        Order.address,
        Order.payment_option,
        Order.comment,
        Order.discount,
    ]
    name_plural = "Orders"


class OrderItemAdmin(ModelView, model=OrderItem):
    # Ordered so staff fulfilling rentals see, left to right: who, what, how many,
    # and when to hand it over / take it back — sorted by pickup time by default.
    column_list = [
        OrderItem.order_item_id,
        OrderItem.order,
        OrderItem.product,
        OrderItem.quantity,
        OrderItem.rental_start,
        OrderItem.rental_end,
        OrderItem.unit_price,
    ]
    column_default_sort = [(OrderItem.rental_start, False)]
    name_plural = "Order Items"
