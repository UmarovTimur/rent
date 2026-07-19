import { Flex, Text } from '@chakra-ui/react'
import { useEffect, useState } from 'react'
import { TASHKENT_TIMEZONE } from '@/utils/rental'
import { useTranslation } from '@/i18n/LanguageContext'

const timeFormatter = new Intl.DateTimeFormat('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    hourCycle: 'h23',
    timeZone: TASHKENT_TIMEZONE,
})

export default function TashkentClock() {
    const [now, setNow] = useState(() => new Date())
    const { t } = useTranslation()

    useEffect(() => {
        // Re-render right after each minute boundary so the clock never lags.
        let timeout: number

        const scheduleTick = () => {
            const msToNextMinute = 60_000 - (Date.now() % 60_000)
            timeout = window.setTimeout(() => {
                setNow(new Date())
                scheduleTick()
            }, msToNextMinute + 50)
        }

        scheduleTick()
        return () => window.clearTimeout(timeout)
    }, [])

    return (
        <Flex
            h="hb"
            alignItems="center"
            gap="6px"
            title={t('clockTooltip')}
        >
            <Text fontSize="xs" opacity={0.7} color="text">
                {t('clockCity')}
            </Text>
            <Text fontSize="xs" fontWeight="700" color="text">
                {timeFormatter.format(now)}
            </Text>
        </Flex>
    )
}
