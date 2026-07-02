import { Provider } from '@/components/ui/provider'
import React, { Suspense, lazy } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import '@fontsource-variable/montserrat/index.css'

// Admin calendar is lazy-loaded so its code (FullCalendar, etc.) stays out of the main client bundle.
const AdminApp = lazy(() => import('./AdminApp'))
const isAdminRoute = window.location.pathname.startsWith('/app/admin')

// Some Telegram WebView clients restore a previously opened Mini App from bfcache instead of doing
// a fresh navigation when it's reopened (e.g. via the persistent Menu button after /admin_calendar
// was used). A restored page never re-runs this module, so it would keep showing whichever route was
// cached. Force a real reload so the route above is re-evaluated against the current URL.
window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
        window.location.reload()
    }
})

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <Provider>
            {isAdminRoute ? (
                <Suspense fallback={null}>
                    <AdminApp />
                </Suspense>
            ) : (
                <App />
            )}
        </Provider>
    </React.StrictMode>
)
