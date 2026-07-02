import { Box, Flex } from '@chakra-ui/react'
import { AnimatePresence, motion } from 'framer-motion'
import { useRef, useState } from 'react'

type Props = {
    images: string[]
    rounded?: string | object
    width?: string | object
    maxW?: string | object
    alt?: string
}

export default function ImageSlider({ images, rounded, width, maxW, alt }: Props) {
    const [idx, setIdx] = useState(0)
    const [dir, setDir] = useState(0)
    const touchStartX = useRef<number | null>(null)

    const goTo = (next: number) => {
        if (next === idx) return
        setDir(next > idx ? 1 : -1)
        setIdx(next)
    }

    const handleTouchStart = (e: React.TouchEvent) => {
        touchStartX.current = e.touches[0].clientX
    }

    const handleTouchEnd = (e: React.TouchEvent) => {
        if (touchStartX.current === null) return
        const diff = touchStartX.current - e.changedTouches[0].clientX
        if (Math.abs(diff) > 40) goTo(diff > 0 ? Math.min(images.length - 1, idx + 1) : Math.max(0, idx - 1))
        touchStartX.current = null
    }

    const src = images[idx] ?? 'shava.png'

    return (
        <Box
            position="relative"
            width={width}
            maxW={maxW}
            overflow="hidden"
            rounded={rounded}
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
        >
            <AnimatePresence mode="wait" initial={false} custom={dir}>
                <motion.img
                    key={src}
                    src={src}
                    alt={alt}
                    custom={dir}
                    initial={{ opacity: 0, x: `${dir * 40}%` }}
                    animate={{ opacity: 1, x: '0%' }}
                    exit={{ opacity: 0, x: `${-dir * 40}%` }}
                    transition={{ duration: 0.22, ease: 'easeInOut' }}
                    style={{ width: '100%', display: 'block', objectFit: 'cover' }}
                />
            </AnimatePresence>

            {images.length > 1 && (
                <>
                    {/* Left tap */}
                    <Box
                        position="absolute" left="0" top="0"
                        w="45%" h="full" zIndex="1" cursor="pointer"
                        onClick={() => goTo(Math.max(0, idx - 1))}
                    />
                    {/* Right tap */}
                    <Box
                        position="absolute" right="0" top="0"
                        w="45%" h="full" zIndex="1" cursor="pointer"
                        onClick={() => goTo(Math.min(images.length - 1, idx + 1))}
                    />
                    {/* Pagination dots */}
                    <Flex
                        position="absolute" bottom="10px" left="0" right="0"
                        justify="center" gap="5px" zIndex="2" pointerEvents="none"
                    >
                        {images.map((_, i) => (
                            <Box
                                key={i}
                                h="5px"
                                rounded="full"
                                bg={i === idx ? 'white' : 'rgba(255,255,255,0.45)'}
                                style={{
                                    width: i === idx ? '18px' : '5px',
                                    transition: 'all 0.25s ease',
                                }}
                            />
                        ))}
                    </Flex>
                </>
            )}
        </Box>
    )
}
