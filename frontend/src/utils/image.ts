/**
 * Resolves a product image_url to a usable src string.
 *
 * New uploads from the admin store absolute paths like /media/products/abc.jpg
 * Old data may store relative paths like df/1.jpg (served from public/products/)
 */
export function productImageSrc(imageUrl: string | null | undefined, fallback = 'shava.png'): string {
    if (!imageUrl) return fallback
    // Absolute URL or path — use as-is
    if (imageUrl.startsWith('/') || imageUrl.startsWith('http')) return imageUrl
    // Legacy relative path — prepend public folder prefix
    return `products/${imageUrl}`
}
