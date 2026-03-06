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

export interface Product {
    product_id: number
    name: string
    description: string
    price: number
    image_url: string | null
    proteins?: number
    fats?: number
    carbohydrates?: number
    calories?: number
    is_custom?: boolean
    ingredients?: Ingredient[]
    category: Category
}
