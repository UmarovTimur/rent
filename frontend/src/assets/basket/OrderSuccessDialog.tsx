import { Dialog, Text, Button, Flex } from '@chakra-ui/react'
import { useOrder } from '@/contexts/OrderContext'

const BOT_LINK = 'https://t.me/camping_rent_uz_bot'

export default function OrderSuccessDialog() {
    const { isReceiptNoticeOpen, closeReceiptNotice } = useOrder()

    const handleGoToBot = () => {
        closeReceiptNotice()
        const webApp = window.Telegram?.WebApp
        if (webApp?.close) {
            // Внутри Telegram: сворачиваем Mini App — пользователь попадает в чат с ботом.
            webApp.close()
        } else {
            window.open(BOT_LINK, '_blank')
        }
    }

    return (
        <Dialog.Root open={isReceiptNoticeOpen} onOpenChange={closeReceiptNotice} placement="center">
            <Dialog.Backdrop bg="back/90" backdropFilter="blur(8px)" />
            <Dialog.Positioner>
                <Dialog.Content bg="card" p="gap" rounded="42px" gap="0" w="90%">
                    <Dialog.Header p="0" pt="gap">
                        <Dialog.Title textAlign="center" fontSize="xl" fontWeight="700" w="full">
                            ⏳ Заявка принята
                        </Dialog.Title>
                        <Dialog.CloseTrigger position="absolute" right="24px" top="24px" />
                    </Dialog.Header>

                    <Dialog.Body px="0" py="gap">
                        <Text fontSize="md" textAlign="center">
                            Бронь ещё не подтверждена. Мы отправили вам в Telegram-бот реквизиты
                            для предоплаты — переведите её и пришлите боту чек из банковского
                            приложения. После проверки чека мы подтвердим вашу бронь.
                        </Text>
                    </Dialog.Body>

                    <Dialog.Footer p="0">
                        <Flex w="full" direction="column" gap="12px">
                            <Button
                                w="full"
                                onClick={handleGoToBot}
                                bg="accent"
                                h="48px"
                                rounded="full"
                                color="text"
                                fontWeight="700"
                                fontSize="md"
                            >
                                Отправить чек боту
                            </Button>
                            <Button
                                w="full"
                                onClick={closeReceiptNotice}
                                bg="back"
                                h="48px"
                                rounded="full"
                                color="text"
                                fontWeight="700"
                                fontSize="md"
                            >
                                Позже
                            </Button>
                        </Flex>
                    </Dialog.Footer>
                </Dialog.Content>
            </Dialog.Positioner>
        </Dialog.Root>
    )
}
