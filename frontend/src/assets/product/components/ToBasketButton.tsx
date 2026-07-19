import { CloseButton } from '@chakra-ui/react'
import { useDrawer } from '@/contexts/DrawerContext'
import { useBasketContext } from '@/contexts/BasketContext'
import { useTripDates } from '@/contexts/TripDatesContext'
import { formatPriceK } from '@/utils/price'
import { AddonSelection } from '@/types/Basket'
import { useTranslation } from '@/i18n/LanguageContext'

type ToBasketProps = {
    currentPrice: number
    productId: number
    quantity: number
    disabled?: boolean
    unavailable?: boolean
    // True when there's real capacity, but this basket already holds all of it
    // for these exact dates — distinct from "unavailable" (no capacity at all).
    atCapacityInBasket?: boolean
    addons?: AddonSelection[]
}

export default function ToBasketButton({
    currentPrice,
    productId,
    quantity,
    disabled = false,
    unavailable = false,
    atCapacityInBasket = false,
    addons = [],
}: ToBasketProps) {
    const { onClose } = useDrawer()
    const { addToBasket, loading } = useBasketContext()
    const { hasValidRange, datesConfirmed, rentalStartIso, rentalEndIso } = useTripDates()
    const { t } = useTranslation()

    const needsDates = !hasValidRange || !datesConfirmed
    // A zero total means nothing billable is selected — a 0-priced product needs at
    // least one paid add-on. Block the add and prompt to pick options instead.
    const requiresOptions = !needsDates && !unavailable && currentPrice === 0
    const isDisabled = needsDates || disabled || loading || requiresOptions

    const handleClick = async () => {
        if (!hasValidRange || !datesConfirmed || !rentalStartIso || !rentalEndIso) return
        if (currentPrice === 0) return

        const success = await addToBasket(
            productId,
            quantity,
            rentalStartIso,
            rentalEndIso,
            addons
        )

        if (success) onClose()
    }

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
                ? t('specifyDates')
                : unavailable
                  ? t('unavailableForDates')
                  : atCapacityInBasket
                    ? t('alreadyInCartMax')
                    : requiresOptions
                      ? t('chooseOptions')
                      : `${t('addToCart')} - ${formatPriceK(currentPrice)}`}
        </CloseButton>
    )
}
