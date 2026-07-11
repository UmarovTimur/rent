import axios from 'axios'
import API_BASE_URL from '@/config'

// Admin surfaces (rental calendar) authenticate with the shared admin session
// cookie set by the login endpoint / SQLAdmin panel, so requests must send credentials.
const adminClient = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true,
})

export default adminClient
