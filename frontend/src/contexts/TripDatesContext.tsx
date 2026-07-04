import {
    createContext,
    useContext,
    useEffect,
    useMemo,
    useRef,
    useState,
} from 'react'
import {
    getBilledRentalDaysFromInputs,
    getEveningGraceExplanationRu,
    getTashkentNowWall,
    hasEveningPickupGrace,
    parseTashkentDateTime,
    tashkentDateTimeToUtcIso,
    utcIsoToTashkentParts,
} from '@/utils/rental'
import { BasketService } from '@/api/BasketService'

type TripDatesContextType = {
    startDate: string
    endDate: string
    startTime: string
    endTime: string
    setStartDate: (value: string) => void
    setEndDate: (value: string) => void
    setStartTime: (value: string) => void
    setEndTime: (value: string) => void
    startDateConfirmed: boolean
    endDateConfirmed: boolean
    startTimeConfirmed: boolean
    endTimeConfirmed: boolean
    datesConfirmed: boolean
    confirmStartDate: () => void
    confirmEndDate: () => void
    confirmStartTime: () => void
    confirmEndTime: () => void
    getTripDurationDays: () => number | null
    hasEveningGrace: boolean
    eveningGraceExplanation: string | null
    hasValidRange: boolean
    validationError: string | null
    rentalStartIso: string | null
    rentalEndIso: string | null
}

const TripDatesContext = createContext<TripDatesContextType | undefined>(undefined)

// Wall Dates carry Tashkent fields in UTC getters (see utils/rental.ts).
const wallToInputDate = (wall: Date) => {
    const yyyy = wall.getUTCFullYear()
    const mm = String(wall.getUTCMonth() + 1).padStart(2, '0')
    const dd = String(wall.getUTCDate()).padStart(2, '0')
    return `${yyyy}-${mm}-${dd}`
}

