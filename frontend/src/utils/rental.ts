const DAY_MS = 24 * 60 * 60 * 1000

const displayDateTimeFormatter = new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    hourCycle: 'h23',
})

const displayDateFormatter = new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
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

export const parseLocalDateTime = (
    date: string,
    time: string
): Date | null => {
    const dateParts = parseDateParts(date)
    const timeParts = parseTimeParts(time)

    if (!dateParts || !timeParts) return null

    const [year, month, day] = dateParts
    const [hours, minutes] = timeParts

    const value = new Date(year, month - 1, day, hours, minutes, 0, 0)
    if (Number.isNaN(value.getTime())) return null

    return value
}

export const localDateTimeToUtcIso = (
    date: string,
    time: string
): string | null => {
    const value = parseLocalDateTime(date, time)
    if (!value) return null
    return value.toISOString()
}

export const getRoundedRentalDaysFromDates = (
    start: Date,
    end: Date
): number | null => {
    const durationMs = end.getTime() - start.getTime()
    if (!Number.isFinite(durationMs) || durationMs <= 0) return null

    const wholeDays = Math.floor(durationMs / DAY_MS)
    const remainder = durationMs % DAY_MS
    const roundedDays = wholeDays + (remainder * 2 > DAY_MS ? 1 : 0)

    return Math.max(1, roundedDays)
}

export const getRoundedRentalDaysFromInputs = (
    startDate: string,
    startTime: string,
    endDate: string,
    endTime: string
): number | null => {
    const start = parseLocalDateTime(startDate, startTime)
    const end = parseLocalDateTime(endDate, endTime)

    if (!start || !end) return null
    return getRoundedRentalDaysFromDates(start, end)
}

export const getRoundedRentalDaysFromIso = (
    startIso?: string | null,
    endIso?: string | null
): number | null => {
    if (!startIso || !endIso) return null

    const start = new Date(startIso)
    const end = new Date(endIso)

    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null
    return getRoundedRentalDaysFromDates(start, end)
}

export const getRentalDaysUnitRu = (days: number): 'сутки' | 'суток' => {
    const normalizedDays = Math.abs(Math.trunc(days))

    return normalizedDays % 10 === 1 && normalizedDays % 100 !== 11
        ? 'сутки'
        : 'суток'
}

export const formatRentalDaysRu = (days?: number | null): string => {
    const safeDays = Math.max(0, Math.trunc(days ?? 0))
    return `${safeDays} ${getRentalDaysUnitRu(safeDays)}`
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
    const value = new Date(year, month - 1, day)
    if (Number.isNaN(value.getTime())) return date

    return displayDateFormatter.format(value)
}
