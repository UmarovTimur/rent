import { Dialog, Text, Button } from '@chakra-ui/react'
import { useOrder } from '@/contexts/OrderContext'

export default function OrderSuccessDialog() {
    const { isReceiptNoticeOpen, closeReceiptNotice } = useOrder()

    return (
        <Dialog.Root open={isReceiptNoticeOpen} onOpenChange={closeReceiptNotice} placement="center">
            <Dialog.Backdrop bg="back/90" backdropFilter="blur(8px)" />
            <Dialog.Positioner>
                <Dialog.Content bg="card" p="gap" rounded="42px" gap="0" w="90%">
                    <Dialog.Header p="0" pt="gap">
                        <Dialog.Title textAlign="center" fontSize="xl" fontWeight="700" w="full">
                            ✅ Заказ оформлен!
                        </Dialog.Title>
                        <Dialog.CloseTrigger position="absolute" right="24px" top="24px" />
                    </Dialog.Header>

                    <Dialog.Body px="0" py="gap">
                        <Text fontSize="md" textAlign="center">
                            Для подтверждения брони переведите предоплату и отправьте чек в
                            Telegram-бот. Реквизиты для оплаты — в сообщении от бота.
                        </Text>
                    </Dialog.Body>

                    <Dialog.Footer p="0">
                        <Button
                            w="full"
                            onClick={closeReceiptNotice}
                            bg="accent"
                            h="48px"
                            rounded="full"
                            color="text"
                            fontWeight="700"
                            fontSize="md"
                        >
                            Понятно
                        </Button>
                    </Dialog.Footer>
                </Dialog.Content>
            </Dialog.Positioner>
        </Dialog.Root>
    )
}
