from sqladmin import ModelView

from src.clients.database.models.rental import ProductRental, ProductRentalSlot


class ProductRentalAdmin(ModelView, model=ProductRental):
    column_list = [
        ProductRental.rental_id,
        ProductRental.product_id,
        ProductRental.total_quantity,
        ProductRental.slot_duration_minutes,
        ProductRental.min_rental_slots,
        ProductRental.max_rental_slots,
        ProductRental.buffer_before_minutes,
        ProductRental.buffer_after_minutes,
        ProductRental.is_enabled,
        ProductRental.created_at,
        ProductRental.updated_at,
    ]
    name_plural = "Product Rentals"


class ProductRentalSlotAdmin(ModelView, model=ProductRentalSlot):
    column_list = [
        ProductRentalSlot.slot_id,
        ProductRentalSlot.rental_id,
        ProductRentalSlot.slot_start,
        ProductRentalSlot.slot_end,
        ProductRentalSlot.reserved_quantity,
        ProductRentalSlot.blocked_quantity,
        ProductRentalSlot.capacity_override,
        ProductRentalSlot.is_closed,
        ProductRentalSlot.note,
        ProductRentalSlot.created_at,
        ProductRentalSlot.updated_at,
    ]
    name_plural = "Product Rental Slots"
