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
    // True once the user has actually changed any date/time field. Consumers use
    // this to avoid persisting the untouched local default over the server.
    tripDatesTouched: boolean
    // Earliest allowed rental start — "now" in Tashkent. `minStartTime` is only set
    // when the start date is today (so earlier times are allowed on future dates).
    minStartDate: string
    minStartTime: string | undefined
}

const TripDatesContext = createContext<TripDatesContextType | undefined>(undefined)

// Wall Dates carry Tashkent fields in UTC getters (see utils/rental.ts).
const wallToInputDate = (wall: Date) => {
    const yyyy = wall.getUTCFullYear()
    const mm = String(wall.getUTCMonth() + 1).padStart(2, '0')
    const dd = String(wall.getUTCDate()).padStart(2, '0')
    return `${yyyy}-${mm}-${dd}`
}

const wallToInputTime = (wall: Date) => {
    const hh = String(wall.getUTCHours()).padStart(2, '0')
    const mm = String(wall.getUTCMinutes()).padStart(2, '0')
    return `${hh}:${mm}`
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
    // Default start time is "now" (not noon) so the untouched default is never in
    // the past; end keeps a simple noon default the next day.
    const [startTime, setStartTime] = useState<string>(wallToInputTime(today))
    const [endTime, setEndTime] = useState<string>('12:00')
    const [startDateConfirmed, setStartDateConfirmed] = useState(false)
    const [endDateConfirmed, setEndDateConfirmed] = useState(false)
    const [startTimeConfirmed, setStartTimeConfirmed] = useState(false)
    const [endTimeConfirmed, setEndTimeConfirmed] = useState(false)

    // Trip dates persist on the basket (server-side), independent of items.
    const [touched, setTouched] = useState(false)
    const userInteractedRef = useRef(false)

    const markInteracted = () => {
        userInteractedRef.current = true
        setTouched(true)
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
                }
            })
            .catch(() => {
                /* keep local defaults */
            })

        return () => {
            cancelled = true
        }
    }, [userId])

    const value = useMemo<TripDatesContextType>(() => {
        let validationError: string | null = null
        let hasValidRange = Boolean(startDate && endDate && startTime && endTime)

        // "Now" in Tashkent, truncated to the minute — the earliest allowed start.
        const nowWall = getTashkentNowWall()
        nowWall.setUTCMinutes(nowWall.getUTCMinutes(), 0, 0)
        const minStartDate = wallToInputDate(nowWall)
        const minStartTime = startDate === minStartDate ? wallToInputTime(nowWall) : undefined

        const start = hasValidRange
            ? parseTashkentDateTime(startDate, startTime)
            : null
        const end = hasValidRange
            ? parseTashkentDateTime(endDate, endTime)
            : null

        if (hasValidRange && (!start || !end)) {
            hasValidRange = false
            validationError = 'Проверьте корректность даты и времени аренды'
        } else if (hasValidRange && start && start.getTime() < nowWall.getTime()) {
            hasValidRange = false
            // Don't nag about the untouched "now" default drifting into the past while
            // the user is idle — only once they've actually engaged with the start.
            if (startDateConfirmed || startTimeConfirmed) {
                validationError = 'Начало аренды не может быть в прошлом'
            }
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
            tripDatesTouched: touched,
            minStartDate,
            minStartTime,
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
        touched,
    ])

    // Server persistence + item migration on a date change is owned by
    // BasketContext, which calls the atomic set-dates-and-migrate endpoint.

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
