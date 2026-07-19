import { createContext, useCallback, useContext, useEffect, useMemo, useState, ReactNode } from 'react'
import { UserService } from '@/api/UserService'
import { Lang, normalizeLang, translations } from './translations'

type TranslateFn = (key: string, vars?: Record<string, string | number>) => string

type LanguageContextType = {
    lang: Lang
    setLang: (lang: Lang) => void
    t: TranslateFn
}

const translate = (lang: Lang): TranslateFn => (key, vars) => {
    const entry = translations[key]
    let text = entry ? entry[lang] ?? entry.ru : key
    if (vars) {
        for (const [k, v] of Object.entries(vars)) {
            text = text.replace(`{${k}}`, String(v))
        }
    }
    return text
}

const LanguageContext = createContext<LanguageContextType>({
    lang: 'ru',
    setLang: () => {},
    t: translate('ru'),
})

export const LanguageProvider = ({
    children,
    initialLang,
}: {
    children: ReactNode
    // Comes from user.language_code; the provider keeps it in sync when the user loads.
    initialLang?: string | null
}) => {
    const [lang, setLangState] = useState<Lang>(normalizeLang(initialLang))

    useEffect(() => {
        if (initialLang) setLangState(normalizeLang(initialLang))
    }, [initialLang])

    const setLang = useCallback((next: Lang) => {
        setLangState(next) // optimistic — the UI switches immediately
        void UserService.setLanguage(next).catch((err) => {
            console.error('Failed to persist language:', err)
        })
    }, [])

    // Memoize so `t` is stable per language — components/effects depending on it
    // don't churn on every render.
    const value = useMemo(() => ({ lang, setLang, t: translate(lang) }), [lang, setLang])

    return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export const useTranslation = () => useContext(LanguageContext)
