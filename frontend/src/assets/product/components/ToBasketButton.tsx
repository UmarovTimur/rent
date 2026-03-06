import { CloseButton } from '@chakra-ui/react'
import { useDrawer } from '@/contexts/DrawerContext'
import { useBasketContext } from '@/contexts/BasketContext'
import { useTripDates } from '@/contexts/TripDatesContext'
import { formatPriceK } from '@/utils/price'

type ToBasketProps = {
    currentPrice: number
    productId: number
    quantity: number
    disabled?: boolean
}

export default function ToBasketButton({
    currentPrice,
    productId,
    quantity,
    disabled = false,
}: ToBasketProps) {
    const { onClose } = useDrawer()
    const { addToBasket, loading } = useBasketContext()
    const { hasValidRange, rentalStartIso, rentalEndIso } = useTripDates()

    const handleClick = async () => {
        if (!hasValidRange || !rentalStartIso || !rentalEndIso) return

        const success = await addToBasket(
            productId,
            quantity,
            rentalStartIso,
            rentalEndIso
        )

        if (success) onClose()
    }

    const isDisabled = !hasValidRange || disabled || loading

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
            В корзину - {formatPriceK(currentPrice)}
        </CloseButton>
    )
}
