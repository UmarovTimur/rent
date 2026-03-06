export const toWholePrice = (value: number | null | undefined): number => {
    if (typeof value !== 'number' || Number.isNaN(value)) return 0
    return Math.trunc(value)
}

export const formatPriceK = (value: number | null | undefined): string =>
    `${toWholePrice(value)}к`
