export interface BasketItemAddon {
    basket_item_id: number
    product_id: number
    name: string
    price: number
    price_mode: 'per_day' | 'flat'
    quantity: number
}

export interface BasketItem {
    basket_item_id: number
    product_id: number
    quantity: number
    rental_start?: string | null
    rental_end?: string | null
    addons?: BasketItemAddon[]
}

export interface Basket {
    basket_id: number
    user_id: number
    rental_start?: string | null
    rental_end?: string | null
    items: BasketItem[]
    total_price: number
}

export type OrderStatus = 'created' | 'in_progress' | 'completed' | 'canceled' | 'taken' | 'paused'

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
