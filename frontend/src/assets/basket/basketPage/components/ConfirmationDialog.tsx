import { Dialog, Text, Button, Flex } from '@chakra-ui/react'
import { ReactNode } from 'react'
import { useTranslation } from '@/i18n/LanguageContext'

type ConfirmationDialogProps = {
    isOpen: boolean
    onClose: () => void
    onConfirm: () => void
    title: string
    message: ReactNode
    confirmLabel?: string
    confirmColor?: string
}

export default function ConfirmationDialog({
    isOpen,
    onClose,
    onConfirm,
    title,
    message,
    confirmLabel,
    confirmColor = 'red.500',
}: ConfirmationDialogProps) {
    const { t } = useTranslation()
    return (
        <Dialog.Root open={isOpen} onOpenChange={onClose} placement="center">
            <Dialog.Backdrop bg="back/90" backdropFilter="blur(8px)" />
            <Dialog.Positioner>
                <Dialog.Content
                    bg="card"
                    p="gap"
                    rounded="42px"
                    gap="0"
                    w="90%"
                >
                    <Dialog.Header p="0" pt="gap">
                        <Dialog.Title
                            textAlign="center"
                            fontSize="xl"
                            fontWeight="700"
                            w="full"
                        >
                            {title}
                        </Dialog.Title>
                        <Dialog.CloseTrigger
                            position="absolute"
                            right="24px"
                            top="24px"
                        />
                    </Dialog.Header>

                    <Dialog.Body px="0" py="gap">
                        <Text fontSize="md" textAlign="center">
                            {message}
                        </Text>
                    </Dialog.Body>

                    <Dialog.Footer p="0" gap="12px">
                        <Flex w="full" gap="12px">
                            <Button
                                flex="1"
                                onClick={onClose}
                                bg="back"
                                h="48px"
                                rounded="full"
                                color="text"
                                fontWeight="700"
                                fontSize="md"
                            >
                                {t('cancel')}
                            </Button>
                            <Button
                                flex="1"
                                onClick={() => {
                                    onConfirm()
                                    onClose()
                                }}
                                bg={confirmColor}
                                h="48px"
                                rounded="full"
                                color="white"
                                fontWeight="700"
                                fontSize="md"
                            >
                                {confirmLabel ?? t('remove')}
                            </Button>
                        </Flex>
                    </Dialog.Footer>
                </Dialog.Content>
            </Dialog.Positioner>
        </Dialog.Root>
    )
}
