import { Flex } from '@chakra-ui/react'
import { useEffect, useState } from 'react'
import PromoDialog from './PromoDialog'
import { Promo, PromoService } from '@/api/PromoService'

const STORAGE_KEY = 'promoViewed'

const loadViewed = (): Set<number> => {
    try {
        return new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'))
    } catch {
        return new Set()
    }
}

export default function PromoGroup() {
    const [promos, setPromos] = useState<Promo[]>([])
    const [viewed, setViewed] = useState<Set<number>>(loadViewed)

    useEffect(() => {
        PromoService.getPromos()
            .then(setPromos)
            .catch((error) => console.error('Не удалось загрузить промо:', error))
    }, [])

    const markViewed = (promoId: number) => {
        setViewed((prev) => {
            if (prev.has(promoId)) return prev
            const next = new Set(prev).add(promoId)
            localStorage.setItem(STORAGE_KEY, JSON.stringify([...next]))
            return next
        })
    }

    if (promos.length === 0) return null

    return (
        <Flex gap="8px" overflowX="auto" scrollbar="hidden" w="100%" px="gap">
            {promos.map((promo) => (
                <PromoDialog
                    key={promo.promo_id}
                    frames={promo.frames}
                    isViewed={viewed.has(promo.promo_id)}
                    onView={() => markViewed(promo.promo_id)}
                />
            ))}
        </Flex>
    )
}
