import axios from 'axios'
import API_BASE_URL from '@/config'

export type RentalCalendarSlot = {
    slot_start: string
    slot_end: string
    available_quantity: number
    is_available: boolean
    is_closed: boolean
}

export type RentalCalendarResponse = {
    product_id: number
    rental_id: number
    total_quantity: number
    slot_duration_minutes: number
    range_start: string
    range_end: string
    slots: RentalCalendarSlot[]
}

export const RentalService = {
    async getProductCalendar(
        productId: number,
        dateFromIso: string,
        dateToIso: string
    ): Promise<RentalCalendarResponse> {
        const response = await axios.get<RentalCalendarResponse>(
            `${API_BASE_URL}api/v1/rental/product/${productId}/calendar`,
            {
                params: {
                    date_from: dateFromIso,
                    date_to: dateToIso,
                },
            }
        )
        return response.data
    },
}
