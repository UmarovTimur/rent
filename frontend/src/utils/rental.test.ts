/**
 * Mirror of backend/tests/test_rental_pricing.py — the owner's approved
 * reference table. Keep both suites in sync: drift on either side fails here.
 *
 * All rental times are Tashkent wall time (fixed UTC+5) regardless of the
 * device timezone, so cases are built as Tashkent-wall → UTC instants —
 * exactly how production data arrives. Results must be identical under any
 * TZ env (see CI which runs vitest under a non-Tashkent timezone).
 */
import { describe, expect, it } from 'vitest'
import {
    floorToStep,
    formatRentalDaysRu,
    getBilledHalfDaysFromDates,
    getBilledRentalDaysFromDates,
    getEveningGraceExplanationRu,
    getLineTotal,
    hasEveningPickupGrace,
    previewLineTotalWithAddons,
    tashkentDateTimeToUtcIso,
    utcIsoToTashkentParts,
} from './rental'

const TASHKENT_OFFSET_MS = 5 * 60 * 60 * 1000

// 2026-07-10 is a Friday (month is 0-based: 6 = July).
// Tashkent wall time → UTC instant (Tashkent is fixed UTC+5, no DST).
const d = (day: number, hh: number, mm = 0) =>
    new Date(Date.UTC(2026, 6, day, hh, mm) - TASHKENT_OFFSET_MS)
const FRI = 10
const SAT = 11
const SUN = 12
const MON = 13

describe('owner reference table (mirrors backend)', () => {
    const table: Array<[Date, Date, number, string]> = [
        [d(FRI, 19), d(SUN, 19), 3, 'Fri 19:00 → Sun 19:00 = 1.5 days'],
        [d(FRI, 19), d(SAT, 20), 2, 'Fri 19:00 → Sat 20:00 = 1 day (min)'],
        [d(SAT, 9), d(SUN, 10, 30), 2, 'Sat 09:00 → Sun 10:30 = 1 day'],
        [d(SAT, 9), d(SUN, 18), 3, 'Sat 09:00 → Sun 18:00 = 1.5 days'],
        // Owner's "week-long trip": Tue 09:00 start, 150h−2 = 148h → 6.5 days
        [d(MON, 18), d(20, 15), 13, 'Mon 18:00 → Mon+7 15:00 = 6.5 days'],
        // Literal Mon 18:00 → Sun 15:00: 126h−2 = 124h → 5.5 days
        [d(MON, 18), d(19, 15), 11, 'Mon 18:00 → Sun 15:00 = 5.5 days'],
    ]

    it.each(table)('%#: %s', (start, end, expectedHalfDays) => {
        expect(getBilledHalfDaysFromDates(start, end)).toBe(expectedHalfDays)
    })
})

describe('grace boundary', () => {
    it('pickup exactly 17:00 triggers grace', () => {
        expect(getBilledHalfDaysFromDates(d(SAT, 17), d(SUN, 17))).toBe(2)
        expect(getBilledHalfDaysFromDates(d(SAT, 17), d(SUN, 23, 59))).toBe(2)
    })

    it('pickup 16:59 does not', () => {
        expect(getBilledHalfDaysFromDates(d(SAT, 16, 59), d(SUN, 17))).toBe(2)
        expect(getBilledHalfDaysFromDates(d(SAT, 16, 59), d(SUN, 23, 59))).toBe(3)
    })

    it('hasEveningPickupGrace', () => {
        expect(hasEveningPickupGrace(d(FRI, 17))).toBe(true)
        expect(hasEveningPickupGrace(d(FRI, 16, 59))).toBe(false)
    })
})

describe('rounding boundary: 24h + 2h leniency', () => {
    it('exactly 26h = 1 day', () => {
        expect(getBilledHalfDaysFromDates(d(SAT, 9), d(SUN, 11))).toBe(2)
    })

    it('+1 minute = 1.5 days', () => {
        expect(getBilledHalfDaysFromDates(d(SAT, 9), d(SUN, 11, 1))).toBe(3)
    })
})

describe('degenerate windows → minimum', () => {
    it('return before billing start', () => {
        expect(getBilledHalfDaysFromDates(d(FRI, 19), d(FRI, 20))).toBe(2)
    })

    it('return equals billing start', () => {
        expect(getBilledHalfDaysFromDates(d(FRI, 19), d(SAT, 9))).toBe(2)
    })

    it('duration swallowed by leniency', () => {
        expect(getBilledHalfDaysFromDates(d(SAT, 9), d(SAT, 10, 30))).toBe(2)
    })
})

