import { OrderStatus } from '@/types/Basket'

export interface RentalStatusMeta {
    color: string
    label: string
}

export const RENTAL_STATUS_MAP: Record<OrderStatus, RentalStatusMeta> = {
    created: { color: 'gray', label: 'Создан' },
    in_progress: { color: 'blue', label: 'В процессе' },
    taken: { color: 'orange', label: 'Выдан' },
    paused: { color: 'purple', label: 'Пауза' },
    completed: { color: 'green', label: 'Завершён' },
    canceled: { color: 'red', label: 'Отменён' },
}

export const getRentalStatusMeta = (status: OrderStatus): RentalStatusMeta =>
    RENTAL_STATUS_MAP[status] ?? { color: 'gray', label: status }
