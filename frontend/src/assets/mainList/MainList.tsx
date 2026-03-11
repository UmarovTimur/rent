import { Alert, Box, Flex, Skeleton, Text } from '@chakra-ui/react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import Fuse from 'fuse.js'
import { useInView } from 'react-intersection-observer'
import CategoryTitle from './components/CategoryTitle'
import { useProducts } from '@/hooks/useProducts'
import Card from './components/Card'
import ProductPage from '@/assets/product/ProductPage'
import MotionDrawer from '@/assets/MotionDrawer'
import { RentalService } from '@/api/RentalService'
import { useTripDates } from '@/contexts/TripDatesContext'
import { Product } from '@/types/Products'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'

type MainListProps = {
    categories: string[]
    activeCategory: string
    setActiveCategory: (category: string) => void
    searchQuery: string
}

type CategoryProducts = {
    category: string
    products: Product[]
}

const CARD_HEIGHT_PX = 180
const CARD_VERTICAL_GAP_PX = 16
const OVERSCAN_ITEMS = 6
const OVERSCAN_PX = (CARD_HEIGHT_PX + CARD_VERTICAL_GAP_PX) * OVERSCAN_ITEMS

type VirtualizedProductCardProps = {
    product: Product
}

function VirtualizedProductCard({ product }: VirtualizedProductCardProps) {
    const [isDrawerOpen, setIsDrawerOpen] = useState(false)
    const { ref, inView } = useInView({
        threshold: 0,
        rootMargin: `${OVERSCAN_PX}px 0px ${OVERSCAN_PX}px 0px`,
    })

    const shouldRenderCard = inView || isDrawerOpen

    return (
        <Box ref={ref} h={`${CARD_HEIGHT_PX}px`} w="full">
            {shouldRenderCard ? (
                <MotionDrawer
                    trigger={<Card product={product} />}
                    onOpenChange={setIsDrawerOpen}
                >
                    <ProductPage product={product} />
                </MotionDrawer>
            ) : null}
        </Box>
    )
}

