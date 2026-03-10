const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/'

const base = API_BASE_URL.endsWith('/') ? API_BASE_URL : `${API_BASE_URL}/`
export default base
export const ADMIN_URL = `${base}admin/`
