import { useCallback, useEffect, useRef, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import listPlugin from '@fullcalendar/list'
import interactionPlugin from '@fullcalendar/interaction'
import type { EventClickArg, EventInput, EventSourceFuncArg } from '@fullcalendar/core'
import { Badge, Box, Flex } from '@chakra-ui/react'
import { useIsDesktop } from '@/hooks/useIsDesktop'
import { AdminRentalService } from '@/api/AdminRentalService'
import { RentalOrderSummary } from '@/types/AdminRental'
import { OrderStatus } from '@/types/Basket'
import { RENTAL_STATUS_MAP, getRentalStatusCalendarColor } from '@/utils/rentalStatus'
import MotionDrawer from '@/assets/MotionDrawer.tsx'
import RentalDetailDrawer from '@/assets/admin/RentalDetailDrawer'

const toEvent = (rental: RentalOrderSummary): EventInput => {
    const color = getRentalStatusCalendarColor(rental.status)
    const client = rental.first_name || rental.username || `ID ${rental.telegram_id}`
    return {
        id: String(rental.order_id),
        title: `#${rental.order_id} ${client}`,
        start: rental.rental_start,
        end: rental.rental_end,
        backgroundColor: color,
        borderColor: color,
    }
}

const ALL_STATUSES = Object.keys(RENTAL_STATUS_MAP) as OrderStatus[]

export default function AdminCalendar() {
    const isDesktop = useIsDesktop()
    const calendarRef = useRef<FullCalendar>(null)
    const drawerTriggerRef = useRef<HTMLButtonElement>(null)
    const [selectedStatuses, setSelectedStatuses] = useState<OrderStatus[]>([])
    const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null)

    useEffect(() => {
        calendarRef.current?.getApi().changeView(isDesktop ? 'dayGridMonth' : 'listWeek')
    }, [isDesktop])

    const toggleStatus = (status: OrderStatus) => {
        setSelectedStatuses((current) =>
            current.includes(status) ? current.filter((s) => s !== status) : [...current, status]
        )
    }

    // Stable identity between renders (FullCalendar refetches whenever the `events` prop
    // changes, so an inline function would make every event flash on unrelated re-renders,
    // e.g. when opening the detail drawer). Filtering is client-side: an empty selection
    // shows everything.
    const fetchEvents = useCallback(
        (
            fetchInfo: EventSourceFuncArg,
            successCallback: (events: EventInput[]) => void,
            failureCallback: (error: Error) => void
        ) => {
            AdminRentalService.getRentals(fetchInfo.startStr, fetchInfo.endStr)
                .then((rentals) => {
                    const visible =
                        selectedStatuses.length > 0
                            ? rentals.filter((rental) => selectedStatuses.includes(rental.status))
                            : rentals
                    successCallback(visible.map(toEvent))
                })
                .catch((error) => {
                    console.error('Failed to load rentals:', error)
                    failureCallback(error)
                })
        },
        [selectedStatuses]
    )

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
                    const active = selectedStatuses.includes(status)
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
                            onClick={() => toggleStatus(status)}
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
                events={fetchEvents}
            />

            <MotionDrawer trigger={<button ref={drawerTriggerRef} style={{ display: 'none' }} />}>
                {selectedOrderId !== null && (
                    <RentalDetailDrawer orderId={selectedOrderId} onStatusChanged={refetch} />
                )}
            </MotionDrawer>
        </Box>
    )
}
