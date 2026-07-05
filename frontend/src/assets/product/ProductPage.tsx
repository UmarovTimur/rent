import {
    Drawer,
    Heading,
    Flex,
    CloseButton,
    Text,
    Box,
    Center,
    Mark,
} from '@chakra-ui/react'
import { useEffect, useMemo, useState } from 'react'
import { IoClose } from 'react-icons/io5'
import { FiCheck, FiMinus, FiPlus } from 'react-icons/fi'
import { Addon, Product } from '@/types/Products'
import CustomNumberInput from './components/CustomNumberInput'
import ToBasketButton from './components/ToBasketButton'
import ImageSlider from './components/ImageSlider'
import { useDrawer } from '@/contexts/DrawerContext'
import { useBasketContext } from '@/contexts/BasketContext'
import { useTripDates } from '@/contexts/TripDatesContext'
import LimitDialog from './components/LimitDialog'
import { RentalService } from '@/api/RentalService'
import { ProductService } from '@/api/ProductService'
import { formatPriceK } from '@/utils/price'
import { productImageSrc } from '@/utils/media'
import {
    formatInputDate,
    formatRentalDaysRu,
    getBilledRentalDaysFromIso,
    previewLineTotalWithAddons,
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
    const [addons, setAddons] = useState<Addon[]>([])
    // Max quantity of each add-on available for the window (0 = unavailable).
    const [addonMax, setAddonMax] = useState<Record<number, number>>({})
    // Selected add-ons -> chosen quantity (absent/0 = not selected).
    const [addonQty, setAddonQty] = useState<Record<number, number>>({})

    const { onClose } = useDrawer()
    const { error, clearError, basketProducts } = useBasketContext()
    const {
        startDate,
        endDate,
        startTime,
        endTime,
        hasValidRange,
        datesConfirmed,
        rentalStartIso,
        rentalEndIso,
        getTripDurationDays,
        eveningGraceExplanation,
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
        // Only probe availability once the user has actually chosen dates;
        // before that the product is shown but not date-bound.
        if (!hasValidRange || !datesConfirmed || !rentalStartIso || !rentalEndIso) {
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
    }, [hasValidRange, datesConfirmed, rentalStartIso, rentalEndIso, selectedProduct.product_id])

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

    // Optional add-ons offered on this product.
    useEffect(() => {
        let cancelled = false
        ProductService.fetchAddons(selectedProduct.product_id).then((data) => {
            if (!cancelled) setAddons(data)
        })
        return () => {
            cancelled = true
        }
    }, [selectedProduct.product_id])

    // Per-add-on availability for the chosen window (same calendar as products).
    useEffect(() => {
        if (!datesConfirmed || !rentalStartIso || !rentalEndIso || addons.length === 0) {
            setAddonMax({})
            return
        }
        let cancelled = false
        Promise.all(
            addons.map(async (a) => {
                try {
                    const cal = await RentalService.getProductCalendar(
                        a.product_id,
                        rentalStartIso,
                        rentalEndIso
                    )
                    // Max units bookable = smallest availability across the window.
                    const max =
                        cal.slots.length > 0
                            ? Math.min(
                                  ...cal.slots.map((s) =>
                                      s.is_available ? s.available_quantity : 0
                                  )
                              )
                            : 0
                    return [a.product_id, Math.max(0, max)] as const
                } catch {
                    return [a.product_id, 0] as const
                }
            })
        ).then((res) => {
            if (!cancelled) setAddonMax(Object.fromEntries(res))
        })
        return () => {
            cancelled = true
        }
    }, [addons, datesConfirmed, rentalStartIso, rentalEndIso])

    // Drop / clamp selected add-ons when availability for the window changes.
    useEffect(() => {
        setAddonQty((prev) => {
            const next: Record<number, number> = {}
            for (const [id, qty] of Object.entries(prev)) {
                const max = addonMax[Number(id)]
                if (max === undefined) next[Number(id)] = qty
                else if (max > 0) next[Number(id)] = Math.min(qty, max)
            }
            return next
        })
    }, [addonMax])

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
    // When the item can't be added and the button shows the reason why (dates not
    // chosen / unavailable on these dates), hide the +/- stepper so the button takes
    // the full width.
    const needsDates = !hasValidRange || !datesConfirmed
    const canAddToBasket = !needsDates && !isUnavailableForDates
    const tripDurationDays =
        hasValidRange && rentalStartIso && rentalEndIso
            ? getBilledRentalDaysFromIso(rentalStartIso, rentalEndIso) ?? 1
            : getTripDurationDays() ?? 1
    const tripHalfDays = Math.round(tripDurationDays * 2)
    const formattedStartDate = formatInputDate(startDate)
    const formattedEndDate = formatInputDate(endDate)

    const isAddonDisabled = (addonId: number) =>
        datesConfirmed && addonMax[addonId] === 0
    const addonMaxQty = (addonId: number) =>
        Math.max(1, Math.min(99, addonMax[addonId] ?? 99))
    const toggleAddon = (addonId: number) => {
        if (isAddonDisabled(addonId)) return
        setAddonQty((prev) => {
            const next = { ...prev }
            if (next[addonId]) delete next[addonId]
            else next[addonId] = 1
            return next
        })
    }
    const setAddonQuantity = (addonId: number, qty: number) => {
        setAddonQty((prev) => {
            const next = { ...prev }
            if (qty <= 0) delete next[addonId]
            else next[addonId] = Math.min(qty, addonMaxQty(addonId))
            return next
        })
    }
    const selectedAddons = useMemo(
        () =>
            addons
                .filter(
                    (a) =>
                        (addonQty[a.product_id] ?? 0) > 0 &&
                        addonMax[a.product_id] !== 0
                )
                .map((a) => ({ ...a, quantity: addonQty[a.product_id] })),
        [addons, addonQty, addonMax]
    )
    const currentPrice = previewLineTotalWithAddons(
        selectedProduct.price,
        tempQuantity,
        tripHalfDays,
        selectedAddons.map((a) => ({
            price: a.price,
            price_mode: a.price_mode,
            quantity: a.quantity,
        }))
    )

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
                    <ImageSlider
                        images={(() => {
                            const all = [
                                ...(product.image_url ? [productImageSrc(product.image_url)] : []),
                                ...(product.image_urls ?? []).map(productImageSrc),
                            ]
                            return all.length > 0 ? all : ['shava.png']
                        })()}
                        rounded={{ base: '32px', sm: '42px' }}
                        width={{ base: '62%', sm: '54%', md: '56%', lg: '46%' }}
                        maxW={{ base: '260px', md: '400px' }}
                        alt={product.name}
                    />
                    <Heading
                        size={{ base: '4xl', md: '5xl' }}
                        fontWeight="800"
                        color="text"
                        textAlign="center"
                        mt={{ base: '16px', md: '16px' }}
                        pos="relative"
                        w="full"
                        px={{ base: '36px', md: '0' }}
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
                                {hasValidRange && datesConfirmed
                                    ? `${formattedStartDate} ${startTime} — ${formattedEndDate} ${endTime}`
                                    : 'Выберите даты и время аренды на главном экране'}
                            </Text>
                            {hasValidRange && datesConfirmed && eveningGraceExplanation && (
                                <Text opacity={0.7} fontSize="xs" mt="4px" color="green.500">
                                    {eveningGraceExplanation}
                                </Text>
                            )}
                        </Box>
                        {hasValidRange && datesConfirmed && (
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

                        {addons.length > 0 && (
                            <Box mt="14px">
                                <Text fontWeight="700" px="18px" mb="8px">
                                    Дополнительно
                                </Text>
                                <Flex direction="column" gap="8px">
                                    {addons.map((addon) => {
                                        const disabled = isAddonDisabled(addon.product_id)
                                        const qty = addonQty[addon.product_id] ?? 0
                                        const checked = qty > 0 && !disabled
                                        const max = addonMaxQty(addon.product_id)
                                        return (
                                            <Flex
                                                key={addon.product_id}
                                                role="button"
                                                onClick={() => toggleAddon(addon.product_id)}
                                                align="center"
                                                gap="12px"
                                                bg="back"
                                                rounded="18px"
                                                px="16px"
                                                h="52px"
                                                w="full"
                                                textAlign="left"
                                                opacity={disabled ? 0.5 : 1}
                                                cursor={disabled ? 'not-allowed' : 'pointer'}
                                                borderWidth="1.5px"
                                                borderColor={checked ? 'accent' : 'transparent'}
                                                transition="border-color 0.15s ease"
                                            >
                                                <Center
                                                    h="22px"
                                                    w="22px"
                                                    flexShrink={0}
                                                    rounded="6px"
                                                    borderWidth="2px"
                                                    borderColor={checked ? 'accent' : 'gray'}
                                                    bg={checked ? 'accent' : 'transparent'}
                                                    color="text"
                                                >
                                                    {checked && <FiCheck size={14} />}
                                                </Center>
                                                <Flex direction="column" flex="1" minW="0">
                                                    <Text fontWeight="600" lineClamp={1}>
                                                        {addon.name}
                                                    </Text>
                                                    {disabled && (
                                                        <Text fontSize="xs" color="red.400">
                                                            Недоступно на эти даты
                                                        </Text>
                                                    )}
                                                </Flex>

                                                {checked && (
                                                    <Flex
                                                        align="center"
                                                        gap="7px"
                                                        flexShrink={0}
                                                        onClick={(e) => e.stopPropagation()}
                                                    >
                                                        <Center
                                                            as="button"
                                                            h="26px"
                                                            w="26px"
                                                            rounded="full"
                                                            borderWidth="1.5px"
                                                            borderColor="gray"
                                                            color="text"
                                                            onClick={() =>
                                                                setAddonQuantity(addon.product_id, qty - 1)
                                                            }
                                                        >
                                                            <FiMinus size={13} />
                                                        </Center>
                                                        <Text minW="16px" textAlign="center" fontWeight="700">
                                                            {qty}
                                                        </Text>
                                                        <Center
                                                            as="button"
                                                            h="26px"
                                                            w="26px"
                                                            rounded="full"
                                                            borderWidth="1.5px"
                                                            borderColor={qty >= max ? 'gray' : 'accent'}
                                                            color={qty >= max ? 'gray' : 'accent'}
                                                            opacity={qty >= max ? 0.5 : 1}
                                                            cursor={qty >= max ? 'not-allowed' : 'pointer'}
                                                            onClick={() =>
                                                                setAddonQuantity(addon.product_id, qty + 1)
                                                            }
                                                        >
                                                            <FiPlus size={13} />
                                                        </Center>
                                                    </Flex>
                                                )}

                                                <Text fontWeight="700" color="accent" flexShrink={0}>
                                                    +{formatPriceK(addon.price)}
                                                    <Text as="span" fontSize="xs" opacity={0.7} color="text" ml="2px">
                                                        {addon.price_mode === 'flat' ? 'разово' : '/сутки'}
                                                    </Text>
                                                </Text>
                                            </Flex>
                                        )
                                    })}
                                </Flex>
                            </Box>
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
                    {canAddToBasket && (
                        <CustomNumberInput
                            value={tempQuantity.toString()}
                            max={maxSelectableQuantity}
                            setQuantity={(value) => {
                                setTempQuantity(value)
                            }}
                        />
                    )}

                    <ToBasketButton
                        currentPrice={currentPrice}
                        productId={selectedProduct.product_id}
                        quantity={tempQuantity}
                        disabled={availabilityLoading || isUnavailableForDates}
                        unavailable={isUnavailableForDates}
                        addons={selectedAddons.map((a) => ({
                            product_id: a.product_id,
                            quantity: a.quantity,
                        }))}
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
