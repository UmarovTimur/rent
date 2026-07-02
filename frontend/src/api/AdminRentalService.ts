import adminClient from '@/api/adminClient'
import { RentalOrderDetail, RentalOrderSummary } from '@/types/AdminRental'
import { OrderStatus } from '@/types/Basket'

export const AdminRentalService = {
    async getRentals(dateFromIso: string, dateToIso: string, status?: OrderStatus): Promise<RentalOrderSummary[]> {
        const response = await adminClient.get<RentalOrderSummary[]>('api/v1/admin/rentals', {
            params: {
                date_from: dateFromIso,
                date_to: dateToIso,
                status,
            },
        })
        return response.data
    },

    async getRental(orderId: number): Promise<RentalOrderDetail> {
        const response = await adminClient.get<RentalOrderDetail>(`api/v1/admin/rentals/${orderId}`)
        return response.data
    },

    async updateStatus(orderId: number, status: OrderStatus): Promise<void> {
        await adminClient.patch(`api/v1/admin/rentals/${orderId}/status`, { status })
    },
}
