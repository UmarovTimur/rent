import { Box, CloseButton, Dialog, Flex, Image, Portal } from '@chakra-ui/react'
import { useEffect, useState } from 'react'
import PromoCard from './PromoCard'
import { promoMediaSrc } from '@/utils/media'

type PromoDialogProps = {
    frames: string[]
    isViewed: boolean
    onView?: () => void
}

const FRAME_MS = 4000

// Instagram-story-style viewer: tap right = next frame, tap left = previous,
// auto-advance, progress bars on top. Advancing past the last frame closes it.
export default function PromoDialog({ frames, isViewed, onView }: PromoDialogProps) {
    const [open, setOpen] = useState(false)
    const [index, setIndex] = useState(0)

    const cover = frames[0]

    // Reset to the first frame and mark viewed whenever the story is opened.
    useEffect(() => {
        if (open) {
            setIndex(0)
            onView?.()
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [open])

    // Auto-advance the current frame; re-armed on every frame change.
    useEffect(() => {
        if (!open) return
        const timer = window.setTimeout(() => {
            setIndex((i) => {
                if (i + 1 >= frames.length) {
                    setOpen(false)
                    return i
                }
                return i + 1
            })
        }, FRAME_MS)
        return () => window.clearTimeout(timer)
    }, [open, index, frames.length])

    const goPrev = () => setIndex((i) => Math.max(0, i - 1))
    const goNext = () => {
        if (index + 1 >= frames.length) setOpen(false)
        else setIndex(index + 1)
    }

    return (
        <Dialog.Root size="full" open={open} onOpenChange={(e) => setOpen(e.open)}>
            <Dialog.Trigger asChild>
                <PromoCard image={promoMediaSrc(cover)} isViewed={isViewed} />
            </Dialog.Trigger>
            <Portal>
                <Dialog.Positioner>
                    <Dialog.Content bg="back/95" backdropFilter="blur(20px)">
                        <Dialog.Body
                            p="0"
                            pos="relative"
                            display="flex"
                            justifyContent="center"
                            alignItems="center"
                            minH="100dvh"
                        >
                            <Flex
                                gap="4px"
                                pos="absolute"
                                top="calc(var(--tg-safe-area-inset-top, 0px) + 10px)"
                                left="10px"
                                right="10px"
                                zIndex={3}
                            >
                                {frames.map((_, i) => (
                                    <Box
                                        key={i}
                                        flex="1"
                                        h="3px"
                                        rounded="full"
                                        bg={i <= index ? 'accent' : 'whiteAlpha.400'}
                                        transition="background 0.2s"
                                    />
                                ))}
                            </Flex>

                            <Image
                                pos="relative"
                                zIndex={1}
                                src={promoMediaSrc(frames[index])}
                                maxH="100dvh"
                                maxW="100vw"
                                w="auto"
                                h="auto"
                                objectFit="contain"
                            />

                            {/* Tap zones: left third = prev, right = next. */}
                            <Flex pos="absolute" inset="0" zIndex={2}>
                                <Box w="33%" h="full" onClick={goPrev} />
                                <Box flex="1" h="full" onClick={goNext} />
                            </Flex>

                            <CloseButton
                                size="sm"
                                pos="absolute"
                                top="calc(var(--tg-safe-area-inset-top, 0px) + 16px)"
                                right="12px"
                                zIndex={4}
                                onClick={() => setOpen(false)}
                            />
                        </Dialog.Body>
                    </Dialog.Content>
                </Dialog.Positioner>
            </Portal>
        </Dialog.Root>
    )
}
