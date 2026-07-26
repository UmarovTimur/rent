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
    Switch,
} from '@chakra-ui/react'
import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { IoArrowBackOutline } from 'react-icons/io5'
import { HiCheck, HiX } from 'react-icons/hi'
import ConfirmOrderButton from './components/ConfirmOrderButton.tsx'
import CustomSelect from './components/CustomSelect.tsx'
import { IoWallet, IoCard } from 'react-icons/io5'
import { useOrder } from '@/contexts/OrderContext'
import { useUserContext } from '@/contexts/UserContext'
import { useBasketContext } from '@/contexts/BasketContext'
import { useTripDates } from '@/contexts/TripDatesContext.tsx'
import { formatInputDate, formatRentalDaysRu } from '@/utils/rental'
import { formatPriceK } from '@/utils/price'
import { useTranslation } from '@/i18n/LanguageContext'
import { PICKUP_ADDRESS } from '@/config'

const MotionHeader = motion(Drawer.Header)
const MotionBody = motion(Drawer.Body)
const MotionFooter = motion(Drawer.Footer)

export const ConfirmOrderPage = {
    Header: ({ onBack }: { onBack: () => void }) => {
        const { t } = useTranslation()
        return (
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
                    {t('checkoutTitle')}
                </Heading>
            </MotionHeader>
        )
    },

    Body: () => {
        const { t } = useTranslation()
        const paymentOptions = [
            { label: t('payCard'), value: 'card', icon: <IoCard /> },
            { label: t('payCash'), value: 'cash', icon: <IoWallet /> },
        ]

        const { startDate, getTripDurationDays, endDate, startTime, endTime } = useTripDates()
        const { formState, errors, updateField, updateSelectField, setUseCoins } = useOrder()
        const { user } = useUserContext()
        const { basket } = useBasketContext()
        const formattedStartDate = formatInputDate(startDate)
        const formattedEndDate = formatInputDate(endDate)
        const availableCoins = Math.min(user?.coins || 0, basket?.total_price || 0)

        // Only one pickup location exists — there's nothing to choose, so it's
        // set once here rather than shown as a selectable field.
        useEffect(() => {
            if (!formState.address) {
                updateSelectField('address', PICKUP_ADDRESS)
            }
            // eslint-disable-next-line react-hooks/exhaustive-deps
        }, [])

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
                        <Text fontWeight="600">{t('rentalPeriod')}</Text>
                        <Text opacity="0.7" fontSize="sm">
                            {formattedStartDate} {startTime} — {formattedEndDate} {endTime}
                        </Text>
                        <Mark fontWeight="bold" color="accent">
                            {formatRentalDaysRu(getTripDurationDays())}
                        </Mark>
                        <Text opacity="0.7" fontSize="sm" mt="4px">
                            {t('pickupAddressLabel')}: {PICKUP_ADDRESS}
                        </Text>
                    </Box>

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
                        placeholder={t('namePlaceholder')}
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
                        placeholder={t('paymentPlaceholder')}
                        value={[formState.paymentOption]}
                        setValue={(val) => updateSelectField('paymentOption', val)}
                        isInvalid={!!errors.paymentOption}
                    />

                    {availableCoins > 0 && (
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
                                {t('useCoinsLabel', { amount: formatPriceK(availableCoins) })}
                            </Text>

                            <Switch.Root
                                size="md"
                                scale="1.5"
                                checked={formState.useCoins}
                                onCheckedChange={(e) => setUseCoins(e.checked)}
                            >
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
                    )}

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
                        placeholder={t('commentPlaceholder')}
                        value={formState.comment}
                        onChange={(e) => updateField('comment', e.target.value)}
                    />
                    <Text opacity="0.5" textAlign="center" fontSize="sm" color="text" mt="8px">{t('depositPassport')}</Text>
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
