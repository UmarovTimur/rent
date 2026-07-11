import axios from 'axios'

// Attach the Telegram initData to every backend request so the server can verify
// the caller's identity (see require_telegram_user on the backend). The raw
// initData string is signed by Telegram; the backend derives the user id from it
// and ignores any client-supplied user_id. Applied to the default axios instance
// used by all data services; adminClient (session-cookie auth) is separate.
axios.interceptors.request.use((config) => {
    const initData = window.Telegram?.WebApp?.initData
    if (initData) {
        config.headers['X-Telegram-Init-Data'] = initData
    }
    return config
})
