import axios from 'axios'
import API_BASE_URL from '@/config'
import { Basket, AddonSelection } from '@/types/Basket'

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
        _userId: number,
        productId: number,
        quantity: number = 1,
        rentalStart?: string,
        rentalEnd?: string,
        addons: AddonSelection[] = []
    ): Promise<void> {
        await axios.post(
            `${API_BASE_URL}api/v1/basket/add_item`,
            {
                product_id: productId,
                quantity,
                rental_start: rentalStart,
                rental_end: rentalEnd,
                addons,
            }
        )
    },

    // Sets the trip window and atomically migrates existing items into it on the
    // server, returning the updated basket (replaces client-side reconciliation).
    async setBasketDatesAndMigrate(
        _userId: number,
        rentalStart: string,
        rentalEnd: string
    ): Promise<Basket> {
        const response = await axios.put<Basket>(
            `${API_BASE_URL}api/v1/basket/dates`,
            {
                rental_start: rentalStart,
                rental_end: rentalEnd,
            }
        )
        return response.data
    },

    async getBasket(_userId: number): Promise<Basket | null> {
        try {
            const response = await axios.get<Basket>(
                `${API_BASE_URL}api/v1/basket/`
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
        try {
            await axios.delete(
                `${API_BASE_URL}api/v1/basket/remove_item/${basketItemId}`
            )
        } catch (error) {
            // Idempotent: a 404 means the item is already gone (e.g. removed by a
            // concurrent date migration) — treat that as success.
            if (axios.isAxiosError(error) && error.response?.status === 404) return
            throw error
        }
    },
}
