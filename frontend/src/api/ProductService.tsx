import axios from 'axios'
import { Category, Product, Ingredient } from '@/types/Products'
import API_BASE_URL from '@/config'

let cachedProducts: Product[] | null = null
let cachedCategories: Category[] | null = null
let cachedIngredients: Ingredient[] | null = []

export const ProductService = {
    fetchAllProducts: async (): Promise<Product[]> => {
        if (cachedProducts) return cachedProducts

        try {
            const response = await axios.get<Product[]>(
                `${API_BASE_URL}api/v1/product/`
            )
            cachedProducts = response.data
            return cachedProducts
        } catch (error) {
            console.error('Error fetching products:', error)
            throw error
        }
    },

    getUniqueProducts: (): Product[] => {
        if (!cachedProducts) throw new Error('Data not loaded')
        return cachedProducts
    },

    getProductsByCategory: (category: string): Product[] => {
        return ProductService.getUniqueProducts().filter(
            (product) => product.category.name === category
        )
    },

    fetchCategories: async (): Promise<Category[]> => {
        if (cachedCategories) return cachedCategories

        try {
            const response = await axios.get<Category[]>(
                `${API_BASE_URL}api/v1/category/`
            )
            cachedCategories = response.data
            return cachedCategories
        } catch (error) {
            console.error('Error fetching categories:', error)
            throw error
        }
    },

    getProductById: (productId: number): Product | null => {
        if (!cachedProducts) return null
        return (
            cachedProducts.find((product) => product.product_id === productId) ??
            null
        )
    },

    createProduct: async (productData: {
        name: string
        description: string
        category_id: number
        price: number
        ingredient_ids?: number[]
    }): Promise<Product> => {
        try {
            const formData = new FormData()

            const productJson = JSON.stringify({
                name: productData.name,
                description: productData.description,
                category_id: productData.category_id,
                price: productData.price,
            })

            formData.append('product', productJson)

            const response = await axios.post<Product>(
                `${API_BASE_URL}api/v1/product/`,
                formData,
                {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                        Accept: 'application/json',
                    },
                }
            )
            return response.data
        } catch (error) {
            console.error('Error creating product:', error)
            if (axios.isAxiosError(error)) {
                console.error('Server response:', {
                    status: error.response?.status,
                    data: error.response?.data,
                    config: error.config,
                })
            }
            throw error
        }
    },

    resetCache: () => {
        cachedProducts = null
        cachedCategories = null
        cachedIngredients = []
    },

    // Legacy constructor API is disabled in rental-only mode.
    fetchAllIngredients: async (): Promise<Ingredient[]> => {
        return cachedIngredients ?? []
    },

    getCachedIngredients: (): Ingredient[] | null => {
        return cachedIngredients
    },
}
