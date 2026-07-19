import { ReactNode } from 'react'
import { useUserContext } from '@/contexts/UserContext'
import { LanguageProvider } from './LanguageContext'

// Seeds the language from the loaded user (user.language_code) — must render
// inside UserProvider. Keeps the app UI language in sync with the same
// preference the bot uses.
export const LanguageBridge = ({ children }: { children: ReactNode }) => {
    const { user } = useUserContext()
    return <LanguageProvider initialLang={user?.language_code}>{children}</LanguageProvider>
}
