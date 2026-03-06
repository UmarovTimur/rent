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
import { useRef } from 'react'
// import Bonuses from './components/Bonuses.tsx'
import ProfileButton from './components/ProfileButton.tsx'
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
}

const DatePickerField = ({ value, onChange, min }: DatePickerFieldProps) => {
    const inputRef = useRef<HTMLInputElement | null>(null)

    const openPicker = () => {
        const input = inputRef.current
        if (!input) return

        if ('showPicker' in input && typeof input.showPicker === 'function') {
            input.showPicker()
            return
        }

        input.focus()
        input.click()
    }

    return (
        <Box
            position="relative"
            flex="1"
            role="button"
            tabIndex={0}
            onClick={openPicker}
            onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    openPicker()
                }
            }}
        >
            <Flex
                bg="back"
                rounded="full"
                h="40px"
                px="14px"
                alignItems="center"
            >
                <Text fontSize="sm">{formatInputDate(value)}</Text>
            </Flex>
            <Input
                ref={inputRef}
                type="date"
                lang="ru-RU"
                value={value}
                min={min}
                onChange={(e) => onChange(e.target.value)}
                position="absolute"
                inset="0"
                opacity={0}
                pointerEvents="none"
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
        validationError,
    } = useTripDates()

    return (
        <>
            <Box
                position="sticky"
                top="0"
                bg="back"
                p="gap"
                zIndex="3"
                w="100%"
            >
                <Box position="relative">
                    <Flex justify="space-between" alignItems="center">
                        {/* <Bonuses /> */}
                        <span></span>
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
                                    onChange={(value) => {
                                        setStartDate(value)
                                        if (endDate < value) setEndDate(value)
                                    }}
                                />
                                <Input
                                    type="time"
                                    lang="en-GB"
                                    inputMode="numeric"
                                    step={60}
                                    value={startTime}
                                    onChange={(e) => setStartTime(e.target.value)}
                                    bg="back"
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
                                    onChange={(value) => setEndDate(value < startDate ? startDate : value)}
                                />
                                <Input
                                    type="time"
                                    lang="en-GB"
                                    inputMode="numeric"
                                    step={60}
                                    value={endTime}
                                    min={startDate === endDate ? startTime : undefined}
                                    onChange={(e) => setEndTime(e.target.value)}
                                    bg="back"
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
