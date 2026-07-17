// Billing rules — MUST match backend/src/settings/billing.py (BillingSettings).
// The reference table is mirrored in rental.test.ts and
// backend/tests/test_rental_pricing.py; drift fails a test on the diverged side.
export const BILLING = {
    eveningPickupHour: 17, // pickup at/after this local hour → grace
    dayStartHour: 9, // billing starts here the next day after grace
    returnLeniencyMinutes: 120, // subtracted from duration before rounding
    roundingStepMinutes: 720, // 12h = 0.5-day step, rounded UP
    minHalfDays: 2, // minimum charge = 1 day
    totalFloorStep: 100, // floor final order/basket total to nearest 100 sum
} as const

const MINUTE_MS = 60 * 1000

// All rental times are Tashkent wall time (fixed UTC+5, no DST), regardless
// of the device timezone — mirrors BILLING_TIMEZONE=Asia/Tashkent on the backend.
export const TASHKENT_TIMEZONE = 'Asia/Tashkent'
const TASHKENT_UTC_OFFSET_MS = 5 * 60 * MINUTE_MS

// A "wall" Date carries Tashkent wall-clock fields in its UTC getters
// (getUTCHours() = Tashkent hour). Never render a wall Date via local getters.
const instantToTashkentWall = (instant: Date): Date =>
    new Date(instant.getTime() + TASHKENT_UTC_OFFSET_MS)

const tashkentWallToInstant = (wallMs: number): Date =>
    new Date(wallMs - TASHKENT_UTC_OFFSET_MS)

export const getTashkentNowWall = (): Date => instantToTashkentWall(new Date())

const displayDateTimeFormatter = new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    hourCycle: 'h23',
    timeZone: TASHKENT_TIMEZONE,
})

const displayDateFormatter = new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: 'UTC', // input is a date-only wall value built via Date.UTC
})

const parseDateParts = (date: string): [number, number, number] | null => {
    const [year, month, day] = date.split('-').map(Number)

    if (
        !Number.isInteger(year) ||
        !Number.isInteger(month) ||
        !Number.isInteger(day)
    ) {
        return null
    }

    return [year, month, day]
}

const parseTimeParts = (time: string): [number, number] | null => {
    const [hours, minutes] = time.split(':').map(Number)

    if (
        !Number.isInteger(hours) ||
        !Number.isInteger(minutes) ||
        hours < 0 ||
        hours > 23 ||
        minutes < 0 ||
        minutes > 59
    ) {
        return null
    }

    return [hours, minutes]
}

// Parse user-entered date/time as Tashkent wall time → real UTC instant.
export const parseTashkentDateTime = (
    date: string,
    time: string
): Date | null => {
    const dateParts = parseDateParts(date)
    const timeParts = parseTimeParts(time)

    if (!dateParts || !timeParts) return null

    const [year, month, day] = dateParts
    const [hours, minutes] = timeParts

    const wallMs = Date.UTC(year, month - 1, day, hours, minutes, 0, 0)
    if (Number.isNaN(wallMs)) return null

    return tashkentWallToInstant(wallMs)
}

export const tashkentDateTimeToUtcIso = (
    date: string,
    time: string
): string | null => {
    const value = parseTashkentDateTime(date, time)
    if (!value) return null
    return value.toISOString()
}

// Shift a "YYYY-MM-DD" input-date string by N calendar days (UTC-safe).
export const addDaysToInputDate = (date: string, days: number): string => {
    const parts = parseDateParts(date)
    if (!parts) return date
    const [year, month, day] = parts
    const shifted = new Date(Date.UTC(year, month - 1, day))
    shifted.setUTCDate(shifted.getUTCDate() + days)
    const yyyy = shifted.getUTCFullYear()
    const mm = String(shifted.getUTCMonth() + 1).padStart(2, '0')
    const dd = String(shifted.getUTCDate()).padStart(2, '0')
    return `${yyyy}-${mm}-${dd}`
}

// Inverse of parseTashkentDateTime: a UTC instant → Tashkent wall-clock
// date ("YYYY-MM-DD") + time ("HH:MM"), for restoring the trip-date inputs.
export const utcIsoToTashkentParts = (
    iso?: string | null
): { date: string; time: string } | null => {
    if (!iso) return null

    const instant = new Date(iso)
    if (Number.isNaN(instant.getTime())) return null

    const wall = instantToTashkentWall(instant)
    const yyyy = wall.getUTCFullYear()
    const mm = String(wall.getUTCMonth() + 1).padStart(2, '0')
    const dd = String(wall.getUTCDate()).padStart(2, '0')
    const hh = String(wall.getUTCHours()).padStart(2, '0')
    const min = String(wall.getUTCMinutes()).padStart(2, '0')

    return { date: `${yyyy}-${mm}-${dd}`, time: `${hh}:${min}` }
}

// `start` is a real instant; the grace rule is evaluated on its Tashkent hour.
export const hasEveningPickupGrace = (start: Date): boolean =>
    instantToTashkentWall(start).getUTCHours() >= BILLING.eveningPickupHour

// Mirror of backend get_billed_rental_half_days (rental_pricing.py):
// instants in, grace applied in Tashkent wall time.
export const getBilledHalfDaysFromDates = (start: Date, end: Date): number => {
    let billingStartMs = start.getTime()

    if (hasEveningPickupGrace(start)) {
        const wall = instantToTashkentWall(start)
        const nextDayWallMs = Date.UTC(
            wall.getUTCFullYear(),
            wall.getUTCMonth(),
            wall.getUTCDate() + 1,
            BILLING.dayStartHour,
            0,
            0,
            0
        )
        billingStartMs = tashkentWallToInstant(nextDayWallMs).getTime()
    }

    const billedMinutes =
        Math.floor((end.getTime() - billingStartMs) / MINUTE_MS) -
        BILLING.returnLeniencyMinutes

    if (billedMinutes <= 0) return BILLING.minHalfDays

    const halfDays = Math.ceil(billedMinutes / BILLING.roundingStepMinutes)
    return Math.max(BILLING.minHalfDays, halfDays)
}

