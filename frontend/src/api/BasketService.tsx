import axios from 'axios'
import API_BASE_URL from '@/config'
import { Basket } from '@/types/Basket'

const isBasketNotFoundError = (error: unknown): boolean => {
    if (!axios.isAxiosError(error)) return false

    const status = error.response?.status
    if (status !== 400 && status !== 404) return false

    const responseData = error.response?.data as
        | { detail?: unknown; message?: unknown }
        | undefined
    const detail =
        typeof responseData?.detail === 'string'
            ? responseData.detail
            : typeof responseData?.message === 'string'
              ? responseData.message
              : ''

    return detail.toLowerCase().includes('basket not found')
}

export const BasketService = {
    async addItem(
        userId: number,
        productId: number,
        quantity: number = 1,
        rentalStart?: string,
        rentalEnd?: string
    ): Promise<void> {
        await axios.post(
            `${API_BASE_URL}api/v1/basket/add_item?user_id=${userId}`,
            {
                product_id: productId,
                quantity,
                rental_start: rentalStart,
                rental_end: rentalEnd,
            }
        )
    },

    async getBasket(userId: number): Promise<Basket | null> {
        try {
            const response = await axios.get<Basket>(
                `${API_BASE_URL}api/v1/basket/${userId}`
            )
            return response.data
        } catch (error) {
            // New users may not have a basket yet; treat it as an empty basket state.
            if (isBasketNotFoundError(error)) {
                return null
            }
            throw error
        }
    },

    async changeQuantity(
        basketItemId: number,
        quantity: number
    ): Promise<void> {
        await axios.post(`${API_BASE_URL}api/v1/basket/change_quantity`, {
            basket_item_id: basketItemId,
            quantity,
        })
    },

    async removeItem(basketItemId: number): Promise<void> {
        await axios.delete(
            `${API_BASE_URL}api/v1/basket/remove_item/${basketItemId}`
        )
    },
}
