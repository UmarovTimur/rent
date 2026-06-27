import { useState, useEffect } from 'react'

export function useIsDesktop(breakpoint = 768) {
    const [isDesktop, setIsDesktop] = useState(() => window.innerWidth >= breakpoint)
    useEffect(() => {
        const handler = () => setIsDesktop(window.innerWidth >= breakpoint)
        window.addEventListener('resize', handler)
        return () => window.removeEventListener('resize', handler)
    }, [breakpoint])
    return isDesktop
}
