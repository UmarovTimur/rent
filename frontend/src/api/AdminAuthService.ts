import adminClient from '@/api/adminClient'

export interface AdminInfo {
    username: string
}

export const AdminAuthService = {
    async me(): Promise<AdminInfo> {
        const response = await adminClient.get<AdminInfo>('api/v1/admin/me')
        return response.data
    },

    async login(username: string, password: string): Promise<AdminInfo> {
        const response = await adminClient.post<AdminInfo>('api/v1/admin/login', { username, password })
        return response.data
    },

    async logout(): Promise<void> {
        await adminClient.post('api/v1/admin/logout')
    },
}
