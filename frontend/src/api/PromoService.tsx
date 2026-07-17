import axios from 'axios'
import API_BASE_URL from '@/config'

export type Promo = {
    promo_id: number
    title?: string | null
    // Ordered media filenames (cover first).
    frames: string[]
}

export const PromoService = {
    async getPromos(): Promise<Promo[]> {
        const response = await axios.get<Promo[]>(`${API_BASE_URL}api/v1/promos/`)
        return response.data
    },
}
