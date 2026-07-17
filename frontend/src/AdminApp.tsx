import {
    Alert,
    Box,
    Button,
    Center,
    ChakraProvider,
    Flex,
    Heading,
    Input,
    Link,
    Spinner,
    Stack,
    Text,
} from '@chakra-ui/react'
import { FormEvent, useEffect, useState } from 'react'
import axios from 'axios'
import { system } from './theme.ts'
import { ADMIN_URL } from '@/config'
import { Toaster } from '@/components/ui/toaster'
import { AdminAuthService } from '@/api/AdminAuthService'
import AdminCalendar from '@/assets/admin/AdminCalendar'
import { useTelegramSafeArea } from '@/hooks/useTelegramSafeArea'

type AccessState = 'checking' | 'granted' | 'unauthenticated' | 'error'

function AdminNavHeader({ onLogout }: { onLogout?: () => void }) {
    // Sticky + padded past Telegram's safe-area insets so the native close/⋮
    // buttons (which float over the WebView) never sit on top of these links —
    // same treatment as the main app's Header.tsx. Buttons are a touch-friendly
    // "md" size on mobile (were cramped "sm" everywhere) and drop to "sm" once
    // there's room on wider screens.
    return (
        <Flex
            position="sticky"
            top="0"
            zIndex="3"
            bg="back"
            gap="2"
            px="3"
            pb="3"
            pt="calc(var(--tg-safe-area-inset-top, 0px) + var(--tg-content-safe-area-inset-top, 0px) + 12px)"
            borderBottomWidth="1px"
            wrap="wrap"
            align="center"
        >
            <Link href={ADMIN_URL}>
                <Button variant="outline" size={{ base: 'md', md: 'sm' }} rounded="full">
                    Админ
                </Button>
            </Link>
            <Button
                variant="solid"
                colorPalette="blue"
                size={{ base: 'md', md: 'sm' }}
                rounded="full"
                pointerEvents="none"
            >
                Календарь
            </Button>
            <Link href="/app/">
                <Button variant="outline" size={{ base: 'md', md: 'sm' }} rounded="full">
                    Приложение
                </Button>
            </Link>
            {onLogout && (
                <Button
                    variant="ghost"
                    size={{ base: 'md', md: 'sm' }}
                    rounded="full"
                    ml="auto"
                    onClick={onLogout}
                >
                    Выйти
                </Button>
            )}
        </Flex>
    )
}

function LoginForm({ onSuccess }: { onSuccess: () => void }) {
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const handleSubmit = async (event: FormEvent) => {
        event.preventDefault()
        setSubmitting(true)
        setError(null)
        try {
            await AdminAuthService.login(username, password)
            onSuccess()
        } catch (err) {
            if (axios.isAxiosError(err) && err.response?.status === 401) {
                setError('Неверный логин или пароль')
            } else {
                setError('Не удалось войти. Попробуйте позже.')
            }
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Center h="80vh" px="4">
            <Box as="form" onSubmit={handleSubmit} w="full" maxW="360px">
                <Heading size="lg" mb="6" textAlign="center">
                    Вход в админку
                </Heading>
                <Stack gap="3">
                    <Input
                        placeholder="Логин"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        autoComplete="username"
                        autoFocus
                    />
                    <Input
                        type="password"
                        placeholder="Пароль"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        autoComplete="current-password"
                    />
                    {error && (
                        <Text color="red.500" fontSize="sm">
                            {error}
                        </Text>
                    )}
                    <Button
                        type="submit"
                        colorPalette="blue"
                        loading={submitting}
                        disabled={!username || !password}
                    >
                        Войти
                    </Button>
                </Stack>
            </Box>
        </Center>
    )
}

export default function AdminApp() {
    const [access, setAccess] = useState<AccessState>('checking')

    useTelegramSafeArea()

    useEffect(() => {
        if (window.Telegram?.WebApp) {
            window.Telegram.WebApp.ready()
            window.Telegram.WebApp.expand?.()
        }
    }, [])

    const checkAccess = async () => {
        try {
            await AdminAuthService.me()
            setAccess('granted')
        } catch (error) {
            if (axios.isAxiosError(error) && error.response?.status === 401) {
                setAccess('unauthenticated')
            } else {
                console.error('Failed to check admin access:', error)
                setAccess('error')
            }
        }
    }

    useEffect(() => {
        checkAccess()
    }, [])

    const handleLogout = async () => {
        try {
            await AdminAuthService.logout()
        } catch (error) {
            console.error('Failed to log out:', error)
        }
        setAccess('unauthenticated')
    }

    return (
        <ChakraProvider value={system}>
            {access !== 'unauthenticated' && (
                <AdminNavHeader onLogout={access === 'granted' ? handleLogout : undefined} />
            )}

            {access === 'checking' && (
                <Center h="100vh">
                    <Spinner size="xl" />
                </Center>
            )}

            {access === 'unauthenticated' && <LoginForm onSuccess={() => setAccess('granted')} />}

            {access === 'error' && (
                <Center h="100vh" px="4">
                    <Alert.Root status="error">
                        <Alert.Indicator />
                        <Alert.Title>Не удалось загрузить данные. Попробуйте позже.</Alert.Title>
                    </Alert.Root>
                </Center>
            )}

            {access === 'granted' && (
                <Box maxW="1100px" mx="auto" p="4">
                    <AdminCalendar />
                </Box>
            )}

            <Toaster />
        </ChakraProvider>
    )
}
