import {
    Flex,
    Heading,
    Box,
    Center,
    Text,
    Button,
    Link,
    Input,
    Alert,
} from '@chakra-ui/react'
// import Bonuses from './components/Bonuses.tsx'
import ProfileButton from './components/ProfileButton.tsx'
import TashkentClock from './components/TashkentClock.tsx'
import PromoGroup from './components/promoList/PromoGroup.tsx'
import CategoriesGroup from './components/categoriesNavigation/CategoriesGroup.tsx'
import MotionDrawer from '@/assets/MotionDrawer.tsx'
import ProfilePage from '@/assets/profile/ProfilePage.tsx'
import { useUserContext } from '@/contexts/UserContext'
import { useTripDates } from '@/contexts/TripDatesContext'
import { ADMIN_URL } from '@/config'
import { formatInputDate } from '@/utils/rental'

type HeaderProps = {
    categories: string[]
    activeCategory: string
    setActiveCategory: (category: string) => void
    searchQuery: string
    setSearchQuery: (value: string) => void
}

type DatePickerFieldProps = {
    value: string
    onChange: (value: string) => void
    min?: string
    confirmed: boolean
}

const DatePickerField = ({ value, onChange, min, confirmed }: DatePickerFieldProps) => {
    // The date <input> sits transparently on top and is tapped directly (like the
    // time input) — iOS only opens the native date picker on a real tap on the
    // input, not on a programmatic open of a pointer-events:none element.
    const openPicker = (e: React.MouseEvent<HTMLInputElement>) => {
        const input = e.currentTarget
        try {
            if (typeof input.showPicker === 'function') {
                input.showPicker()
            }
        } catch {
            // showPicker may be blocked (older browsers) — the native tap on the
            // input already opens the picker on mobile, so this is best-effort.
        }
    }

    return (
        <Box position="relative" flex="1">
            <Flex
                bg={confirmed ? 'green.500/10' : 'red.500/10'}
                borderWidth="1.5px"
                borderColor={confirmed ? 'green.500/60' : 'red.500/50'}
                transition="background 0.2s, border-color 0.2s"
                rounded="full"
                h="40px"
                px="14px"
                alignItems="center"
            >
                <Text fontSize="sm">{formatInputDate(value)}</Text>
            </Flex>
            <Input
                type="date"
                lang="ru-RU"
                aria-label="Дата поездки"
                value={value}
                min={min}
                onChange={(e) => onChange(e.target.value)}
                onClick={openPicker}
                position="absolute"
                inset="0"
                opacity="0"
                cursor="pointer"
            />
        </Box>
    )
}

