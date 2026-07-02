import { useCallback, useEffect, useState } from 'react'
import { Badge, Box, Button, Center, CloseButton, Flex, Heading, Spinner, Stack, Text } from '@chakra-ui/react'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import axios from 'axios'
import { useDrawer } from '@/contexts/DrawerContext'
import { AdminRentalService } from '@/api/AdminRentalService'
import { RentalOrderDetail } from '@/types/AdminRental'
import { OrderStatus } from '@/types/Basket'
import { getRentalStatusMeta } from '@/utils/rentalStatus'
import { formatPriceK } from '@/utils/price'
import { toaster } from '@/components/ui/toaster'

const formatDateTime = (value: string) => {
    try {
        return format(new Date(value), 'dd.MM.yyyy HH:mm', { locale: ru })
    } catch {
        return value
    }
}

interface RentalDetailDrawerProps {
    orderId: number
    onStatusChanged: () => void
}

export default function RentalDetailDrawer({ orderId, onStatusChanged }: RentalDetailDrawerProps) {
    const { onClose } = useDrawer()
    const [detail, setDetail] = useState<RentalOrderDetail | null>(null)
    const [loading, setLoading] = useState(true)
    const [updating, setUpdating] = useState(false)

    const fetchDetail = useCallback(async () => {
        setLoading(true)
        try {
            const data = await AdminRentalService.getRental(orderId)
            setDetail(data)
        } catch (error) {
            console.error('Failed to load rental detail:', error)
            setDetail(null)
        } finally {
            setLoading(false)
        }
    }, [orderId])

    useEffect(() => {
        fetchDetail()
    }, [fetchDetail])

    const handleTransition = async (status: OrderStatus) => {
        setUpdating(true)
        try {
            await AdminRentalService.updateStatus(orderId, status)
            toaster.create({ description: 'Статус обновлён', type: 'success' })
            await fetchDetail()
            onStatusChanged()
        } catch (error) {
            let message = 'Не удалось обновить статус'
            if (axios.isAxiosError(error)) {
                const detailMessage = (error.response?.data as { detail?: string } | undefined)?.detail
                if (detailMessage) message = detailMessage
            }
            toaster.create({ description: message, type: 'error' })
        } finally {
            setUpdating(false)
        }
    }

    if (loading) {
        return (
            <Center h="200px">
                <Spinner size="lg" />
            </Center>
        )
    }

    if (!detail) {
        return (
            <Center h="200px">
                <Text>Не удалось загрузить заказ</Text>
            </Center>
        )
    }

    const meta = getRentalStatusMeta(detail.status)

    return (
        <Box p="6" overflowY="auto" h="100%">
            <Flex justify="space-between" align="center" mb="4">
                <Heading size="md">Заказ #{detail.order_id}</Heading>
                <CloseButton onClick={onClose} />
            </Flex>

            <Badge colorPalette={meta.color} size="lg" mb="4">
                {meta.label}
            </Badge>

            <Stack gap="2" mb="6">
                <Text>
                    <b>Клиент:</b> {detail.first_name || detail.username || `ID ${detail.telegram_id}`}
                </Text>
                {detail.phone && (
                    <Text>
                        <b>Телефон:</b> {detail.phone}
                    </Text>
                )}
                {detail.address && (
                    <Text>
                        <b>Адрес:</b> {detail.address}
                    </Text>
                )}
                <Text>
                    <b>Период:</b> {formatDateTime(detail.rental_start)} — {formatDateTime(detail.rental_end)}
                </Text>
                <Text>
                    <b>Сумма:</b> {formatPriceK(detail.total_price)}
                </Text>
                {detail.comment && (
                    <Text>
                        <b>Комментарий:</b> {detail.comment}
                    </Text>
                )}
            </Stack>

            <Heading size="sm" mb="2">
                Позиции
            </Heading>
            <Stack gap="2" mb="6">
                {detail.items.map((item) => (
                    <Box key={item.order_item_id} p="3" borderWidth="1px" rounded="md">
                        <Text fontWeight="bold">
                            {item.product_name || `Товар #${item.product_id}`} × {item.quantity}
                        </Text>
                        {item.rental_start && item.rental_end && (
                            <Text fontSize="sm" color="fg.muted">
                                {formatDateTime(item.rental_start)} — {formatDateTime(item.rental_end)}
                            </Text>
                        )}
                    </Box>
                ))}
            </Stack>

            {detail.allowed_transitions.length > 0 && (
                <Stack gap="2">
                    {detail.allowed_transitions.map((status) => (
                        <Button
                            key={status}
                            colorPalette={getRentalStatusMeta(status).color}
                            size="lg"
                            loading={updating}
                            onClick={() => handleTransition(status)}
                        >
                            {getRentalStatusMeta(status).label}
                        </Button>
                    ))}
                </Stack>
            )}
        </Box>
    )
}
