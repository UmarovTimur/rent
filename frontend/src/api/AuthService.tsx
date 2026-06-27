import axios from 'axios'
import API_BASE_URL from '@/config'

export interface TokenResponse {
    access_token: string
    user_id: number
}

export interface PhoneCheckResponse {
    exists: boolean
    first_name?: string
}

export const AuthService = {
    checkPhone: async (phone_number: string): Promise<PhoneCheckResponse> => {
        const { data } = await axios.post<PhoneCheckResponse>(`${API_BASE_URL}api/v1/auth/phone/check`, { phone_number })
        return data
    },

    loginByPhone: async (phone_number: string): Promise<TokenResponse> => {
        const { data } = await axios.post<TokenResponse>(`${API_BASE_URL}api/v1/auth/phone/login`, { phone_number })
        return data
    },

    registerByPhone: async (phone_number: string, first_name: string, last_name?: string): Promise<TokenResponse> => {
        const { data } = await axios.post<TokenResponse>(`${API_BASE_URL}api/v1/auth/phone/register`, {
            phone_number,
            first_name,
            last_name: last_name || null,
        })
        return data
    },

    saveSession: (token: string, userId: number) => {
        localStorage.setItem('auth_token', token)
        localStorage.setItem('web_user_id', String(userId))
    },

    getStoredUserId: (): number | null => {
        const v = localStorage.getItem('web_user_id')
        return v ? parseInt(v, 10) : null
    },

    clearSession: () => {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('web_user_id')
    },
}
