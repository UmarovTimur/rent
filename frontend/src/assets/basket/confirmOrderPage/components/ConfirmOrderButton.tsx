import { Button } from '@chakra-ui/react'
import { useDrawer } from '@/contexts/DrawerContext.tsx'
import { useBasketContext } from '@/contexts/BasketContext.tsx'
import { useOrder } from '@/contexts/OrderContext'
import { useEffect } from 'react'
import { toaster } from '@/components/ui/toaster.tsx'
import { useUserContext } from '@/contexts/UserContext.tsx'
import { formatPriceK } from '@/utils/price'

export default function ConfirmOrderButton() {
    const { basket, refreshBasket } = useBasketContext()
    const { onClose } = useDrawer()
    const { submitOrder, isSuccess, resetForm } = useOrder()
    const { refreshOrderHistory } = useUserContext()

    useEffect(() => {
        if (isSuccess) {
            resetForm()
            onClose()
            toaster.create({
                description: 'Заказ успешно оформлен!',
                type: 'success',
            })
        }
    }, [isSuccess, resetForm, onClose])

    const handleSubmit = async () => {
        if (!basket) return
        await submitOrder(basket)
        await refreshBasket()
        await refreshOrderHistory()
    }

    return (
        <Button
            w="full"
            bg="accent"
            h="48px"
            p="0"
            fontSize="md"
            fontWeight="700"
            rounded="full"
            color="text"
            onClick={handleSubmit}
        >
            Заказать - {formatPriceK(basket?.total_price)}
        </Button>
    )
}
