import { CloseButton } from '@chakra-ui/react'
import { useDrawer } from '@/contexts/DrawerContext'
import { useBasketContext } from '@/contexts/BasketContext'
import { useTripDates } from '@/contexts/TripDatesContext'
import { formatPriceK } from '@/utils/price'
import { AddonSelection } from '@/types/Basket'

type ToBasketProps = {
    currentPrice: number
    productId: number
    quantity: number
    disabled?: boolean
    unavailable?: boolean
    addons?: AddonSelection[]
}

export default function ToBasketButton({
    currentPrice,
    productId,
    quantity,
    disabled = false,
    unavailable = false,
    addons = [],
}: ToBasketProps) {
    const { onClose } = useDrawer()
    const { addToBasket, loading } = useBasketContext()
    const { hasValidRange, datesConfirmed, rentalStartIso, rentalEndIso } = useTripDates()

    const handleClick = async () => {
        if (!hasValidRange || !datesConfirmed || !rentalStartIso || !rentalEndIso) return

        const success = await addToBasket(
            productId,
            quantity,
            rentalStartIso,
            rentalEndIso,
            addons
        )

        if (success) onClose()
    }

    const needsDates = !hasValidRange || !datesConfirmed
    const isDisabled = needsDates || disabled || loading

    return (
        <CloseButton
            flex="1"
            bg="accent"
            h="48px"
            p="0"
            fontSize="md"
            fontWeight="700"
            rounded="full"
            color="text"
            onClick={handleClick}
            disabled={isDisabled}
            opacity={isDisabled ? 0.6 : 1}
        >
            {needsDates
                ? 'Укажите даты аренды'
                : unavailable
                  ? 'Недоступно на эти даты'
                  : `В корзину - ${formatPriceK(currentPrice)}`}
        </CloseButton>
    )
}
