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

type AccessState = 'checking' | 'granted' | 'unauthenticated' | 'error'

function AdminNavHeader({ onLogout }: { onLogout?: () => void }) {
    return (
        <Flex gap="2" p="3" borderBottomWidth="1px" mb="4" wrap="wrap" align="center">
            <Link href={ADMIN_URL}>
                <Button variant="outline" size="sm" rounded="full">
                    Админ
                </Button>
            </Link>
            <Button variant="solid" colorPalette="blue" size="sm" rounded="full" pointerEvents="none">
                Календарь
            </Button>
            <Link href="/app/">
                <Button variant="outline" size="sm" rounded="full">
                    Приложение
                </Button>
            </Link>
            {onLogout && (
                <Button variant="ghost" size="sm" rounded="full" ml="auto" onClick={onLogout}>
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
