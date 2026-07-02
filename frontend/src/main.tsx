import { Provider } from '@/components/ui/provider'
import React, { Suspense, lazy } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import '@fontsource-variable/montserrat/index.css'

// Admin calendar is lazy-loaded so its code (FullCalendar, etc.) stays out of the main client bundle.
const AdminApp = lazy(() => import('./AdminApp'))
const isAdminRoute = window.location.pathname.startsWith('/app/admin')

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
