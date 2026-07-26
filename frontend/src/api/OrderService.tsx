import axios from 'axios'
import API_BASE_URL from '@/config'
import { Basket } from '@/types/Basket'

export const OrderService = {
    createOrder: async (
        _userId: number,
        orderData: {
            basket_id: number
            payment_option: 'card' | 'cash'
            comment: string
            first_name: string
            address: string
            phone: string
            use_coins: boolean
        }
    ): Promise<Basket> => {
        const response = await axios.post<Basket>(
            `${API_BASE_URL}api/v1/order/`,
            orderData
        )
        return response.data
    },
}
