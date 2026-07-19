import { Button } from '@chakra-ui/react'
import { useDrawer } from '@/contexts/DrawerContext.tsx'
import { useBasketContext } from '@/contexts/BasketContext.tsx'
import { useOrder } from '@/contexts/OrderContext'
import { useEffect } from 'react'
import { useUserContext } from '@/contexts/UserContext.tsx'
import { formatPriceK } from '@/utils/price'
import { useTranslation } from '@/i18n/LanguageContext'

export default function ConfirmOrderButton() {
    const { basket, refreshBasket } = useBasketContext()
    const { onClose } = useDrawer()
    const { submitOrder, isSuccess, resetForm } = useOrder()
    const { refreshOrderHistory } = useUserContext()
    const { t } = useTranslation()

    // Успешное оформление: закрываем корзину, дальше клиенту показывается
    // OrderSuccessDialog (глобальный попап с напоминанием отправить чек в бот).
    useEffect(() => {
        if (isSuccess) {
            resetForm()
            onClose()
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
            {t('order')} - {formatPriceK(basket?.total_price)}
        </Button>
    )
}