export const TripDatesProvider = ({
    userId,
    children,
}: {
    userId: number
    children: React.ReactNode
}) => {
    // Defaults are Tashkent's today/tomorrow, not the device's.
    const today = getTashkentNowWall()
    const tomorrow = new Date(today.getTime() + 24 * 60 * 60 * 1000)

    const [startDate, setStartDate] = useState<string>(wallToInputDate(today))
    const [endDate, setEndDate] = useState<string>(wallToInputDate(tomorrow))
    const [startTime, setStartTime] = useState<string>('12:00')
    const [endTime, setEndTime] = useState<string>('12:00')
    const [startDateConfirmed, setStartDateConfirmed] = useState(false)
    const [endDateConfirmed, setEndDateConfirmed] = useState(false)
    const [startTimeConfirmed, setStartTimeConfirmed] = useState(false)
    const [endTimeConfirmed, setEndTimeConfirmed] = useState(false)

    // Trip dates persist on the basket (server-side), independent of items.
    const [loaded, setLoaded] = useState(false)
    const userInteractedRef = useRef(false)
    const lastSavedKeyRef = useRef<string | null>(null)

    const markInteracted = () => {
        userInteractedRef.current = true
    }

    // Load persisted trip window once — unless the user already picked dates
    // while the request was in flight (then their choice wins).
    useEffect(() => {
        let cancelled = false

        BasketService.getBasket(userId)
            .then((basket) => {
                if (cancelled) return
                const start = utcIsoToTashkentParts(basket?.rental_start)
                const end = utcIsoToTashkentParts(basket?.rental_end)

                if (start && end && !userInteractedRef.current) {
                    setStartDate(start.date)
                    setStartTime(start.time)
                    setEndDate(end.date)
                    setEndTime(end.time)
                    setStartDateConfirmed(true)
                    setStartTimeConfirmed(true)
                    setEndDateConfirmed(true)
                    setEndTimeConfirmed(true)
                    lastSavedKeyRef.current = `${basket!.rental_start}|${basket!.rental_end}`
                }
            })
            .catch(() => {
                /* keep local defaults */
            })
            .finally(() => {
                if (!cancelled) setLoaded(true)
            })

        return () => {
            cancelled = true
        }
    }, [userId])

    const value = useMemo<TripDatesContextType>(() => {
        let validationError: string | null = null
        let hasValidRange = Boolean(startDate && endDate && startTime && endTime)

        const start = hasValidRange
            ? parseTashkentDateTime(startDate, startTime)
            : null
        const end = hasValidRange
            ? parseTashkentDateTime(endDate, endTime)
            : null

        if (hasValidRange && (!start || !end)) {
            hasValidRange = false
            validationError = 'Проверьте корректность даты и времени аренды'
        } else if (hasValidRange && start && end && end <= start) {
            hasValidRange = false
            // The first time a start-date change auto-bumps the end date to match it
            // (see Header.tsx), end === start is just a side effect, not a deliberate
            // conflict — don't nag the user about it until they've actually chosen an
            // end date themselves, at which point a real conflict is worth flagging.
            if (endDateConfirmed) {
                validationError = 'Время возврата должно быть позже времени получения'
            }
        }

        const rentalStartIso =
            hasValidRange && start
                ? tashkentDateTimeToUtcIso(startDate, startTime)
                : null
        const rentalEndIso =
            hasValidRange && end
                ? tashkentDateTimeToUtcIso(endDate, endTime)
                : null

        const getTripDurationDays = () =>
            hasValidRange
                ? getBilledRentalDaysFromInputs(
                    startDate,
                    startTime,
                    endDate,
                    endTime
                )
                : null

        const hasEveningGrace = Boolean(start && hasEveningPickupGrace(start))
        const eveningGraceExplanation = start
            ? getEveningGraceExplanationRu(start)
            : null

        return {
            startDate,
            endDate,
            startTime,
            endTime,
            setStartDate: (v: string) => {
                markInteracted()
                setStartDate(v)
            },
            setEndDate: (v: string) => {
                markInteracted()
                setEndDate(v)
            },
            setStartTime: (v: string) => {
                markInteracted()
                setStartTime(v)
            },
            setEndTime: (v: string) => {
                markInteracted()
                setEndTime(v)
            },
            startDateConfirmed,
            endDateConfirmed,
            startTimeConfirmed,
            endTimeConfirmed,
            datesConfirmed:
                startDateConfirmed &&
                endDateConfirmed &&
                startTimeConfirmed &&
                endTimeConfirmed,
            confirmStartDate: () => {
                markInteracted()
                setStartDateConfirmed(true)
            },
            confirmEndDate: () => {
                markInteracted()
                setEndDateConfirmed(true)
            },
            confirmStartTime: () => {
                markInteracted()
                setStartTimeConfirmed(true)
            },
            confirmEndTime: () => {
                markInteracted()
                setEndTimeConfirmed(true)
            },
            getTripDurationDays,
            hasEveningGrace,
            eveningGraceExplanation,
            hasValidRange,
            validationError,
            rentalStartIso,
            rentalEndIso,
        }
    }, [
        startDate,
        endDate,
        startTime,
        endTime,
        startDateConfirmed,
        endDateConfirmed,
        startTimeConfirmed,
        endTimeConfirmed,
    ])

    // Persist the trip window to the basket (debounced). Fires on any valid
    // range the user has actually touched — not only when all four fields are
    // "confirmed" — so picking dates while leaving the default times still
    // saves. Gated by `loaded` + `userInteracted` so we never overwrite the
    // server with the untouched local default before reading it.
    const { rentalStartIso, rentalEndIso } = value
    useEffect(() => {
        if (
            !loaded ||
            !userInteractedRef.current ||
            !rentalStartIso ||
            !rentalEndIso
        ) {
            return
        }

        const key = `${rentalStartIso}|${rentalEndIso}`
        if (key === lastSavedKeyRef.current) return

        const timeout = window.setTimeout(() => {
            lastSavedKeyRef.current = key
            BasketService.setBasketDates(
                userId,
                rentalStartIso,
                rentalEndIso
            ).catch(() => {
                // Allow a retry on the next change.
                lastSavedKeyRef.current = null
            })
        }, 600)

        return () => window.clearTimeout(timeout)
    }, [loaded, rentalStartIso, rentalEndIso, userId])

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
