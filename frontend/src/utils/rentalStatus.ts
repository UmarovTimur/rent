import { OrderStatus } from '@/types/Basket'

export interface RentalStatusMeta {
    color: string
    label: string
    // Chakra scale step used for the calendar event color; defaults to 500.
    calendarShade?: number
}

export const RENTAL_STATUS_MAP: Record<OrderStatus, RentalStatusMeta> = {
    created: { color: 'gray', label: 'Создан' },
    in_progress: { color: 'blue', label: 'В процессе' },
    taken: { color: 'orange', label: 'Отдан' },
    paused: { color: 'purple', label: 'Пауза' },
    // Successful outcome — client returned the gear, slot released.
    returned: { color: 'green', label: 'Возвращён' },
    // Unsuccessful outcome — closed without a return (no revenue), kept distinct from "returned" for stats.
    completed: { color: 'red', label: 'Закрыт (неуспешно)' },
    canceled: { color: 'red', label: 'Отменён', calendarShade: 700 },
}

export const getRentalStatusMeta = (status: OrderStatus): RentalStatusMeta =>
    RENTAL_STATUS_MAP[status] ?? { color: 'gray', label: status }

// FullCalendar needs real CSS colors, not Chakra palette names. Resolve through the
// theme's CSS variables so calendar events use the same standard Chakra scale as the badges.
export const getRentalStatusCalendarColor = (status: OrderStatus): string => {
    const meta = getRentalStatusMeta(status)
    return `var(--chakra-colors-${meta.color}-${meta.calendarShade ?? 500})`
}
