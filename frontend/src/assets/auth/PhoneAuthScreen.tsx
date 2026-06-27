import { useState, useRef } from 'react'
import {
    Box,
    Button,
    Center,
    Flex,
    Heading,
    Input,
    Text,
    Spinner,
    Icon,
    Image,
} from '@chakra-ui/react'
import { RiSmartphoneLine, RiTelegramLine, RiArrowLeftLine, RiHome4Line } from 'react-icons/ri'
import { AuthService } from '@/api/AuthService'

type Step = 'main' | 'phone_input' | 'login_confirm' | 'register'

interface Props {
    onAuth: (userId: number) => void
}

function formatPhone(raw: string): string {
    const digits = raw.replace(/\D/g, '')
    if (!digits) return ''
    let result = '+'
    if (digits[0] === '7' || digits[0] === '8') {
        result += '7'
        if (digits.length > 1) result += ' (' + digits.slice(1, 4)
        if (digits.length > 4) result += ') ' + digits.slice(4, 7)
        if (digits.length > 7) result += '-' + digits.slice(7, 9)
        if (digits.length > 9) result += '-' + digits.slice(9, 11)
    } else {
        result += digits.slice(0, 15)
    }
    return result
}

export default function PhoneAuthScreen({ onAuth }: Props) {
    const [step, setStep] = useState<Step>('main')
    const [phone, setPhone] = useState('')
    const [phoneRaw, setPhoneRaw] = useState('')
    const [foundName, setFoundName] = useState('')
    const [firstName, setFirstName] = useState('')
    const [lastName, setLastName] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const phoneInputRef = useRef<HTMLInputElement>(null)

    const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const raw = e.target.value.replace(/\D/g, '')
        setPhoneRaw(raw)
        setPhone(formatPhone(e.target.value))
        setError(null)
    }

    const normalizedPhone = (): string => {
        const digits = phoneRaw.replace(/^8/, '7')
        return '+' + digits
    }

    const handlePhoneSubmit = async () => {
        if (phoneRaw.replace(/\D/g, '').length < 10) {
            setError('Введите корректный номер телефона')
            return
        }
        setLoading(true)
        setError(null)
        try {
            const result = await AuthService.checkPhone(normalizedPhone())
            if (result.exists) {
                setFoundName(result.first_name || '')
                setStep('login_confirm')
            } else {
                setStep('register')
            }
        } catch {
            setError('Ошибка соединения. Попробуйте ещё раз.')
        } finally {
            setLoading(false)
        }
    }

    const handleLogin = async () => {
        setLoading(true)
        setError(null)
        try {
            const { access_token, user_id } = await AuthService.loginByPhone(normalizedPhone())
            AuthService.saveSession(access_token, user_id)
            onAuth(user_id)
        } catch {
            setError('Не удалось войти. Попробуйте ещё раз.')
        } finally {
            setLoading(false)
        }
    }

    const handleRegister = async () => {
        if (!firstName.trim()) {
            setError('Введите ваше имя')
            return
        }
        setLoading(true)
        setError(null)
        try {
            const { access_token, user_id } = await AuthService.registerByPhone(
                normalizedPhone(),
                firstName.trim(),
                lastName.trim() || undefined,
            )
            AuthService.saveSession(access_token, user_id)
            onAuth(user_id)
        } catch (e: unknown) {
            const status = (e as { response?: { status?: number } })?.response?.status
            if (status === 409) {
                setError('Этот номер уже зарегистрирован. Попробуйте войти.')
            } else {
                setError('Ошибка регистрации. Попробуйте ещё раз.')
            }
        } finally {
            setLoading(false)
        }
    }

    const goBack = () => {
        setError(null)
        if (step === 'login_confirm' || step === 'register') setStep('phone_input')
        else setStep('main')
    }

    return (
        <Center minH="100vh" bg="back" px="24px">
            <Flex direction="column" gap="0" w="100%" maxW="360px">
                {/* Back to landing */}
                <Button
                    variant="ghost"
                    w="fit-content"
                    p="0"
                    mb="16px"
                    color="text/50"
                    gap="6px"
                    onClick={() => { window.location.href = '/' }}
                >
                    <Icon as={RiHome4Line} boxSize="18px" />
                    <Text fontSize="sm">На главную</Text>
                </Button>

                {/* Logo block */}
                <Flex direction="column" align="center" mb="40px" gap="16px">
                    <Image
                        src="/images/logo.svg"
                        alt="ShawaBear"
                        w="200px"
                        filter="brightness(0) invert(1)"
                    />
                    <Text color="text/50" fontSize="sm" textAlign="center">
                        Войдите, чтобы продолжить
                    </Text>
                </Flex>

                {/* MAIN step */}
                {step === 'main' && (
                    <Flex direction="column" gap="12px">
                        {/* Telegram button */}
                        <Button
                            size="lg"
                            borderRadius="18px"
                            bg="gray"
                            color="text"
                            fontWeight="700"
                            h="56px"
                            gap="10px"
                            opacity="0.5"
                            cursor="not-allowed"
                            _hover={{}}
                        >
                            <Icon as={RiTelegramLine} boxSize="22px" color="#2AABEE" />
                            Войти через Telegram
                        </Button>
                        <Text fontSize="xs" color="text/40" textAlign="center" mt="-4px" mb="4px">
                            Доступно только внутри Telegram Mini App
                        </Text>

                        {/* Divider */}
                        <Flex align="center" gap="12px" my="4px">
                            <Box flex="1" h="1px" bg="gray" />
                            <Text fontSize="sm" color="text/40" fontWeight="600">или</Text>
                            <Box flex="1" h="1px" bg="gray" />
                        </Flex>

                        {/* Phone button */}
                        <Button
                            size="lg"
                            borderRadius="18px"
                            bg="accent"
                            color="token-black"
                            fontWeight="700"
                            h="56px"
                            gap="10px"
                            onClick={() => setStep('phone_input')}
                        >
                            <Icon as={RiSmartphoneLine} boxSize="22px" />
                            Войти по номеру телефона
                        </Button>
                    </Flex>
                )}

                {/* PHONE INPUT step */}
                {step === 'phone_input' && (
                    <Flex direction="column" gap="16px">
                        <Button variant="ghost" w="fit-content" p="0" mb="-4px" onClick={goBack} color="text/50">
                            <Icon as={RiArrowLeftLine} boxSize="20px" />
                            <Text fontSize="sm">Назад</Text>
                        </Button>

                        <Heading size="lg" fontWeight="700">Номер телефона</Heading>
                        <Text color="text/50" fontSize="sm" mt="-8px">
                            Введите ваш номер для входа или регистрации
                        </Text>

                        <Input
                            ref={phoneInputRef}
                            placeholder="+7 (999) 123-45-67"
                            value={phone}
                            onChange={handlePhoneChange}
                            type="tel"
                            size="lg"
                            h="56px"
                            borderRadius="16px"
                            borderWidth="2px"
                            borderColor="gray"
                            fontSize="lg"
                            fontWeight="600"
                            autoFocus
                            onKeyDown={(e) => { if (e.key === 'Enter') handlePhoneSubmit() }}
                        />

                        {error && <Text color="red.500" fontSize="sm">{error}</Text>}

                        <Button
                            size="lg"
                            h="56px"
                            borderRadius="18px"
                            bg="accent"
                            color="token-black"
                            fontWeight="700"
                            onClick={handlePhoneSubmit}
                            disabled={loading}
                        >
                            {loading ? <Spinner size="sm" /> : 'Продолжить'}
                        </Button>
                    </Flex>
                )}

                {/* LOGIN CONFIRM step */}
                {step === 'login_confirm' && (
                    <Flex direction="column" gap="16px">
                        <Button variant="ghost" w="fit-content" p="0" mb="-4px" onClick={goBack} color="text/50">
                            <Icon as={RiArrowLeftLine} boxSize="20px" />
                            <Text fontSize="sm">Назад</Text>
                        </Button>

                        <Heading size="lg" fontWeight="700">
                            {foundName ? `Привет, ${foundName}!` : 'С возвращением!'}
                        </Heading>
                        <Text color="text/50" fontSize="sm" mt="-8px">
                            Нашли аккаунт, привязанный к номеру
                        </Text>
                        <Box
                            bg="gray"
                            borderRadius="14px"
                            px="16px"
                            py="14px"
                        >
                            <Text fontWeight="700" fontSize="lg">{phone}</Text>
                        </Box>

                        {error && <Text color="red.500" fontSize="sm">{error}</Text>}

                        <Button
                            size="lg"
                            h="56px"
                            borderRadius="18px"
                            bg="accent"
                            color="token-black"
                            fontWeight="700"
                            onClick={handleLogin}
                            disabled={loading}
                        >
                            {loading ? <Spinner size="sm" /> : 'Войти'}
                        </Button>
                    </Flex>
                )}

                {/* REGISTER step */}
                {step === 'register' && (
                    <Flex direction="column" gap="16px">
                        <Button variant="ghost" w="fit-content" p="0" mb="-4px" onClick={goBack} color="text/50">
                            <Icon as={RiArrowLeftLine} boxSize="20px" />
                            <Text fontSize="sm">Назад</Text>
                        </Button>

                        <Heading size="lg" fontWeight="700">Регистрация</Heading>
                        <Text color="text/50" fontSize="sm" mt="-8px">
                            Номер <Text as="span" fontWeight="700" color="text">{phone}</Text> не найден. Создадим аккаунт?
                        </Text>

                        <Input
                            placeholder="Имя *"
                            value={firstName}
                            onChange={(e) => { setFirstName(e.target.value); setError(null) }}
                            size="lg"
                            h="56px"
                            borderRadius="16px"
                            borderWidth="2px"
                            borderColor="gray"
                            fontWeight="600"
                            autoFocus
                        />
                        <Input
                            placeholder="Фамилия (необязательно)"
                            value={lastName}
                            onChange={(e) => setLastName(e.target.value)}
                            size="lg"
                            h="56px"
                            borderRadius="16px"
                            borderWidth="2px"
                            borderColor="gray"
                            fontWeight="600"
                            onKeyDown={(e) => { if (e.key === 'Enter') handleRegister() }}
                        />

                        {error && <Text color="red.500" fontSize="sm">{error}</Text>}

                        <Button
                            size="lg"
                            h="56px"
                            borderRadius="18px"
                            bg="accent"
                            color="token-black"
                            fontWeight="700"
                            onClick={handleRegister}
                            disabled={loading}
                        >
                            {loading ? <Spinner size="sm" /> : 'Зарегистрироваться'}
                        </Button>
                    </Flex>
                )}

                <Box h="env(safe-area-inset-bottom, 32px)" minH="32px" />
            </Flex>
        </Center>
    )
}
