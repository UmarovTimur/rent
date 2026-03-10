import { Text, Flex, Image, Heading, Center } from '@chakra-ui/react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useBasketContext, ProductWithQuantity } from '@/contexts/BasketContext'
import CustomNumberInput from '@/assets/product/components/CustomNumberInput'
import DeleteProductButton from './DeleteProductButton.tsx'
import ConfirmationDialog from './ConfirmationDialog'
import { useDrawer } from '@/contexts/DrawerContext.tsx'
import { RentalService } from '@/api/RentalService'
import {
    formatRentalDaysRu,
    formatRentalDateTimeRange,
    getRoundedRentalDaysFromIso,
} from '@/utils/rental'
import { formatPriceK } from '@/utils/price'

type CardProps = {
    price: ProductWithQuantity
}

export default function BasketCard({ price }: CardProps) {
    const { basket, basketProducts, updateQuantity, removeFromBasket } =
        useBasketContext()
    const { onClose } = useDrawer()
    const [localQuantity, setLocalQuantity] = useState(price.quantity)
    const updateTimeoutRef = useRef<number | null>(null)
    const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
    const [availableQuantity, setAvailableQuantity] = useState<number | null>(null)

    useEffect(() => {
        setLocalQuantity(price.quantity)
    }, [price.quantity])

    const reservedInBasketQuantity = useMemo(() => {
        if (!price.rental_start || !price.rental_end) return 0

        const currentStartIso = new Date(price.rental_start).toISOString()
        const currentEndIso = new Date(price.rental_end).toISOString()

        return basketProducts.reduce((sum, item) => {
            if (item.basket_item_id === price.basket_item_id) return sum
            if (item.product_id !== price.product_id) return sum
            if (!item.rental_start || !item.rental_end) return sum

            const sameStart =
                new Date(item.rental_start).toISOString() === currentStartIso
            const sameEnd = new Date(item.rental_end).toISOString() === currentEndIso

            return sameStart && sameEnd ? sum + item.quantity : sum
        }, 0)
    }, [
        basketProducts,
        price.basket_item_id,
        price.product_id,
        price.rental_end,
        price.rental_start,
    ])

    const remainingAvailableQuantity =
        availableQuantity == null
            ? null
            : Math.max(0, availableQuantity - reservedInBasketQuantity)

    useEffect(() => {
        if (!price.rental_start || !price.rental_end) {
            setAvailableQuantity(null)
            return
        }
        const rentalStart = price.rental_start
        const rentalEnd = price.rental_end

        let cancelled = false

        const loadAvailability = async () => {
            try {
                const calendar = await RentalService.getProductCalendar(
                    price.product_id,
                    new Date(rentalStart).toISOString(),
                    new Date(rentalEnd).toISOString()
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
            }
        }

        loadAvailability()

        return () => {
            cancelled = true
        }
    }, [price.product_id, price.rental_end, price.rental_start])

    const maxSelectableQuantity =
        remainingAvailableQuantity == null
            ? 99
            : Math.max(1, Math.min(99, remainingAvailableQuantity))

    const handleQuantityChange = useCallback(
        (newQuantity: number) => {
            const clampedQuantity = Math.min(
                Math.max(newQuantity, 1),
                maxSelectableQuantity
            )
            setLocalQuantity(clampedQuantity)

            if (updateTimeoutRef.current) clearTimeout(updateTimeoutRef.current)

            updateTimeoutRef.current = window.setTimeout(async () => {
                try {
                    await updateQuantity(price.basket_item_id, clampedQuantity)
                } catch (error) {
                    setLocalQuantity(price.quantity)
                    console.error(error)
                }
            }, 500)
        },
        [maxSelectableQuantity, price.basket_item_id, price.quantity, updateQuantity]
    )

    useEffect(() => {
        if (remainingAvailableQuantity == null) return
        if (localQuantity <= maxSelectableQuantity) return

        handleQuantityChange(maxSelectableQuantity)
    }, [
        handleQuantityChange,
        localQuantity,
        maxSelectableQuantity,
        remainingAvailableQuantity,
    ])

    useEffect(() => {
        return () => {
            if (updateTimeoutRef.current) clearTimeout(updateTimeoutRef.current)
        }
    }, [])

    const billedDays = useMemo(
        () => getRoundedRentalDaysFromIso(price.rental_start, price.rental_end) ?? 1,
        [price.rental_end, price.rental_start]
    )
    const lineTotal = price.price * localQuantity * billedDays

    const handleDeleteConfirm = async () => {
        await removeFromBasket(price.basket_item_id)
        if (basket?.items.length === 1) onClose()
    }

    return (
        <>
            <ConfirmationDialog
                isOpen={isDeleteDialogOpen}
                onClose={() => setIsDeleteDialogOpen(false)}
                onConfirm={handleDeleteConfirm}
                title="Удаление товара"
                message={`Удалить "${price.name}" из корзины?`}
            />

            <Flex
                rounded="26px"
                overflow="hidden"
                bg="card"
                w="full"
                h="180px"
                justifyContent="space-between"
                p="0"
                gap="0"
            >
                {price.image_url && (
                    <Image
                        src={`products/${price.image_url}`}
                        h="full"
                        minW="122px"
                        marginRight="20px"
                        alt={price.name}
                    />
                )}
                <Flex
                    flexDirection="column"
                    flex="2"
                    height="calc(full - 12px)"
                    py="6px"
                    justifyContent="space-between"
                    position="relative"
                >
                    <DeleteProductButton onDelete={() => setIsDeleteDialogOpen(true)} />

                    <Flex paddingRight="45px" alignItems="flex-end" gap="8px">
                        <Heading color="text" size="2xl" fontWeight="700">
                            {price.name}
                        </Heading>
                    </Flex>

                    <Text
                        color="text"
                        fontWeight="400"
                        opacity="50%"
                        textAlign="left"
                        lineHeight="15px"
                        fontSize="xs"
                        minH="15px"
                    >
                        {formatRentalDateTimeRange(price.rental_start, price.rental_end)}
                    </Text>

                    <Text
                        color="accent"
                        fontWeight="600"
                        textAlign="left"
                        w="85%"
                        lineHeight="15px"
                        fontSize="xs"
                        minH="15px"
                        mb="4px"
                    >
                        {formatRentalDaysRu(billedDays)}
                    </Text>

                    <Flex
                        justifyContent="space-between"
                        alignItems="center"
                        w="full"
                        h="fit"
                    >
                        <Center
                            h="32px"
                            bg="back"
                            color="text"
                            px="20px"
                            rounded="full"
                            fontSize="xs"
                            fontWeight="500"
                        >
                            {formatPriceK(lineTotal)}
                        </Center>

                        <CustomNumberInput
                            small={true}
                            value={localQuantity.toString()}
                            max={maxSelectableQuantity}
                            setQuantity={handleQuantityChange}
                        />
                    </Flex>
                </Flex>
            </Flex>
        </>
    )
}
