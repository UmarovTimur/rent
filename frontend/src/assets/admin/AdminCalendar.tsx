import { useEffect, useRef, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import listPlugin from '@fullcalendar/list'
import interactionPlugin from '@fullcalendar/interaction'
import type { EventClickArg, EventInput } from '@fullcalendar/core'
import { Badge, Box, Flex } from '@chakra-ui/react'
import { useIsDesktop } from '@/hooks/useIsDesktop'
import { AdminRentalService } from '@/api/AdminRentalService'
import { RentalOrderSummary } from '@/types/AdminRental'
import { OrderStatus } from '@/types/Basket'
import { RENTAL_STATUS_MAP, getRentalStatusMeta } from '@/utils/rentalStatus'
import MotionDrawer from '@/assets/MotionDrawer.tsx'
import RentalDetailDrawer from '@/assets/admin/RentalDetailDrawer'

const toEvent = (rental: RentalOrderSummary): EventInput => {
    const meta = getRentalStatusMeta(rental.status)
    const client = rental.first_name || rental.username || `ID ${rental.telegram_id}`
    return {
        id: String(rental.order_id),
        title: `#${rental.order_id} ${client}`,
        start: rental.rental_start,
        end: rental.rental_end,
        backgroundColor: meta.color,
        borderColor: meta.color,
    }
}

const ALL_STATUSES = Object.keys(RENTAL_STATUS_MAP) as OrderStatus[]

export default function AdminCalendar() {
    const isDesktop = useIsDesktop()
    const calendarRef = useRef<FullCalendar>(null)
    const drawerTriggerRef = useRef<HTMLButtonElement>(null)
    const [statusFilter, setStatusFilter] = useState<OrderStatus | null>(null)
    const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null)

    useEffect(() => {
        calendarRef.current?.getApi().changeView(isDesktop ? 'dayGridMonth' : 'listWeek')
    }, [isDesktop])

    useEffect(() => {
        calendarRef.current?.getApi().refetchEvents()
    }, [statusFilter])

    const handleEventClick = (info: EventClickArg) => {
        setSelectedOrderId(Number(info.event.id))
        drawerTriggerRef.current?.click()
    }

    const refetch = () => calendarRef.current?.getApi().refetchEvents()

    return (
        <Box>
            <Flex gap="2" wrap="wrap" mb="4">
                {ALL_STATUSES.map((status) => {
                    const meta = RENTAL_STATUS_MAP[status]
                    const active = statusFilter === status
                    return (
                        <Badge
                            key={status}
                            colorPalette={meta.color}
                            variant={active ? 'solid' : 'outline'}
                            cursor="pointer"
                            px="3"
                            py="2"
                            rounded="full"
                            fontSize="sm"
                            onClick={() => setStatusFilter(active ? null : status)}
                        >
                            {meta.label}
                        </Badge>
                    )
                })}
            </Flex>

            <FullCalendar
                ref={calendarRef}
                plugins={[dayGridPlugin, listPlugin, interactionPlugin]}
                initialView={isDesktop ? 'dayGridMonth' : 'listWeek'}
                headerToolbar={{ left: 'prev,next today', center: 'title', right: '' }}
                height="auto"
                locale="ru"
                firstDay={1}
                eventClick={handleEventClick}
                events={(fetchInfo, successCallback, failureCallback) => {
                    AdminRentalService.getRentals(fetchInfo.startStr, fetchInfo.endStr, statusFilter ?? undefined)
                        .then((rentals) => successCallback(rentals.map(toEvent)))
                        .catch((error) => {
                            console.error('Failed to load rentals:', error)
                            failureCallback(error)
                        })
                }}
            />

            <MotionDrawer trigger={<button ref={drawerTriggerRef} style={{ display: 'none' }} />}>
                {selectedOrderId !== null && (
                    <RentalDetailDrawer orderId={selectedOrderId} onStatusChanged={refetch} />
                )}
            </MotionDrawer>
        </Box>
    )
}
