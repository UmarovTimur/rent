import { Alert, Box, Center, ChakraProvider, Heading, Spinner, Text } from '@chakra-ui/react'
import { useEffect, useState } from 'react'
import { startOfWeek, endOfWeek } from 'date-fns'
import axios from 'axios'
import { system } from './theme.ts'
import { Toaster } from '@/components/ui/toaster'
import { AdminRentalService } from '@/api/AdminRentalService'
import AdminCalendar from '@/assets/admin/AdminCalendar'

type AccessState = 'checking' | 'granted' | 'denied' | 'error'

export default function AdminApp() {
    const [access, setAccess] = useState<AccessState>('checking')

    useEffect(() => {
        const checkAccess = async () => {
            try {
                const from = startOfWeek(new Date(), { weekStartsOn: 1 })
                const to = endOfWeek(new Date(), { weekStartsOn: 1 })
                await AdminRentalService.getRentals(from.toISOString(), to.toISOString())
                setAccess('granted')
            } catch (error) {
                if (axios.isAxiosError(error) && error.response?.status === 403) {
                    setAccess('denied')
                } else {
                    console.error('Failed to check admin access:', error)
                    setAccess('error')
                }
            }
        }
        checkAccess()
    }, [])

    return (
        <ChakraProvider value={system}>
            {access === 'checking' && (
                <Center h="100vh">
                    <Spinner size="xl" />
                </Center>
            )}

            {access === 'denied' && (
                <Center h="100vh" px="4">
                    <Box textAlign="center">
                        <Heading size="lg" mb="2">
                            Нет доступа
                        </Heading>
                        <Text color="fg.muted">У вас нет прав администратора для просмотра этого раздела.</Text>
                    </Box>
                </Center>
            )}

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
