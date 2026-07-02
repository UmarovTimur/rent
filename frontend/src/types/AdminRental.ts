import { OrderStatus } from '@/types/Basket'

export interface RentalOrderItemBrief {
    order_item_id: number
    product_id: number
    product_name: string | null
    quantity: number
    unit_price: number
    rental_start: string | null
    rental_end: string | null
}

export interface RentalOrderSummary {
    order_id: number
    telegram_id: number
    first_name: string | null
    username: string | null
    phone: string | null
    status: OrderStatus
    rental_start: string
    rental_end: string
    total_price: number
    items: RentalOrderItemBrief[]
}

export interface RentalOrderDetail extends RentalOrderSummary {
    order_date: string
    payment_option: string
    address: string | null
    comment: string | null
    allowed_transitions: OrderStatus[]
}