export const getBilledRentalDaysFromDates = (
    start: Date,
    end: Date
): number | null => {
    if (
        Number.isNaN(start.getTime()) ||
        Number.isNaN(end.getTime()) ||
        end.getTime() <= start.getTime()
    ) {
        return null
    }
    return getBilledHalfDaysFromDates(start, end) / 2
}

export const getBilledRentalDaysFromInputs = (
    startDate: string,
    startTime: string,
    endDate: string,
    endTime: string
): number | null => {
    const start = parseTashkentDateTime(startDate, startTime)
    const end = parseTashkentDateTime(endDate, endTime)

    if (!start || !end) return null
    return getBilledRentalDaysFromDates(start, end)
}

export const getBilledRentalDaysFromIso = (
    startIso?: string | null,
    endIso?: string | null
): number | null => {
    if (!startIso || !endIso) return null

    const start = new Date(startIso)
    const end = new Date(endIso)

    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null
    return getBilledRentalDaysFromDates(start, end)
}

// Line total in sum for client-side previews (basket/order totals stay
// backend-authoritative): unit_price × qty × half_days / 2, floored.
export const getLineTotal = (
    unitPrice: number,
    quantity: number,
    halfDays: number
): number => Math.floor((unitPrice * quantity * halfDays) / 2)

export const floorToStep = (amount: number, step: number): number =>
    step <= 1 ? amount : Math.floor(amount / step) * step

// Mirror of backend rental_pricing.line_half_day_units: a line's contribution
// in half-day units, honouring price_mode ('per_day' × days, 'flat' once ×2).
export const lineHalfDayUnits = (
    unitPrice: number,
    quantity: number,
    halfDays: number,
    priceMode: 'per_day' | 'flat' = 'per_day'
): number =>
    priceMode === 'flat'
        ? unitPrice * quantity * 2
        : unitPrice * quantity * halfDays

// Combine a product line + its add-ons into one total the way the backend does:
// sum all half-day units, divide by 2 once, floor to 100 once.
export const previewLineTotalWithAddons = (
    unitPrice: number,
    quantity: number,
    halfDays: number,
    addons: { price: number; price_mode: 'per_day' | 'flat'; quantity: number }[]
): number => {
    let units = lineHalfDayUnits(unitPrice, quantity, halfDays, 'per_day')
    for (const a of addons) {
        // Each add-on is billed by its own quantity, independent of the parent.
        units += lineHalfDayUnits(a.price, a.quantity, halfDays, a.price_mode)
    }
    return floorToStep(Math.floor(units / 2), BILLING.totalFloorStep)
}

// Genitive weekday names for «считаем с …» (index = Date.getDay()).
const WEEKDAY_GENITIVE_RU = [
    'воскресенья',
    'понедельника',
    'вторника',
    'среды',
    'четверга',
    'пятницы',
    'субботы',
] as const

const WEEKDAY_SHORT_RU = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб'] as const

export const getEveningGraceExplanationRu = (start: Date): string | null => {
    if (Number.isNaN(start.getTime()) || !hasEveningPickupGrace(start)) {
        return null
    }

    const wall = instantToTashkentWall(start)
    const nextDayWall = new Date(
        Date.UTC(wall.getUTCFullYear(), wall.getUTCMonth(), wall.getUTCDate() + 1)
    )

    return (
        `Выдача в ${WEEKDAY_SHORT_RU[wall.getUTCDay()]} вечером — этот день бесплатно, ` +
        `аренда считается с ${WEEKDAY_GENITIVE_RU[nextDayWall.getUTCDay()]} с 09:00`
    )
}

export const getRentalDaysUnitRu = (days: number): 'сутки' | 'суток' => {
    // Fractional numerals always take the genitive plural: «1,5 суток».
    if (!Number.isInteger(days)) return 'суток'

    const normalizedDays = Math.abs(days)
    return normalizedDays % 10 === 1 && normalizedDays % 100 !== 11
        ? 'сутки'
        : 'суток'
}

export const formatRentalDaysRu = (days?: number | null): string => {
    const safeDays = Math.max(0, days ?? 0)
    const formatted = Number.isInteger(safeDays)
        ? String(safeDays)
        : safeDays.toLocaleString('ru-RU') // «1,5» — comma decimal separator
    return `${formatted} ${getRentalDaysUnitRu(safeDays)}`
}

export const formatRentalDateTimeRange = (
    startIso?: string | null,
    endIso?: string | null
): string => {
    if (!startIso || !endIso) return 'Период не указан'

    const start = new Date(startIso)
    const end = new Date(endIso)
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        return 'Период не указан'
    }

    return `${displayDateTimeFormatter.format(start)} - ${displayDateTimeFormatter.format(end)}`
}

export const formatInputDate = (date: string): string => {
    const parts = parseDateParts(date)
    if (!parts) return date

    const [year, month, day] = parts
    // Date-only wall value; the formatter reads it back with timeZone: 'UTC',
    // so the calendar date never shifts with the device timezone.
    const value = new Date(Date.UTC(year, month - 1, day))
    if (Number.isNaN(value.getTime())) return date

    return displayDateFormatter.format(value)
}