describe('getBilledRentalDaysFromDates', () => {
    it('returns fractional days', () => {
        expect(getBilledRentalDaysFromDates(d(FRI, 19), d(SUN, 19))).toBe(1.5)
        expect(getBilledRentalDaysFromDates(d(MON, 18), d(20, 15))).toBe(6.5)
    })

    it('null for empty/negative windows', () => {
        expect(getBilledRentalDaysFromDates(d(SAT, 9), d(SAT, 9))).toBeNull()
        expect(getBilledRentalDaysFromDates(d(SUN, 9), d(SAT, 9))).toBeNull()
    })
})

describe('money math (mirrors backend)', () => {
    it('line total for 1.5 days', () => {
        expect(getLineTotal(150_000, 1, 3)).toBe(225_000)
    })

    it('odd price floors the half sum', () => {
        expect(getLineTotal(333, 1, 3)).toBe(499)
    })

    it('floorToStep', () => {
        expect(floorToStep(22_551, 100)).toBe(22_500)
        expect(floorToStep(22_500, 100)).toBe(22_500)
        expect(floorToStep(99, 100)).toBe(0)
        expect(floorToStep(22_551, 1)).toBe(22_551)
    })
})

describe('previewLineTotalWithAddons (mirrors backend total)', () => {
    // 2 billed days (4 half-days), qty 1.
    const halfDays = 4
    it('product only', () => {
        expect(previewLineTotalWithAddons(140_000, 1, halfDays, [])).toBe(280_000)
    })

    it('per_day + flat add-ons', () => {
        // 140000×2 + Ночник 15000×2 (per_day) + Мангал 100000×1 (flat) = 410000
        expect(
            previewLineTotalWithAddons(140_000, 1, halfDays, [
                { price: 15_000, price_mode: 'per_day' },
                { price: 100_000, price_mode: 'flat' },
            ])
        ).toBe(410_000)
    })

    it('quantity scales product and add-ons', () => {
        // qty 2: 140000×2×2 + 15000×2×2 + 100000×2 = 820000
        expect(
            previewLineTotalWithAddons(140_000, 2, halfDays, [
                { price: 15_000, price_mode: 'per_day' },
                { price: 100_000, price_mode: 'flat' },
            ])
        ).toBe(820_000)
    })
})

describe('formatRentalDaysRu', () => {
    it('integers keep сутки/суток logic', () => {
        expect(formatRentalDaysRu(1)).toBe('1 сутки')
        expect(formatRentalDaysRu(5)).toBe('5 суток')
        expect(formatRentalDaysRu(21)).toBe('21 сутки')
        expect(formatRentalDaysRu(11)).toBe('11 суток')
    })

    it('fractions use comma + genitive plural', () => {
        expect(formatRentalDaysRu(1.5)).toBe('1,5 суток')
        expect(formatRentalDaysRu(6.5)).toBe('6,5 суток')
    })

    it('null/undefined → 0 суток', () => {
        expect(formatRentalDaysRu(null)).toBe('0 суток')
        expect(formatRentalDaysRu(undefined)).toBe('0 суток')
    })
})

describe('utcIsoToTashkentParts (round-trip with tashkentDateTimeToUtcIso)', () => {
    it('splits a UTC instant back into Tashkent date + time', () => {
        // 14:00 UTC = 19:00 Tashkent
        expect(utcIsoToTashkentParts('2026-07-10T14:00:00Z')).toEqual({
            date: '2026-07-10',
            time: '19:00',
        })
    })

    it('round-trips date/time → ISO → date/time', () => {
        for (const [date, time] of [
            ['2026-07-10', '19:00'],
            ['2026-12-31', '09:30'],
            ['2026-01-01', '00:15'],
        ] as const) {
            const iso = tashkentDateTimeToUtcIso(date, time)
            expect(utcIsoToTashkentParts(iso)).toEqual({ date, time })
        }
    })

    it('null/invalid → null', () => {
        expect(utcIsoToTashkentParts(null)).toBeNull()
        expect(utcIsoToTashkentParts(undefined)).toBeNull()
        expect(utcIsoToTashkentParts('not-a-date')).toBeNull()
    })
})

describe('getEveningGraceExplanationRu', () => {
    it('explains grace for evening pickup', () => {
        expect(getEveningGraceExplanationRu(d(FRI, 19))).toBe(
            'Выдача в пт вечером — этот день бесплатно, аренда считается с субботы с 09:00'
        )
    })

    it('null for daytime pickup', () => {
        expect(getEveningGraceExplanationRu(d(FRI, 12))).toBeNull()
    })
})
