import {
    Drawer,
    Heading,
    CloseButton,
    Icon,
    Flex,
    Textarea,
    Text,
    Input,
    Box,
    Mark,
} from '@chakra-ui/react'
import { motion } from 'framer-motion'
import { IoArrowBackOutline } from 'react-icons/io5'
import ConfirmOrderButton from './components/ConfirmOrderButton.tsx'
import CustomSelect from './components/CustomSelect.tsx'
import { IoWallet, IoCard } from 'react-icons/io5'
import { useOrder } from '@/contexts/OrderContext'
import { useTripDates } from '@/contexts/TripDatesContext.tsx'
import { formatInputDate, formatRentalDaysRu } from '@/utils/rental'

const MotionHeader = motion(Drawer.Header)
const MotionBody = motion(Drawer.Body)
const MotionFooter = motion(Drawer.Footer)

export const ConfirmOrderPage = {
    Header: ({ onBack }: { onBack: () => void }) => (
        <MotionHeader
            position="relative"
            py="24px"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
        >
            <CloseButton position="absolute" left="24px" top="20px" onClick={onBack}>
                <Icon as={IoArrowBackOutline} boxSize={6} />
            </CloseButton>
            <Heading size="2xl" fontWeight="800" textAlign="center" w="full">
                Оформление
            </Heading>
        </MotionHeader>
    ),

    Body: () => {
        const addressOptions = [
            { label: 'Самовывоз: ул Спитамена 4', value: 'ул. Спитамена 10' },
        ]
        const paymentOptions = [
            { label: 'Картой', value: 'card', icon: <IoCard /> },
            { label: 'Наличными', value: 'cash', icon: <IoWallet /> },
        ]



        const { startDate, getTripDurationDays, endDate, startTime, endTime } = useTripDates()
        const { formState, errors, updateField, updateSelectField } = useOrder()
        const formattedStartDate = formatInputDate(startDate)
        const formattedEndDate = formatInputDate(endDate)

        return (
            <MotionBody
                px="12px"
                py="0"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
            >
                <Flex direction="column" gap="12px" h="full">
                    <Box bg="back" rounded="28px" px="24px" py="14px">
                        <Text fontWeight="600">Период аренды</Text>
                        <Text opacity="0.7" fontSize="sm">
                            {formattedStartDate} {startTime} — {formattedEndDate} {endTime}
                        </Text>
                        <Mark fontWeight="bold" color="accent">
                            {formatRentalDaysRu(getTripDurationDays())}
                        </Mark>
                    </Box>

                    <CustomSelect
                        options={addressOptions}
                        placeholder="Где получить снаряжение?"
                        value={[formState.address]}
                        setValue={(val) => updateSelectField('address', val)}
                        isInvalid={!!errors.address}
                    />
                    <Input
                        bg="back"
                        borderColor={errors.firstName ? 'red.500' : 'back'}
                        outline="none"
                        h="48px"
                        minH="48px"
                        px="24px"
                        rounded="full"
                        size="md"
                        fontWeight="500"
                        placeholder="Имя"
                        value={formState.firstName}
                        onChange={(e) => updateField('firstName', e.target.value)}
                    />
                    <Input
                        bg="back"
                        borderColor={errors.phone ? 'red.500' : 'back'}
                        outline="none"
                        h="48px"
                        minH="48px"
                        rounded="full"
                        size="md"
                        fontWeight="500"
                        px="24px"
                        placeholder="+998 (99) 999-99-99"
                        value={formState.phone}
                        onChange={(e) => updateField('phone', e.target.value)}
                    />
                    <CustomSelect
                        options={paymentOptions}
                        placeholder="Способ оплаты"
                        value={[formState.paymentOption]}
                        setValue={(val) => updateSelectField('paymentOption', val)}
                        isInvalid={!!errors.paymentOption}
                    />

                    {/* {user && basket && user.coins > 0 && (
                        <Flex
                            bg="back"
                            h="48px"
                            minH="48px"
                            rounded="full"
                            px="24px"
                            justify="space-between"
                            alignItems="center"
                        >
                            <Text fontSize="14px" fontWeight="500">
                                {`Скидка ${((
                                    (user.coins * 100) /
                                    Math.max(basket.total_price, 1)
                                ).toFixed(0))}% за баллы`}
                            </Text>

                            <Switch.Root size="md" scale="1.5">
                                <Switch.HiddenInput />
                                <Switch.Control bg="card">
                                    <Switch.Thumb
                                        bg="back"
                                        boxShadow="none"
                                        _checked={{ bg: 'accent' }}
                                    >
                                        <Switch.ThumbIndicator fallback={<HiX color="text" />}>
                                            <HiCheck />
                                        </Switch.ThumbIndicator>
                                    </Switch.Thumb>
                                </Switch.Control>
                            </Switch.Root>
                        </Flex>
                    )} */}

                    <Textarea
                        bg="back"
                        borderWidth="0"
                        outline="none"
                        boxShadow="none"
                        flex="1"
                        rounded="28px"
                        size="md"
                        fontWeight="500"
                        px="24px"
                        py="12px"
                        minH="48px"
                        resize="none"
                        placeholder="Комментарий к заказу..."
                        value={formState.comment}
                        onChange={(e) => updateField('comment', e.target.value)}
                    />
                    <Text opacity="0.5" textAlign="center" fontSize="sm" color="text" mt="8px">В залог - Паспорт</Text>
                </Flex>
                <Text fontSize="sm" color="red.500" mt="8px">
                    {Object.values(errors)[0]}
                </Text>
            </MotionBody>
        )
    },

    Footer: () => (
        <MotionFooter
            p="12px"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
        >
            <ConfirmOrderButton />
        </MotionFooter>
    ),
}
