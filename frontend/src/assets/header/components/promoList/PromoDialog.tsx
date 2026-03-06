import { Box, CloseButton, Dialog, Portal, Image } from '@chakra-ui/react'
import PromoCard from './PromoCard'

type PromoDialogProps = {
    image: string
    isViewed: boolean
    onClick?: () => void
}

export default function PromoDialog({
    image,
    isViewed,
    onClick,
}: PromoDialogProps) {
    return (
        <Dialog.Root size="full">
            <Dialog.Trigger asChild>
                <PromoCard
                    image={image}
                    isViewed={isViewed}
                    onClick={onClick}
                />
            </Dialog.Trigger>
            <Portal>
                <Dialog.Positioner>
                    <Dialog.Content bg="back/90" backdropFilter="blur(20px)">
                        <Dialog.Body
                            p="0"
                            pos="relative"
                            display="flex"
                            justifyContent="center"
                            alignItems="center"
                            minH="100dvh"
                        >
                            <Dialog.CloseTrigger asChild>
                                <Box position="absolute" inset="0" />
                            </Dialog.CloseTrigger>
                            <Image
                                pos="relative"
                                zIndex={1}
                                src={image}
                                maxH="100dvh"
                                maxW="100vw"
                                w="auto"
                                h="auto"
                                objectFit="contain"
                            />
                        </Dialog.Body>
                        <Dialog.CloseTrigger asChild>
                            <CloseButton
                                size="sm"
                                pos="absolute"
                                top="12px"
                                right="12px"
                                zIndex={2}
                            />
                        </Dialog.CloseTrigger>
                    </Dialog.Content>
                </Dialog.Positioner>
            </Portal>
        </Dialog.Root>
    )
}
