import {
    Drawer,
    Heading,
    CloseButton,
    Icon,
    Center,
    Flex,
    Text,
    Spinner,
    Button,
} from '@chakra-ui/react'
import { IoClose } from 'react-icons/io5'
import { useDrawer } from '@/contexts/DrawerContext'
import { RiUser3Line, RiLogoutBoxLine } from 'react-icons/ri'
import { AuthService } from '@/api/AuthService'
import { useUserContext } from '@/contexts/UserContext'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useState } from 'react'
import { formatPriceK } from '@/utils/price'
import axios from 'axios'
import API_BASE_URL from '@/config'
import ConfirmationDialog from '@/assets/basket/basketPage/components/ConfirmationDialog'
import { useTranslation } from '@/i18n/LanguageContext'
import { groupOrderItems } from '@/utils/orderItems'

const cisDateFormatter = new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
})

const formatRentalRange = (start?: string | null, end?: string | null) => {
    if (!start || !end) return null
    const s = new Date(start)
    const e = new Date(end)
    e.setDate(e.getDate() - 1)
    return `${cisDateFormatter.format(s)} - ${cisDateFormatter.format(e)}`
}

export default function ProfilePage() {
    const { onClose } = useDrawer()
    const { user, orderHistory, loading } = useUserContext()
    const { t, lang, setLang } = useTranslation()
    const isWebUser = Boolean(localStorage.getItem('auth_token'))

    const handleLogout = () => {
        AuthService.clearSession()
        window.location.reload()
    }

    const formatOrderDate = (dateString: string) => {
        try {
            const date = new Date(dateString)
            return format(date, 'dd.MM.yyyy HH:mm', { locale: ru })
        } catch {
            return t('dateUnknown')
        }
    }

    const translateStatus = (status: string) => {
        // Simplified client-facing wording — the client doesn't need to know
        // internal states like "paused", just where their order stands.
        return t(`status_${status}`)
    }

    const statusColor = (status: string) => {
        const colorMap: Record<string, string> = {
            created: 'orange.400',
            in_progress: 'green.500',
            paused: 'purple.500',
            taken: 'blue.500',
            // Successful finish ("Завершён") → grey; unsuccessful ("Закрыт") →
            // dark badge (darker than the page background), see theme `closed`.
            returned: 'gray.500',
            completed: 'closed',
            canceled: 'red.500',
        }
        return colorMap[status] || 'accent'
    }

    const translatePayment = (payment: string) => {
        if (payment === 'cash') return t('payCash')
        if (payment === 'card') return t('payCard')
        return payment
    }

    const [cancellingOrderId, setCancellingOrderId] = useState<number | null>(null)
    const [confirmCancelOrderId, setConfirmCancelOrderId] = useState<number | null>(null)
    const { refreshOrderHistory } = useUserContext()

    const handleCancelOrder = async (orderId: number) => {
        setCancellingOrderId(orderId)
        try {
            await axios.patch(`${API_BASE_URL}api/v1/order/change_status/${orderId}?status=canceled`)
            await refreshOrderHistory()
        } catch (err) {
            console.error('Failed to cancel order:', err)
        } finally {
            setCancellingOrderId(null)
        }
    }

    const CANCELLABLE_STATUSES = ['created', 'in_progress']

    if (loading) {
        return (
            <Center h="100vh">
                <Spinner size="xl" />
            </Center>
        )
    }

    return (
        <>
            <Drawer.Header position="relative">
                <CloseButton
                    position="absolute"
                    left="20px"
                    top="20px"
                    w="fit"
                    zIndex="docked"
                    onClick={onClose}
                >
                    <IoClose />
                </CloseButton>

                <Heading size="2xl" fontWeight="800" textAlign="center" w="full">
                    {t('profileTitle')}
                </Heading>
            </Drawer.Header>

            <Drawer.Body p="12px">
                <Flex gap="gap">
                    <Center w="100px" h="100px" bg="back" rounded="24px">
                        <Icon as={RiUser3Line} w="60%" h="60%" color="text" />
                    </Center>

                    <Flex direction="column" justify="space-between" py="8px">
                        <Heading size="xl" fontWeight="800">
                            {user?.first_name || t('userFallback')}
                        </Heading>
                        <Heading size="lg" fontWeight="500">
                            {user?.username ? `@${user.username}` : t('usernameHidden')}
                        </Heading>
                        {!!user?.coins && (
                            <Text fontWeight="600" color="accent">
                                {t('coinsBalance', { amount: formatPriceK(user.coins) })}
                            </Text>
                        )}
                    </Flex>
                </Flex>

                <Flex gap="8px" mt="gap" justify="center">
                    {(['ru', 'uz'] as const).map((code) => (
                        <Button
                            key={code}
                            size="sm"
                            rounded="full"
                            fontWeight="700"
                            px="20px"
                            bg={lang === code ? 'accent' : 'back'}
                            color="text"
                            onClick={() => setLang(code)}
                        >
                            {code === 'ru' ? '🇷🇺 Русский' : '🇺🇿 O‘zbekcha'}
                        </Button>
                    ))}
                </Flex>

                <Heading size="2xl" fontWeight="800" textAlign="center" w="full" py="gap">
                    {t('orderHistory')}
                </Heading>

                <Flex gap="gap" direction="column">
                    {orderHistory.length === 0 ? (
                        <Text textAlign="center" py={4}>
                            {t('noOrders')}
                        </Text>
                    ) : (
                        orderHistory
                            .sort((a, b) => b.order_id - a.order_id)
                            .map((order) => (
                                <Flex
                                    key={order.order_id}
                                    direction="column"
                                    gap="12px"
                                    p="gap"
                                    borderWidth="2px"
                                    borderColor="gray"
                                    w="full"
                                    rounded="32px"
                                    pos="relative"
                                >
                                    <Center
                                        bg={statusColor(order.status)}
                                        color="white"
                                        fontWeight="600"
                                        rounded="full"
                                        px="16px"
                                        py="6px"
                                        w="fit"
                                        right="gap"
                                        pos="absolute"
                                    >
                                        {translateStatus(order.status)}
                                    </Center>

                                    <Text fontWeight="500" color="text/50">
                                        {formatOrderDate(order.order_date)}
                                    </Text>

                                    <Text fontWeight="500">{t('orderNumber', { id: order.order_id })}</Text>

                                    {(() => {
                                        const firstItemWithDates = order.items.find(
                                            (i) => i.rental_start && i.rental_end
                                        )
                                        const period = formatRentalRange(
                                            firstItemWithDates?.rental_start,
                                            firstItemWithDates?.rental_end
                                        )
                                        return period ? (
                                            <Text fontSize="sm" opacity="0.7">
                                                {t('period')}: {period}
                                            </Text>
                                        ) : null
                                    })()}

                                    <Flex direction="column" gap="4px">
                                        {groupOrderItems(order.items, (id) =>
                                            t('productFallback', { id })
                                        ).map((row) =>
                                            row.type === 'flat' ? (
                                                <Text key={row.key} fontWeight="500">
                                                    {row.text}
                                                </Text>
                                            ) : (
                                                <Flex key={row.key} direction="column" gap="2px">
                                                    <Text fontWeight="600">{row.header}</Text>
                                                    {row.children.map((child) => (
                                                        <Text key={child.key} fontWeight="500" pl="14px" fontSize="sm">
                                                            • {child.text}
                                                        </Text>
                                                    ))}
                                                </Flex>
                                            )
                                        )}
                                    </Flex>

                                    <Text fontWeight="500">
                                        {t('paymentMethod')}: {translatePayment(order.payment_option)}
                                    </Text>

                                    <Text fontWeight="500">
                                        {t('totalSum')}: {formatPriceK(order.total_price)}
                                    </Text>

                                    {order.address && (
                                        <Text fontWeight="500" color="text/50">
                                            {t('addressLabel')}: {order.address}
                                        </Text>
                                    )}

                                    {CANCELLABLE_STATUSES.includes(order.status) && (
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            borderWidth="2px"
                                            borderColor="red.500"
                                            color="red.500"
                                            rounded="full"
                                            fontWeight="600"
                                            loading={cancellingOrderId === order.order_id}
                                            onClick={() => setConfirmCancelOrderId(order.order_id)}
                                        >
                                            {t('cancelOrder')}
                                        </Button>
                                    )}
                                </Flex>
                            ))
                    )}
                </Flex>

                <ConfirmationDialog
                    isOpen={confirmCancelOrderId !== null}
                    onClose={() => setConfirmCancelOrderId(null)}
                    onConfirm={() => {
                        if (confirmCancelOrderId !== null) handleCancelOrder(confirmCancelOrderId)
                    }}
                    title={t('cancelOrderTitle')}
                    message={t('cancelOrderMessage')}
                    confirmLabel={t('cancelOrderConfirm')}
                />

                {isWebUser && (
                    <Button
                        mt="24px"
                        w="full"
                        size="lg"
                        borderRadius="18px"
                        variant="outline"
                        borderWidth="2px"
                        borderColor="gray"
                        color="red.500"
                        fontWeight="700"
                        gap="8px"
                        onClick={handleLogout}
                    >
                        <Icon as={RiLogoutBoxLine} boxSize="20px" />
                        {t('logout')}
                    </Button>
                )}
            </Drawer.Body>
        </>
    )
}
