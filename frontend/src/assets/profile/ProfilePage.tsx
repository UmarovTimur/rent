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
import { ProductService } from '@/api/ProductService'
import { useEffect, useMemo, useState } from 'react'
import { Product } from '@/types/Products.ts'
import { formatPriceK } from '@/utils/price'
import axios from 'axios'
import API_BASE_URL from '@/config'
import ConfirmationDialog from '@/assets/basket/basketPage/components/ConfirmationDialog'

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
    const [products, setProducts] = useState<Product[]>([])
    const [productsLoading, setProductsLoading] = useState(true)
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
            return 'Дата неизвестна'
        }
    }

    const translateStatus = (status: string) => {
        const statusMap: Record<string, string> = {
            in_progress: 'В процессе',
            taken: 'Выдан',
            created: 'Создан',
            canceled: 'Отменен',
            completed: 'Завершен',
        }
        return statusMap[status] || status
    }

    const translatePayment = (payment: string) => {
        const paymentMap: Record<string, string> = {
            cash: 'Наличными',
            card: 'Картой',
        }
        return paymentMap[payment] || payment
    }

    useEffect(() => {
        const fetchProducts = async () => {
            try {
                const productsData = await ProductService.fetchAllProducts()
                setProducts(productsData)
            } catch (err) {
                console.error('Failed to load products:', err)
            } finally {
                setProductsLoading(false)
            }
        }

        fetchProducts()
    }, [])

    const productMap = useMemo(() => {
        const map = new Map<number, Product>()
        products.forEach((product) => map.set(product.product_id, product))
        return map
    }, [products])

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

    const isLoading = loading || productsLoading
    if (isLoading) {
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
                    Профиль
                </Heading>
            </Drawer.Header>

            <Drawer.Body p="12px">
                <Flex gap="gap">
                    <Center w="100px" h="100px" bg="back" rounded="24px">
                        <Icon as={RiUser3Line} w="60%" h="60%" color="text" />
                    </Center>

                    <Flex direction="column" justify="space-between" py="8px">
                        <Heading size="xl" fontWeight="800">
                            {user?.first_name || 'Пользователь'}
                        </Heading>
                        <Heading size="lg" fontWeight="500">
                            {user?.username ? `@${user.username}` : 'Юзернейм скрыт'}
                        </Heading>
                        {/* <Heading size="lg" fontWeight="500">
                            Баллов: {user?.coins}
                        </Heading> */}
                    </Flex>
                </Flex>

                <Heading size="2xl" fontWeight="800" textAlign="center" w="full" py="gap">
                    История заказов
                </Heading>

                <Flex gap="gap" direction="column">
                    {orderHistory.length === 0 ? (
                        <Text textAlign="center" py={4}>
                            У вас пока нет заказов
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
                                        bg="accent"
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

                                    <Text fontWeight="500">{order.order_id}</Text>
                                    <Text fontWeight="500">
                                        {order.address || ''}
                                    </Text>

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
                                                Период: {period}
                                            </Text>
                                        ) : null
                                    })()}

                                    <Flex direction="column" gap="4px">
                                        {order.items.map((item) => {
                                            const productInfo = productMap.get(item.product_id)
                                            return (
                                                <Text key={item.order_item_id} fontWeight="500">
                                                    {item.quantity} ×{' '}
                                                    {productInfo
                                                        ? `${productInfo.name} - ${formatPriceK(item.unit_price * item.quantity)}`
                                                        : `Товар #${item.product_id}`}
                                                </Text>
                                            )
                                        })}
                                    </Flex>

                                    <Text fontWeight="500">
                                        Способ оплаты: {translatePayment(order.payment_option)}
                                    </Text>

                                    <Text fontWeight="500">
                                        Итоговая сумма: {formatPriceK(order.total_price)}
                                    </Text>

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
                                            Отменить заказ
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
                    title="Отменить заказ?"
                    message="Вы уверены, что хотите отменить этот заказ? Это действие нельзя отменить."
                    confirmLabel="Да, отменить"
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
                        Выйти из аккаунта
                    </Button>
                )}
            </Drawer.Body>
        </>
    )
}
