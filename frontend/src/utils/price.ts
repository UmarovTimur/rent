export const toWholePrice = (value: number | null | undefined): number => {
    if (typeof value !== 'number' || Number.isNaN(value)) return 0
    return Math.trunc(value)
}

export const formatPriceK = (value: number | null | undefined): string => {
    const n = toWholePrice(value)
    if (n >= 1_000_000) {
        return n.toLocaleString('en-US').replace(/,/g, ' ')
    }
    return `${Math.round(n / 1000)}к`
}
