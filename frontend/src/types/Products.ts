export type IngredientType = 'base' | 'sauce' | 'meat' | 'extras'

export type Step = IngredientType | 'summary'

export interface Ingredient {
    ingredient_id: number
    name: string
    type: IngredientType
    image_url?: string
    price: number
    color?: string
    required?: boolean
    description?: string
    grams?: number
}

export interface Category {
    category_id: number
    name: string
}

export type PriceMode = 'per_day' | 'flat'

export interface Addon {
    product_id: number
    name: string
    price: number
    price_mode: PriceMode
    image_url?: string | null
    // 0 = optional add-on; >0 = kit component pre-included with this quantity.
    default_quantity: number
}

export interface Product {
    product_id: number
    name: string
    description: string
    price: number
    // Catalog display price: `price` plus pre-included kit components' price.
    // Equals `price` for a normal product. Use for catalog cards; use `price`
    // (raw) for billing math (previewLineTotalWithAddons etc.).
    display_price?: number
    image_url: string | null
    image_urls: string[]
    proteins?: number
    fats?: number
    carbohydrates?: number
    calories?: number
    is_custom?: boolean
    is_addon?: boolean
    price_mode?: PriceMode
    ingredients?: Ingredient[]
    category: Category
}