export default function Header({
    categories,
    activeCategory,
    setActiveCategory,
    searchQuery,
    setSearchQuery,
}: HeaderProps) {
    const { user } = useUserContext()
    const {
        startDate,
        endDate,
        startTime,
        endTime,
        setStartDate,
        setEndDate,
        setStartTime,
        setEndTime,
        startDateConfirmed,
        endDateConfirmed,
        startTimeConfirmed,
        endTimeConfirmed,
        confirmStartDate,
        confirmEndDate,
        confirmStartTime,
        confirmEndTime,
        validationError,
    } = useTripDates()

    return (
        <>
            <Box
                position="sticky"
                top="0"
                bg="back"
                px="gap"
                pb="gap"
                // In Telegram fullscreen mode the native close/⋮ buttons float over
                // the webview, so lift the header content below them. Both insets
                // resolve to ~0 in normal mode (and on older clients via fallback).
                pt="calc(var(--tg-safe-area-inset-top, 0px) + var(--tg-content-safe-area-inset-top, 0px) + 16px)"
                zIndex="3"
                w="100%"
            >
                <Box position="relative">
                    <Flex justify="space-between" alignItems="center">
                        {/* <Bonuses /> */}
                        <TashkentClock />
                        <MotionDrawer trigger={<ProfileButton />}>
                            <ProfilePage />
                        </MotionDrawer>
                    </Flex>

                    <Center
                        h="hb"
                        w="full"
                        position="absolute"
                        top="0"
                        pointerEvents="none"
                    >
                        <Heading color="text" fontWeight="800" size="2xl">
                            Меню
                        </Heading>
                    </Center>

                    {user && user.is_admin && (
                        <Link
                            href={ADMIN_URL}
                            pos="absolute"
                            top="0"
                            right="40px"
                        >
                            <Button bg="gray" rounded="full" h="hb" px="16px">
                                <Text
                                    color="text"
                                    fontWeight="600"
                                    fontSize="xs"
                                >
                                    Админ
                                </Text>
                            </Button>
                        </Link>
                    )}
                </Box>
            </Box>

            <PromoGroup />

            <Box p="gap" pb="gap">
                <Flex direction="column" gap="10px">
                    <Box
                        bg="card"
                        borderWidth="1px"
                        borderColor="gray"
                        rounded="24px"
                        p="14px"
                    >
                        <Heading textAlign="center" size="md" mb="10px" color="text">
                            Даты поездки
                        </Heading>

                        <Flex gap="10px" direction="column">
                            <Flex gap="10px" direction={{ base: 'row' }}>
                                <DatePickerField
                                    value={startDate}
                                    confirmed={startDateConfirmed}
                                    onChange={(value) => {
                                        setStartDate(value)
                                        confirmStartDate()
                                        if (endDate < value) setEndDate(value)
                                    }}
                                />
                                <Input
                                    type="time"
                                    lang="en-GB"
                                    inputMode="numeric"
                                    step={60}
                                    value={startTime}
                                    onChange={(e) => {
                                        setStartTime(e.target.value)
                                        confirmStartTime()
                                    }}
                                    bg={startTimeConfirmed ? 'green.500/10' : 'red.500/10'}
                                    borderWidth="1.5px"
                                    borderColor={startTimeConfirmed ? 'green.500/60' : 'red.500/50'}
                                    transition="background 0.2s, border-color 0.2s"
                                    rounded="full"
                                    w={{ base: '140px' }}
                                    css={{
                                        '&::-webkit-datetime-edit-ampm-field': {
                                            display: 'none',
                                        },
                                    }}
                                />
                            </Flex>
                            <Flex gap="10px" direction={{ base: 'row' }} >
                                <DatePickerField
                                    value={endDate}
                                    min={startDate}
                                    confirmed={endDateConfirmed}
                                    onChange={(value) => {
                                        setEndDate(value < startDate ? startDate : value)
                                        confirmEndDate()
                                    }}
                                />
                                <Input
                                    type="time"
                                    lang="en-GB"
                                    inputMode="numeric"
                                    step={60}
                                    value={endTime}
                                    min={startDate === endDate ? startTime : undefined}
                                    onChange={(e) => {
                                        setEndTime(e.target.value)
                                        confirmEndTime()
                                    }}
                                    bg={endTimeConfirmed ? 'green.500/10' : 'red.500/10'}
                                    borderWidth="1.5px"
                                    borderColor={endTimeConfirmed ? 'green.500/60' : 'red.500/50'}
                                    transition="background 0.2s, border-color 0.2s"
                                    rounded="full"
                                    w={{ base: '140px' }}
                                    css={{
                                        '&::-webkit-datetime-edit-ampm-field': {
                                            display: 'none',
                                        },
                                    }}
                                />
                            </Flex>
                        </Flex>

                        <Text textAlign="center" mt="8px" fontSize="xs" opacity="0.7">
                            Показываем доступные товары, <br /> на выбранные даты аренды.
                        </Text>

                        {validationError && (
                            <Alert.Root status="error" mt="10px" rounded="16px">
                                <Alert.Indicator />
                                <Alert.Title fontSize="sm">
                                    {validationError}
                                </Alert.Title>
                            </Alert.Root>
                        )}
                    </Box>
                    <Input
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Поиск по названию и описанию..."
                        bg="card"
                        borderWidth="1px"
                        borderColor="gray"
                        rounded="full"
                        h="44px"
                        px="16px"
                    />

                </Flex>
            </Box >

            <Box display="none" position="sticky" top="64px" zIndex="2">
                <CategoriesGroup
                    categories={categories}
                    activeCategory={activeCategory}
                    setActiveCategory={setActiveCategory}
                />
            </Box>
        </>
    )
}
