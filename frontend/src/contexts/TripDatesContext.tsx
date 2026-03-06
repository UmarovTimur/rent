import { createContext, useContext, useMemo, useState } from 'react'
import {
    getRoundedRentalDaysFromInputs,
    localDateTimeToUtcIso,
    parseLocalDateTime,
} from '@/utils/rental'

type TripDatesContextType = {
    startDate: string
    endDate: string
    startTime: string
    endTime: string
    setStartDate: (value: string) => void
    setEndDate: (value: string) => void
    setStartTime: (value: string) => void
    setEndTime: (value: string) => void
    getTripDurationDays: () => number | null
    hasValidRange: boolean
    validationError: string | null
    rentalStartIso: string | null
    rentalEndIso: string | null
}

const TripDatesContext = createContext<TripDatesContextType | undefined>(undefined)

const toInputDate = (date: Date) => {
    const yyyy = date.getFullYear()
    const mm = String(date.getMonth() + 1).padStart(2, '0')
    const dd = String(date.getDate()).padStart(2, '0')
    return `${yyyy}-${mm}-${dd}`
}

export const TripDatesProvider = ({ children }: { children: React.ReactNode }) => {
    const today = new Date()
    const tomorrow = new Date()
    tomorrow.setDate(today.getDate() + 1)

    const [startDate, setStartDate] = useState<string>(toInputDate(today))
    const [endDate, setEndDate] = useState<string>(toInputDate(tomorrow))
    const [startTime, setStartTime] = useState<string>('12:00')
    const [endTime, setEndTime] = useState<string>('12:00')

    const value = useMemo<TripDatesContextType>(() => {
        let validationError: string | null = null
        let hasValidRange = Boolean(startDate && endDate && startTime && endTime)

        const start = hasValidRange
            ? parseLocalDateTime(startDate, startTime)
            : null
        const end = hasValidRange ? parseLocalDateTime(endDate, endTime) : null

        if (hasValidRange && (!start || !end)) {
            hasValidRange = false
            validationError = 'Проверьте корректность даты и времени аренды'
        } else if (hasValidRange && start && end && end <= start) {
            hasValidRange = false
            validationError = 'Время возврата должно быть позже времени получения'
        }

        const rentalStartIso =
            hasValidRange && start ? localDateTimeToUtcIso(startDate, startTime) : null
        const rentalEndIso =
            hasValidRange && end ? localDateTimeToUtcIso(endDate, endTime) : null

        const getTripDurationDays = () =>
            hasValidRange
                ? getRoundedRentalDaysFromInputs(
                    startDate,
                    startTime,
                    endDate,
                    endTime
                )
                : null

        return {
            startDate,
            endDate,
            startTime,
            endTime,
            setStartDate,
            setEndDate,
            setStartTime,
            setEndTime,
            getTripDurationDays,
            hasValidRange,
            validationError,
            rentalStartIso,
            rentalEndIso,
        }
    }, [startDate, endDate, startTime, endTime])

    return (
        <TripDatesContext.Provider value={value}>
            {children}
        </TripDatesContext.Provider>
    )
}

export const useTripDates = () => {
    const ctx = useContext(TripDatesContext)
    if (!ctx) throw new Error('useTripDates must be used within TripDatesProvider')
    return ctx
}
