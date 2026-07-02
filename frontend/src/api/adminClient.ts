import axios from 'axios'
import { retrieveRawInitData } from '@telegram-apps/sdk'
import API_BASE_URL from '@/config'

const adminClient = axios.create({
    baseURL: API_BASE_URL,
})

adminClient.interceptors.request.use((config) => {
    try {
        const initData = retrieveRawInitData()
        if (initData) {
            config.headers['X-Telegram-Init-Data'] = initData
        }
    } catch (error) {
        console.error('Failed to retrieve Telegram initData:', error)
    }
    return config
})

export default adminClient
