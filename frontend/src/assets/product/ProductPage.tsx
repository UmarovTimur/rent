import {
    Drawer,
    Image,
    Heading,
    Flex,
    CloseButton,
    Text,
    Box,
    Mark,
} from '@chakra-ui/react'
import { useEffect, useMemo, useState } from 'react'
import { IoClose } from 'react-icons/io5'
import { Product } from '@/types/Products'
import CustomNumberInput from './components/CustomNumberInput'
import ToBasketButton from './components/ToBasketButton'
import { useDrawer } from '@/contexts/DrawerContext'
import { useBasketContext } from '@/contexts/BasketContext'
import { useTripDates } from '@/contexts/TripDatesContext'
import LimitDialog from './components/LimitDialog'
import { RentalService } from '@/api/RentalService'
import {
    formatInputDate,
    formatRentalDaysRu,
    getRoundedRentalDaysFromIso,
} from '@/utils/rental'

type ProductPageProps = {
    product: Product
}

export default function ProductPage({ product }: ProductPageProps) {
    const [selectedProduct] = useState<Product>(product)
    const [tempQuantity, setTempQuantity] = useState(1)
    const [showLimitDialog, setShowLimitDialog] = useState(false)
    const [availableQuantity, setAvailableQuantity] = useState<number | null>(null)
    const [availabilityLoading, setAvailabilityLoading] = useState(false)

    const { onClose } = useDrawer()
    const { error, clearError, basketProducts } = useBasketContext()
    const {
        startDate,
        endDate,
        startTime,
        endTime,
        hasValidRange,
        rentalStartIso,
        rentalEndIso,
        getTripDurationDays,
    } = useTripDates()

    const reservedInBasketQuantity = useMemo(() => {
        if (!rentalStartIso || !rentalEndIso) return 0

        return basketProducts.reduce((sum, item) => {
            if (item.product_id !== selectedProduct.product_id) {
                return sum
            }

            const sameStart =
                item.rental_start != null &&
                new Date(item.rental_start).toISOString() === rentalStartIso
            const sameEnd =
                item.rental_end != null &&
                new Date(item.rental_end).toISOString() === rentalEndIso

            return sameStart && sameEnd ? sum + item.quantity : sum
        }, 0)
    }, [
        basketProducts,
        rentalStartIso,
        rentalEndIso,
        selectedProduct.product_id,
    ])

    const remainingAvailableQuantity =
        availableQuantity == null
            ? null
            : Math.max(0, availableQuantity - reservedInBasketQuantity)

    useEffect(() => {
        if (error?.includes('Максимальное')) {
            setShowLimitDialog(true)
        }
    }, [error])

    useEffect(() => {
        if (!hasValidRange || !rentalStartIso || !rentalEndIso) {
            setAvailableQuantity(null)
            setAvailabilityLoading(false)
            return
        }

        let cancelled = false

        const loadAvailability = async () => {
            setAvailabilityLoading(true)

            try {
                const calendar = await RentalService.getProductCalendar(
                    selectedProduct.product_id,
                    rentalStartIso,
                    rentalEndIso
                )

                const minAvailable =
                    calendar.slots.length > 0
                        ? Math.min(
                            ...calendar.slots.map((slot) =>
                                slot.is_available ? slot.available_quantity : 0
                            )
                        )
                        : 0

                if (!cancelled) {
                    setAvailableQuantity(Math.max(0, minAvailable))
                }
            } catch {
                if (!cancelled) {
                    setAvailableQuantity(0)
                }
            } finally {
                if (!cancelled) {
                    setAvailabilityLoading(false)
                }
            }
        }

        loadAvailability()

        return () => {
            cancelled = true
        }
    }, [hasValidRange, rentalStartIso, rentalEndIso, selectedProduct.product_id])

    useEffect(() => {
        if (remainingAvailableQuantity == null) return

        if (remainingAvailableQuantity <= 0) {
            if (tempQuantity !== 1) {
                setTempQuantity(1)
            }
            return
        }

        if (tempQuantity > remainingAvailableQuantity) {
            setTempQuantity(remainingAvailableQuantity)
        }
    }, [remainingAvailableQuantity, tempQuantity])

    const handleCloseDialog = () => {
        setShowLimitDialog(false)
        clearError()
    }

    const maxSelectableQuantity =
        remainingAvailableQuantity == null
            ? 99
            : Math.max(1, Math.min(99, remainingAvailableQuantity))
    const isUnavailableForDates =
        hasValidRange && !availabilityLoading && remainingAvailableQuantity === 0
    const tripDurationDays =
        hasValidRange && rentalStartIso && rentalEndIso
            ? Math.max(1, getRoundedRentalDaysFromIso(rentalStartIso, rentalEndIso) ?? 1)
            : Math.max(1, getTripDurationDays() ?? 1)
    const formattedStartDate = formatInputDate(startDate)
    const formattedEndDate = formatInputDate(endDate)

    return (
        <>
            <Drawer.Header
                position="relative"
                px={{ base: '16px', md: '20px', lg: '24px' }}
            >
                <CloseButton
                    position="absolute"
                    left={{ base: '20px', md: '24px' }}
                    top="20px"
                    w="fit"
                    zIndex="docked"
                    onClick={onClose}
                >
                    <IoClose />
                </CloseButton>
                <Flex
                    flexDirection="column"
                    alignItems="center"
                    w="full"
                    maxW={{ base: '100%', lg: '920px' }}
                    mx="auto"
                >
                    <Image
                        src={
                            product.image_url
                                ? `products/${product.image_url}`
                                : 'shava.png'
                        }
                        rounded={{ base: '32px 32px 0 0', sm: '42px 42px 0 0' }}
                        width={{ base: '80%', sm: '70%', md: '52%', lg: '40%' }}
                        maxW="360px"
                        zIndex="base"
                        alt={product.name}
                    />
                    <Heading
                        size={{ base: '4xl', md: '5xl' }}
                        fontWeight="800"
                        color="text"
                        textAlign="center"
                        mt={{ base: '-30px', md: '-38px' }}
                        pos="relative"
                        w="full"
                        px={{ base: '36px', md: '0' }}
                        textShadow="0px -1px 5px rgba(0,0,0,0.65);"
                    >
                        {product.name}
                    </Heading>
                </Flex>
            </Drawer.Header>

            <Drawer.Body
                px={{ base: '16px', md: '20px', lg: '24px' }}
                display="flex"
                alignItems="center"
                gap="14px"
                flexDirection="column"
                alignSelf="stretch"
            >
                <Flex
                    w="full"
                    maxW={{ base: '100%', lg: '920px' }}
                    mx="auto"
                    direction={{ base: 'column', lg: 'row' }}
                    align={{ base: 'stretch', lg: 'flex-start' }}
                    justifyContent="center"
                    gap={{ base: '14px', lg: '18px' }}
                >
                    <Box>
                        <Text
                            paddingX="18px"
                            paddingBottom="12px"
                            alignSelf="stretch"
                            color="text"
                            opacity={0.8}
                            flex="1">
                            {product.description}
                        </Text>
                        <Box
                            alignSelf="stretch"
                            bg="back"
                            rounded="24px"
                            p="18px"
                            flex="1"
                            minW={{ lg: '320px' }}
                        >
                            <Flex
                                gap="10px"
                                align={{ base: 'flex-start', sm: 'center' }}
                            >
                                <Text fontWeight="600" mb="4px">
                                    Период аренды:
                                </Text>
                                <Mark fontWeight="bold" color="accent">
                                    {formatRentalDaysRu(getTripDurationDays())}
                                </Mark>
                            </Flex>
                            <Text opacity={0.8} fontSize="sm">
                                {hasValidRange
                                    ? `${formattedStartDate} ${startTime} — ${formattedEndDate} ${endTime}`
                                    : 'Выберите даты и время аренды на главном экране'}
                            </Text>
                        </Box>
                        {hasValidRange && (
                            <Text
                                w="full"
                                maxW={{ base: '100%', lg: '920px' }}
                                paddingX="18px"
                                alignSelf="stretch"
                                opacity={0.8}
                                fontSize="sm"
                                mt="6px"
                            >
                                {availabilityLoading
                                    ? 'Проверяем доступность...'
                                    : `Доступно на выбранный период: ${remainingAvailableQuantity ?? 0} шт.`}
                            </Text>
                        )}
                    </Box>
                </Flex>
            </Drawer.Body>

            <Drawer.Footer p={{ base: '12px', md: '16px 20px 20px' }}>
                <Flex
                    w="full"
                    maxW={{ base: '100%', lg: '920px' }}
                    mx="auto"
                    gap="gap"
                >
                    <CustomNumberInput
                        value={tempQuantity.toString()}
                        max={maxSelectableQuantity}
                        disabled={isUnavailableForDates}
                        setQuantity={(value) => {
                            setTempQuantity(value)
                        }}
                    />

                    <ToBasketButton
                        currentPrice={selectedProduct.price * tempQuantity * tripDurationDays}
                        productId={selectedProduct.product_id}
                        quantity={tempQuantity}
                        disabled={availabilityLoading || isUnavailableForDates}
                    />
                </Flex>
            </Drawer.Footer>

            <LimitDialog
                isOpen={showLimitDialog}
                onClose={handleCloseDialog}
                title="Превышен лимит"
                message="В корзине может быть не более 99 единиц одного товара"
            />
        </>
    )
}
