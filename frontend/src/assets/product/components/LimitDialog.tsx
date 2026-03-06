import { Dialog, Text, Button } from '@chakra-ui/react'
import { ReactNode } from 'react'

type LimitDialogProps = {
    isOpen: boolean
    onClose: () => void
    title: string
    message: ReactNode
}

export default function LimitDialog({
    isOpen,
    onClose,
    title,
    message,
}: LimitDialogProps) {
    return (
        <Dialog.Root open={isOpen} onOpenChange={onClose} placement="center">
            <Dialog.Backdrop bg="back/90" backdropFilter="blur(8px)" />
            <Dialog.Positioner p={{ base: '12px', sm: '16px' }}>
                <Dialog.Content
                    bg="card"
                    p={{ base: '12px', sm: 'gap' }}
                    rounded={{ base: '24px', sm: '42px' }}
                    gap="gap"
                    w="full"
                    maxW="420px"
                >
                    <Dialog.Header p="0" pt={{ base: '8px', sm: 'gap' }}>
                        <Dialog.Title
                            textAlign="center"
                            fontSize={{ base: 'xl', sm: '2xl' }}
                            fontWeight="700"
                            w="full"
                            lineHeight="1.2"
                            pr={{ base: '28px', sm: '0' }}
                        >
                            {title}
                        </Dialog.Title>
                        <Dialog.CloseTrigger
                            position="absolute"
                            right={{ base: '12px', sm: '24px' }}
                            top={{ base: '12px', sm: '24px' }}
                        />
                    </Dialog.Header>

                    <Dialog.Body px="0" py={{ base: '12px', sm: 'gap' }}>
                        <Text fontSize={{ base: 'md', sm: 'lg' }} textAlign="center">
                            {message}
                        </Text>
                    </Dialog.Body>

                    <Dialog.Footer p="0">
                        <Button
                            w="full"
                            onClick={onClose}
                            bg="accent"
                            h={{ base: '48px', sm: '56px' }}
                            rounded="full"
                            color="text"
                            fontWeight="700"
                            fontSize={{ base: 'md', sm: 'lg' }}
                        >
                            Понятно
                        </Button>
                    </Dialog.Footer>
                </Dialog.Content>
            </Dialog.Positioner>
        </Dialog.Root>
    )
}