export default function MainList({
    categories,
    activeCategory,
    setActiveCategory,
    searchQuery,
}: MainListProps) {
    const { loading, error, getProductsByCategory } = useProducts()
    const { hasValidRange, rentalStartIso, rentalEndIso } = useTripDates()

    const [visibleCategories, setVisibleCategories] = useState<string[]>([])
    const [isAutoChangeBlocked, setIsAutoChangeBlocked] = useState(false)
    const [availableProductIds, setAvailableProductIds] = useState<Record<number, boolean>>({})
    const [availabilityLoading, setAvailabilityLoading] = useState(false)

    const normalizedSearchQuery = searchQuery.trim()
    const debouncedSearchQuery = useDebouncedValue(normalizedSearchQuery, 1000)

    const handleVisibilityChange = useCallback(
        (category: string, isVisible: boolean) => {
            setVisibleCategories((prev) => {
                const next = isVisible
                    ? [...prev.filter((c) => c !== category), category]
                    : prev.filter((c) => c !== category)

                if (
                    next.length === prev.length &&
                    next.every((value, index) => value === prev[index])
                ) {
                    return prev
                }

                return next
            })
        },
        []
    )

    useEffect(() => {
        setIsAutoChangeBlocked(true)

        const timeout = window.setTimeout(() => {
            setIsAutoChangeBlocked(false)
        }, 700)

        return () => window.clearTimeout(timeout)
    }, [activeCategory])

    useEffect(() => {
        if (isAutoChangeBlocked) return
        if (!categories.length) return

        const nextActiveCategory =
            visibleCategories.length > 0 ? visibleCategories[0] : categories[0]

        if (nextActiveCategory !== activeCategory) {
            setActiveCategory(nextActiveCategory)
        }
    }, [
        visibleCategories,
        isAutoChangeBlocked,
        categories,
        activeCategory,
        setActiveCategory,
    ])

    const uniqueProductCards = useMemo(() => {
        if (loading) return []

        const all = categories.flatMap((category) => getProductsByCategory(category))
        const seen = new Set<number>()

        return all.filter((product) => {
            const id = product.product_id
            if (seen.has(id)) return false
            seen.add(id)
            return true
        })
    }, [categories, getProductsByCategory, loading])

    useEffect(() => {
        if (loading || !hasValidRange || !rentalStartIso || !rentalEndIso) return

        let cancelled = false

        const run = async () => {
            setAvailabilityLoading(true)
            try {
                const results = await Promise.all(
                    uniqueProductCards.map(async (product) => {
                        try {
                            const calendar = await RentalService.getProductCalendar(
                                product.product_id,
                                rentalStartIso,
                                rentalEndIso
                            )

                            const available =
                                calendar.slots.length > 0 &&
                                calendar.slots.every(
                                    (slot) => slot.is_available && slot.available_quantity > 0
                                )

                            return [product.product_id, available] as const
                        } catch {
                            return [product.product_id, false] as const
                        }
                    })
                )

                if (!cancelled) {
                    setAvailableProductIds(Object.fromEntries(results))
                }
            } finally {
                if (!cancelled) setAvailabilityLoading(false)
            }
        }

        run()

        return () => {
            cancelled = true
        }
    }, [loading, hasValidRange, rentalStartIso, rentalEndIso, uniqueProductCards])

    useEffect(() => {
        window.scrollTo({ top: 0, behavior: 'auto' })
    }, [normalizedSearchQuery])

    const availableProductsByCategory = useMemo<CategoryProducts[]>(() => {
        if (loading) return []

        return categories.map((category) => {
            const products = getProductsByCategory(category).filter(
                (product) =>
                    !hasValidRange ||
                    availableProductIds[product.product_id] === true
            )

            return {
                category,
                products,
            }
        })
    }, [categories, getProductsByCategory, hasValidRange, availableProductIds, loading])

    const searchableProducts = useMemo(() => {
        const all = availableProductsByCategory.flatMap((entry) => entry.products)
        const seen = new Set<number>()

        return all.filter((product) => {
            if (seen.has(product.product_id)) return false
            seen.add(product.product_id)
            return true
        })
    }, [availableProductsByCategory])

    const matchedProductIds = useMemo(() => {
        if (!debouncedSearchQuery) return null

        const fuse = new Fuse(searchableProducts, {
            keys: ['name', 'description'],
            threshold: 0.35,
            ignoreLocation: true,
        })

        return new Set(
            fuse.search(debouncedSearchQuery).map((result) => result.item.product_id)
        )
    }, [searchableProducts, debouncedSearchQuery])

    const filteredProductsByCategory = useMemo(() => {
        if (!matchedProductIds) return availableProductsByCategory

        return availableProductsByCategory
            .map((entry) => ({
                ...entry,
                products: entry.products.filter((product) =>
                    matchedProductIds.has(product.product_id)
                ),
            }))
            .filter((entry) => entry.products.length > 0)
    }, [availableProductsByCategory, matchedProductIds])

    const showEmptySearchFallback =
        Boolean(debouncedSearchQuery) && filteredProductsByCategory.length === 0

    if (error) {
        return (
            <Alert.Root status="error">
                <Alert.Indicator />
                <Alert.Title>{error}</Alert.Title>
            </Alert.Root>
        )
    }

    return (
        <Flex px="gap" flexDirection="column" gap="gap" pb="gap">
            {loading ? (
                <>
                    <Skeleton h="32px" rounded="26px" />
                    {Array(6)
                        .fill(0)
                        .map((_, i) => (
                            <Skeleton key={i} h="140px" rounded="26px" />
                        ))}
                </>
            ) : showEmptySearchFallback ? (
                <Box
                    bg="card"
                    borderWidth="1px"
                    borderColor="gray"
                    rounded="26px"
                    p="24px"
                >
                    <Text textAlign="center" fontWeight="600" opacity={0.8}>
                        Ничего не найдено
                    </Text>
                </Box>
            ) : (
                filteredProductsByCategory.map(({ category, products }) => (
                    <Flex
                        id={category}
                        key={category}
                        direction="column"
                        gap="gap"
                        minH="180px"
                    >
                        <CategoryTitle
                            category={category}
                            onVisibilityChange={handleVisibilityChange}
                        />

                        {products.map((product) => (
                            <VirtualizedProductCard
                                key={product.product_id}
                                product={product}
                            />
                        ))}

                        {!availabilityLoading &&
                            !debouncedSearchQuery &&
                            products.length === 0 && (
                                <Text opacity={0.6} fontSize="sm" px="8px">
                                    Нет доступных товаров на выбранные даты
                                </Text>
                            )}
                    </Flex>
                ))
            )}
        </Flex>
    )
}
