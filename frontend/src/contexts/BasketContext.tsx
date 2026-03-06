import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useRef,
    useState,
} from 'react'
import { Basket, BasketItem } from '@/types/Basket'
import { BasketService } from '@/api/BasketService'
import { ProductService } from '@/api/ProductService'
import { RentalService } from '@/api/RentalService'
import { Product, Ingredient } from '@/types/Products'
import { useTripDates } from '@/contexts/TripDatesContext'

export type ProductWithQuantity = Product & {
    quantity: number
    basket_item_id: number
    rental_start?: string | null
    rental_end?: string | null
}

type BasketContextType = {
    basket: Basket | null
    loading: boolean
    error: string
    basketProducts: ProductWithQuantity[]
    refreshBasket: () => Promise<void>
    addToBasket: (
        productId: number,
        quantity: number,
        rentalStart?: string,
        rentalEnd?: string
    ) => Promise<boolean>
    updateQuantity: (basketItemId: number, quantity: number) => Promise<void>
    clearError: () => void
    removeFromBasket: (basketItemId: number) => Promise<Basket | null>
    addCustomProduct: (_ingredients: Ingredient[], _totalPrice: number) => Promise<boolean>
}

const BasketContext = createContext<BasketContextType>({
    basket: null,
    loading: false,
    error: '',
    basketProducts: [],
    refreshBasket: async () => {},
    addToBasket: async () => false,
    updateQuantity: async () => {},
    clearError: () => {},
    removeFromBasket: async () => null,
    addCustomProduct: async () => false,
})

const normalizeIso = (value?: string | null): string | null => {
    if (!value) return null
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) return null
    return parsed.toISOString()
}

const hasSameRentalWindow = (
    item: BasketItem,
    rentalStartIso: string,
    rentalEndIso: string
): boolean => {
    return (
        normalizeIso(item.rental_start) === rentalStartIso &&
        normalizeIso(item.rental_end) === rentalEndIso
    )
}

const getAvailableQuantityForRange = async (
    productId: number,
    rentalStartIso: string,
    rentalEndIso: string
): Promise<number> => {
    const calendar = await RentalService.getProductCalendar(
        productId,
        rentalStartIso,
        rentalEndIso
    )

    if (calendar.slots.length === 0) return 0

    const minAvailable = Math.min(
        ...calendar.slots.map((slot) =>
            slot.is_available ? slot.available_quantity : 0
        )
    )

    return Math.max(0, minAvailable)
}

