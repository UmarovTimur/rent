import { useEffect } from 'react'

// Telegram exposes the notch/overlay-button insets via JS; mirror them into CSS
// variables (--tg-safe-area-inset-* / --tg-content-safe-area-inset-*) so any
// layout can pad content out from under Telegram's buttons that sit on top of it.
// Shared by App.tsx and AdminApp.tsx — both render inside the same Telegram WebView.
export function useTelegramSafeArea() {
    useEffect(() => {
        const wa = window.Telegram?.WebApp
        if (!wa) return

        const root = document.documentElement
        const apply = () => {
            const set = (name: string, v?: number) =>
                root.style.setProperty(name, `${Math.max(0, v ?? 0)}px`)
            set('--tg-safe-area-inset-top', wa.safeAreaInset?.top)
            set('--tg-safe-area-inset-bottom', wa.safeAreaInset?.bottom)
            set('--tg-content-safe-area-inset-top', wa.contentSafeAreaInset?.top)
            set('--tg-content-safe-area-inset-bottom', wa.contentSafeAreaInset?.bottom)
        }
        apply()
        wa.onEvent?.('safeAreaChanged', apply)
        wa.onEvent?.('contentSafeAreaChanged', apply)
        wa.onEvent?.('viewportChanged', apply)
        return () => {
            wa.offEvent?.('safeAreaChanged', apply)
            wa.offEvent?.('contentSafeAreaChanged', apply)
            wa.offEvent?.('viewportChanged', apply)
        }
    }, [])
}
