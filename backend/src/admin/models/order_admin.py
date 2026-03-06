from sqladmin import ModelView

from src.clients.database.models.order import Order, OrderItem


class OrderAdmin(ModelView, model=Order):
    column_list = [
        Order.order_id,
        Order.user_id,
        Order.basket_id,
        Order.order_date,
        Order.total_price,
        Order.payment_option,
        Order.comment,
        Order.status,
        Order.first_name,
        Order.address,
        Order.phone,
        Order.discount,
    ]
    name_plural = "Orders"


class OrderItemAdmin(ModelView, model=OrderItem):
    column_list = [
        OrderItem.order_item_id,
        OrderItem.order_id,
        OrderItem.product_id,
        OrderItem.unit_price,
        OrderItem.quantity,
        OrderItem.rental_start,
        OrderItem.rental_end,
    ]
    name_plural = "Order Items"
