export interface BasketItem {
    basket_item_id: number
    product_id: number
    quantity: number
    rental_start?: string | null
    rental_end?: string | null
}

export interface Basket {
    basket_id: number
    user_id: number
    items: BasketItem[]
    total_price: number
}

export type OrderStatus = 'created' | 'in_progress' | 'completed' | 'canceled' | 'taken'

export type PaymentOption = 'card' | 'cash'

export interface Order {
    order_id: number
    basket_id: number
    payment_option: PaymentOption
    comment: string
    status: OrderStatus
    first_name: string
    address: string
    phone: string
    created_at: string
}
