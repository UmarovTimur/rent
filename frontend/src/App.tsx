import { ChakraProvider, Alert, Spinner, Center, Box, Heading, Text, Button, Link } from '@chakra-ui/react'
import { useState, useEffect } from 'react'
import { system } from './theme.ts'
import Header from '@/assets/header/Header.tsx'
import MainList from '@/assets/mainList/MainList.tsx'
import { useCategories } from '@/hooks/useCategories'
import { useTelegramSafeArea } from '@/hooks/useTelegramSafeArea'
import BasketButton from '@/assets/basket/BasketButton.tsx'
import MotionDrawer from '@/assets/MotionDrawer.tsx'
import { BasketDrawerContent } from '@/assets/basket/BasketDrawer.tsx'
import OrderSuccessDialog from '@/assets/basket/OrderSuccessDialog.tsx'
import { BasketProvider } from '@/contexts/BasketContext.tsx'
import { OrderProvider } from '@/contexts/OrderContext'
import { Toaster } from '@/components/ui/toaster'
import { UserProvider } from '@/contexts/UserContext.tsx'
import { LanguageBridge } from '@/i18n/LanguageBridge.tsx'
import { TripDatesProvider } from '@/contexts/TripDatesContext.tsx'
// Phone-number web registration is temporarily disabled — re-enable by
// restoring the PhoneAuthScreen render in the `needAuth` branch below.
// import PhoneAuthScreen from '@/assets/auth/PhoneAuthScreen.tsx'
import { AuthService } from '@/api/AuthService'

const BOT_URL = 'https://t.me/camping_rent_uz_bot'

declare global {
    interface Window {
        Telegram: {
            WebApp: {
                initData: string
                initDataUnsafe: {
                    user: { id: number; first_name: string; username?: string }
                }
                ready: () => void
                close: () => void
                expand?: () => void
                disableVerticalSwipes?: () => void
                safeAreaInset?: { top: number; right: number; bottom: number; left: number }
                contentSafeAreaInset?: { top: number; right: number; bottom: number; left: number }
                onEvent?: (event: string, handler: () => void) => void
                offEvent?: (event: string, handler: () => void) => void
            }
        }
    }
}

export default function App() {
    const { categories, error } = useCategories()
    const [activeCategory, setActiveCategory] = useState('')
    const [searchQuery, setSearchQuery] = useState('')
    const [confirmActive, setConfirmActive] = useState<boolean>(false)
    const [userId, setUserId] = useState<number | null>(null)
    const [needAuth, setNeedAuth] = useState(false)

    useEffect(() => {
        if (categories.length > 0) setActiveCategory(categories[0].name)
    }, [categories])

    useEffect(() => {
        window.scrollTo(0, 0)
    }, [])

    useTelegramSafeArea()

    useEffect(() => {
        if (window.Telegram?.WebApp) {
            window.Telegram.WebApp.ready()
            // Take the full height and stop Telegram from closing/minimising the
            // Mini App on vertical swipes — otherwise pinching in the image zoom or
            // a slight downward drag while swiping the slider dismisses the app.
            window.Telegram.WebApp.expand?.()
            window.Telegram.WebApp.disableVerticalSwipes?.()
        }

        const telegramId = window?.Telegram?.WebApp?.initDataUnsafe?.user?.id
        if (telegramId) {
            setUserId(telegramId)
            return
        }

        const stored = AuthService.getStoredUserId()
        if (stored) {
            setUserId(stored)
            return
        }

        setNeedAuth(true)
    }, [])

    if (error) {
        return (
            <Alert.Root status="error">
                <Alert.Indicator />
                <Alert.Title>{error}</Alert.Title>
            </Alert.Root>
        )
    }

    if (needAuth) {
        // Web registration by phone number is disabled for now — the Mini App
        // is only available inside Telegram.
        return (
            <ChakraProvider value={system}>
                <Center h="100vh" p="24px" bg="back">
                    <Box
                        maxW="360px"
                        w="full"
                        bg="card"
                        borderWidth="1px"
                        borderColor="gray"
                        rounded="26px"
                        p="28px"
                        textAlign="center"
                    >
                        <Heading size="lg" color="text" mb="10px">
                            Доступно в Telegram
                        </Heading>
                        <Text color="text" opacity={0.7} fontSize="sm" mb="20px">
                            Приложение работает внутри Telegram. Откройте нашего
                            бота, чтобы оформить аренду.
                        </Text>
                        <Link href={BOT_URL} target="_blank" rel="noopener" w="full">
                            <Button bg="accent" color="text" rounded="full" h="48px" w="full" fontWeight="700">
                                Открыть в Telegram
                            </Button>
                        </Link>
                    </Box>
                </Center>
            </ChakraProvider>
        )
    }

    if (userId === null) {
        return (
            <Center h="100vh">
                <Spinner size="xl" />
            </Center>
        )
    }

    return (
        <UserProvider userId={userId}>
            <LanguageBridge>
            <OrderProvider userId={userId}>
                <TripDatesProvider userId={userId}>
                    <BasketProvider userId={userId}>
                        <ChakraProvider value={system}>
                            <Box maxW="1320px" mx="auto">
                                <Header
                                    categories={categories.map((c) => c.name)}
                                    activeCategory={activeCategory}
                                    setActiveCategory={setActiveCategory}
                                    searchQuery={searchQuery}
                                    setSearchQuery={setSearchQuery}
                                />

                                <MainList
                                    categories={categories.map((c) => c.name)}
                                    activeCategory={activeCategory}
                                    setActiveCategory={setActiveCategory}
                                    searchQuery={searchQuery}
                                />

                                <MotionDrawer
                                    trigger={
                                        <BasketButton
                                            openBasketPage={() =>
                                                setConfirmActive(false)
                                            }
                                        />
                                    }
                                >
                                    <BasketDrawerContent
                                        confirmActive={confirmActive}
                                        handleBack={() => setConfirmActive(false)}
                                        handleConfirm={() => setConfirmActive(true)}
                                    />
                                </MotionDrawer>
                            </Box>

                            <OrderSuccessDialog />
                            <Toaster />
                        </ChakraProvider>
                    </BasketProvider>
                </TripDatesProvider>
            </OrderProvider>
            </LanguageBridge>
        </UserProvider>
    )
}
