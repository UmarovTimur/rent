import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useRef,
    useState,
} from 'react'
import { Basket, BasketItemAddon, AddonSelection } from '@/types/Basket'
import { BasketService } from '@/api/BasketService'
import { ProductService } from '@/api/ProductService'
import { Product, Ingredient } from '@/types/Products'
import { useTripDates } from '@/contexts/TripDatesContext'
import { useTranslation } from '@/i18n/LanguageContext'

export type ProductWithQuantity = Product & {
    quantity: number
    basket_item_id: number
    rental_start?: string | null
    rental_end?: string | null
    addons?: BasketItemAddon[]
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
        rentalEnd?: string,
        addons?: AddonSelection[]
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

export const BasketProvider = ({
    children,
    userId,
}: {
    children: React.ReactNode
    userId: number
}) => {
    const { hasValidRange, rentalStartIso, rentalEndIso, tripDatesTouched } = useTripDates()
    const { t } = useTranslation()
    const [basket, setBasket] = useState<Basket | null>(null)
    const [allProducts, setAllProducts] = useState<Product[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const migrateInFlightRef = useRef(false)
    const lastMigratedKeyRef = useRef('')

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
                addons: item.addons ?? [],
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
            setError(t('basketUpdateError'))
            console.error('Ошибка обновления корзины:', err)
        } finally {
            setLoading(false)
        }
    }, [userId])

    const addToBasket = async (
        productId: number,
        quantity: number = 1,
        rentalStart?: string,
        rentalEnd?: string,
        addons: AddonSelection[] = []
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
                setError(t('maxQty99'))
                return false
            }

            await BasketService.addItem(
                userId,
                productId,
                quantity,
                rentalStart,
                rentalEnd,
                addons
            )
            await refreshBasket()
            return true
        } catch (err) {
            setError(t('basketAddError'))
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
                setError(t('maxQty99'))
                return
            }

            await BasketService.changeQuantity(basketItemId, quantity)
            await refreshBasket()
        } catch (err) {
            setError(t('basketQtyError'))
            console.error('Ошибка изменения количества:', err)
        } finally {
            setLoading(false)
        }
    }

    // When the user changes the trip window, atomically set the dates and migrate
    // existing items into the new window on the server (one request), then adopt
    // the returned basket. Gated on `tripDatesTouched` so the untouched default
    // never overwrites the server; skipped when the window already matches.
    useEffect(() => {
        if (!tripDatesTouched || !hasValidRange || !rentalStartIso || !rentalEndIso) {
            return
        }

        const serverStartIso = normalizeIso(basket?.rental_start)
        const serverEndIso = normalizeIso(basket?.rental_end)
        if (serverStartIso === rentalStartIso && serverEndIso === rentalEndIso) {
            return
        }

        const key = `${rentalStartIso}|${rentalEndIso}`
        if (lastMigratedKeyRef.current === key) return

        let cancelled = false
        const timeout = window.setTimeout(async () => {
            if (migrateInFlightRef.current) return
            migrateInFlightRef.current = true
            lastMigratedKeyRef.current = key
            setLoading(true)
            setError('')
            try {
                const updated = await BasketService.setBasketDatesAndMigrate(
                    userId,
                    rentalStartIso,
                    rentalEndIso
                )
                if (!cancelled) setBasket(updated)
            } catch (err) {
                // Allow a retry on the next change.
                lastMigratedKeyRef.current = ''
                if (!cancelled) setError(t('basketRecalcError'))
                console.error('Ошибка пересчета корзины при смене дат:', err)
            } finally {
                migrateInFlightRef.current = false
                if (!cancelled) setLoading(false)
            }
        }, 500)

        return () => {
            cancelled = true
            window.clearTimeout(timeout)
        }
    }, [basket, tripDatesTouched, hasValidRange, rentalStartIso, rentalEndIso, userId])

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
            setError(t('basketRemoveError'))
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
