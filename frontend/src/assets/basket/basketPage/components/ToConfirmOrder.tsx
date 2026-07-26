import { Button } from '@chakra-ui/react'
import { useBasketContext } from '@/contexts/BasketContext'
import { useUserContext } from '@/contexts/UserContext'
import { formatPriceK } from '@/utils/price'
import { useTranslation } from '@/i18n/LanguageContext'

type ToConfirmOrderProps = {
    openConfirmPage: () => void
}

export default function ToConfirmOrder({
    openConfirmPage,
}: ToConfirmOrderProps) {
    const { basket } = useBasketContext()
    const { user } = useUserContext()
    const { t } = useTranslation()

    if (user?.is_banned) {
        return (
            <Button
                w="full"
                bg="red.600"
                h="48px"
                p="0"
                fontSize="md"
                fontWeight="700"
                rounded="full"
                color="white"
                disabled
                _disabled={{ opacity: 1, cursor: 'not-allowed' }}
            >
                {t('userBanned')}
            </Button>
        )
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
            onClick={() => {
                openConfirmPage()
            }}
        >
            {t('checkout')} - {formatPriceK(basket?.total_price)}
        </Button>
    )
}
