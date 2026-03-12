const ensureTrailingSlash = (value: string) =>
    value.endsWith('/') ? value : `${value}/`

const normalizeApiBaseUrl = (rawValue?: string) => {
    const value = rawValue?.trim() || '/'

    if (typeof window !== 'undefined' && window.location.protocol === 'https:' && value.startsWith('http://')) {
        const httpsValue = `https://${value.slice('http://'.length)}`

        try {
            const normalizedUrl = new URL(httpsValue)

            if (normalizedUrl.origin === window.location.origin) {
                return ensureTrailingSlash(normalizedUrl.pathname)
            }
        } catch {
            return ensureTrailingSlash(httpsValue)
        }

        return ensureTrailingSlash(httpsValue)
    }

    return ensureTrailingSlash(value)
}

const base = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL)

export default base
export const ADMIN_URL = `${base}admin/`