export const BasketProvider = ({
    children,
    userId,
}: {
    children: React.ReactNode
    userId: number
}) => {
    const { hasValidRange, rentalStartIso, rentalEndIso } = useTripDates()
    const [basket, setBasket] = useState<Basket | null>(null)
    const [allProducts, setAllProducts] = useState<Product[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const autoSyncInProgressRef = useRef(false)
    const lastAutoSyncKeyRef = useRef('')

    useEffect(() => {
        const loadProducts = async () => {
            try {
                const products = await ProductService.fetchAllProducts()
                setAllProducts(products)
            } catch (err) {
                console.error('Ошибка загрузки товаров:', err)
            }
        }
        loadProducts()
    }, [])

    const getBasketProducts = (): ProductWithQuantity[] => {
        if (!basket || !allProducts.length) return []

        const mapped: Array<ProductWithQuantity | null> = basket.items.map((item) => {
            const product = allProducts.find((p) => p.product_id === item.product_id)
            if (!product) return null

            return {
                ...product,
                quantity: item.quantity,
                basket_item_id: item.basket_item_id,
                rental_start: item.rental_start ?? null,
                rental_end: item.rental_end ?? null,
            }
        })

        return mapped
            .filter((p): p is ProductWithQuantity => p !== null)
            .sort((a, b) => {
                const priceCompare = a.price - b.price
                if (priceCompare !== 0) return priceCompare

                const nameCompare = a.name.localeCompare(b.name)
                if (nameCompare !== 0) return nameCompare

                return `${a.rental_start || ''}${a.rental_end || ''}`.localeCompare(
                    `${b.rental_start || ''}${b.rental_end || ''}`
                )
            })
    }

    const refreshBasket = useCallback(async () => {
        setLoading(true)
        setError('')
        try {
            const data = await BasketService.getBasket(userId)
            setBasket(data)
        } catch (err) {
            setError('Ошибка обновления корзины')
            console.error('Ошибка обновления корзины:', err)
        } finally {
            setLoading(false)
        }
    }, [userId])

    const addToBasket = async (
        productId: number,
        quantity: number = 1,
        rentalStart?: string,
        rentalEnd?: string
    ): Promise<boolean> => {
        setLoading(true)
        setError('')
        try {
            const existingItem = basket?.items.find(
                (item) =>
                    item.product_id === productId &&
                    (item.rental_start || undefined) === rentalStart &&
                    (item.rental_end || undefined) === rentalEnd
            )
            const currentQuantity = existingItem?.quantity || 0
            const newTotal = currentQuantity + quantity

            if (newTotal > 99) {
                setError('Максимальное количество товара в корзине - 99')
                return false
            }

            await BasketService.addItem(
                userId,
                productId,
                quantity,
                rentalStart,
                rentalEnd
            )
            await refreshBasket()
            return true
        } catch (err) {
            setError('Ошибка добавления в корзину')
            console.error('Ошибка добавления в корзину:', err)
            return false
        } finally {
            setLoading(false)
        }
    }

    const updateQuantity = async (basketItemId: number, quantity: number) => {
        setLoading(true)
        setError('')
        try {
            if (quantity > 99) {
                setError('Максимальное количество товара - 99')
                return
            }

            await BasketService.changeQuantity(basketItemId, quantity)
            await refreshBasket()
        } catch (err) {
            setError('Ошибка изменения количества')
            console.error('Ошибка изменения количества:', err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (
            !basket ||
            !hasValidRange ||
            !rentalStartIso ||
            !rentalEndIso ||
            loading ||
            autoSyncInProgressRef.current
        ) {
            return
        }

        const rentalItems = basket.items.filter(
            (item) => item.rental_start && item.rental_end
        )
        const staleRentalItems = rentalItems.filter(
            (item) => !hasSameRentalWindow(item, rentalStartIso, rentalEndIso)
        )

        if (staleRentalItems.length === 0) return

        const syncKey = [
            rentalStartIso,
            rentalEndIso,
            ...rentalItems.map(
                (item) =>
                    `${item.basket_item_id}:${item.product_id}:${item.quantity}:${item.rental_start || ''}:${item.rental_end || ''}`
            ),
        ].join('|')

        if (lastAutoSyncKeyRef.current === syncKey) return
        lastAutoSyncKeyRef.current = syncKey

        let cancelled = false

        const syncBasketForCurrentRentalRange = async () => {
            autoSyncInProgressRef.current = true
            setLoading(true)
            setError('')

            try {
                const itemsByProduct = new Map<number, BasketItem[]>()
                for (const item of rentalItems) {
                    const current = itemsByProduct.get(item.product_id)
                    if (current) {
                        current.push(item)
                    } else {
                        itemsByProduct.set(item.product_id, [item])
                    }
                }

                for (const [productId, items] of itemsByProduct) {
                    const staleItems = items.filter(
                        (item) =>
                            !hasSameRentalWindow(
                                item,
                                rentalStartIso,
                                rentalEndIso
                            )
                    )
                    if (staleItems.length === 0) continue

                    const currentWindowItems = items.filter((item) =>
                        hasSameRentalWindow(item, rentalStartIso, rentalEndIso)
                    )

                    const totalQuantity = items.reduce(
                        (sum, item) => sum + item.quantity,
                        0
                    )
                    const currentWindowQuantity = currentWindowItems.reduce(
                        (sum, item) => sum + item.quantity,
                        0
                    )

                    const availableQuantity = await getAvailableQuantityForRange(
                        productId,
                        rentalStartIso,
                        rentalEndIso
                    )
                    const targetQuantity = Math.min(
                        totalQuantity,
                        availableQuantity,
                        99
                    )

                    const quantityToAdd = Math.max(
                        0,
                        targetQuantity - currentWindowQuantity
                    )
                    if (quantityToAdd > 0) {
                        await BasketService.addItem(
                            userId,
                            productId,
                            quantityToAdd,
                            rentalStartIso,
                            rentalEndIso
                        )
                    }

                    let excessCurrentQuantity = Math.max(
                        0,
                        currentWindowQuantity - targetQuantity
                    )
                    if (excessCurrentQuantity > 0) {
                        const sortedCurrentItems = [...currentWindowItems].sort(
                            (a, b) => b.basket_item_id - a.basket_item_id
                        )

                        for (const currentItem of sortedCurrentItems) {
                            if (excessCurrentQuantity <= 0) break

                            if (currentItem.quantity <= excessCurrentQuantity) {
                                await BasketService.removeItem(
                                    currentItem.basket_item_id
                                )
                                excessCurrentQuantity -= currentItem.quantity
                                continue
                            }

                            await BasketService.changeQuantity(
                                currentItem.basket_item_id,
                                currentItem.quantity - excessCurrentQuantity
                            )
                            excessCurrentQuantity = 0
                        }
                    }

                    for (const staleItem of staleItems) {
                        await BasketService.removeItem(staleItem.basket_item_id)
                    }
                }

                const updatedBasket = await BasketService.getBasket(userId)
                if (!cancelled) {
                    setBasket(updatedBasket)
                }
            } catch (err) {
                if (!cancelled) {
                    setError('Ошибка пересчета корзины при смене дат')
                }
                console.error('Ошибка пересчета корзины при смене дат:', err)
            } finally {
                autoSyncInProgressRef.current = false
                if (!cancelled) {
                    setLoading(false)
                }
            }
        }

        void syncBasketForCurrentRentalRange()

        return () => {
            cancelled = true
        }
    }, [basket, hasValidRange, loading, rentalStartIso, rentalEndIso, userId])

    useEffect(() => {
        void refreshBasket()
    }, [refreshBasket])

    const clearError = () => setError('')

    const removeFromBasket = async (basketItemId: number) => {
        setLoading(true)
        setError('')
        try {
            await BasketService.removeItem(basketItemId)
            const updatedBasket = await BasketService.getBasket(userId)
            setBasket(updatedBasket)
            return updatedBasket
        } catch (err) {
            setError('Ошибка удаления товара')
            console.error('Ошибка удаления товара:', err)
            throw err
        } finally {
            setLoading(false)
        }
    }

    const addCustomProduct = async (): Promise<boolean> => {
        setError('Конструктор отключен в режиме аренды')
        return false
    }

    return (
        <BasketContext.Provider
            value={{
                basket,
                loading,
                error,
                basketProducts: getBasketProducts(),
                refreshBasket,
                addToBasket,
                updateQuantity,
                clearError,
                removeFromBasket,
                addCustomProduct,
            }}
        >
            {children}
        </BasketContext.Provider>
    )
}

export const useBasketContext = () => useContext(BasketContext)
