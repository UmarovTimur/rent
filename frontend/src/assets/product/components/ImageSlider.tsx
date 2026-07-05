import { Box, Flex } from '@chakra-ui/react'
import { animate, motion, PanInfo, useMotionValue } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { IoExpandOutline } from 'react-icons/io5'
import ImageLightbox from '@/components/ImageLightbox'

type Props = {
    images: string[]
    rounded?: string | object
    width?: string | object
    maxW?: string | object
    aspectRatio?: string | number | object
    alt?: string
}

const spring = { type: 'spring', stiffness: 500, damping: 45 } as const
// A press only counts as a tap (open zoom) if the finger moved less than this.
const TAP_MOVE_TOLERANCE = 8

export default function ImageSlider({ images, rounded, width, maxW, aspectRatio = 2 / 3, alt }: Props) {
    const [idx, setIdx] = useState(0)
    const [zoomOpen, setZoomOpen] = useState(false)
    const containerRef = useRef<HTMLDivElement | null>(null)
    const pressStart = useRef<{ x: number; y: number } | null>(null)
    const x = useMotionValue(0)

    const w = () => containerRef.current?.offsetWidth ?? 0

    // Keep the strip aligned to the current slide when idx changes or on resize.
    useEffect(() => {
        const controls = animate(x, -idx * w(), spring)
        const el = containerRef.current
        const ro = el ? new ResizeObserver(() => x.set(-idx * w())) : null
        if (el && ro) ro.observe(el)
        return () => {
            controls.stop()
            ro?.disconnect()
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [idx, images.length])

    const handleDragEnd = (_: unknown, info: PanInfo) => {
        const width = w() || 1
        const off = info.offset.x
        const vel = info.velocity.x
        let next = idx
        if ((off < -width * 0.2 || vel < -400) && idx < images.length - 1) next = idx + 1
        else if ((off > width * 0.2 || vel > 400) && idx > 0) next = idx - 1
        if (next === idx) animate(x, -idx * width, spring)
        else setIdx(next)
    }

    // Manual tap detection: only open the zoom when the pointer barely moved,
    // so a swipe (slide change) never triggers it.
    const handlePointerDown = (e: React.PointerEvent) => {
        pressStart.current = { x: e.clientX, y: e.clientY }
    }
    const handlePointerUp = (e: React.PointerEvent) => {
        const start = pressStart.current
        pressStart.current = null
        if (!start) return
        const moved = Math.hypot(e.clientX - start.x, e.clientY - start.y)
        if (moved < TAP_MOVE_TOLERANCE) setZoomOpen(true)
    }

    return (
        <Box
            ref={containerRef}
            position="relative"
            width={width}
            maxW={maxW}
            aspectRatio={aspectRatio}
            overflow="hidden"
            rounded={rounded}
        >
            {/* Draggable strip — follows the finger in real time, snaps on release */}
            <motion.div
                drag={images.length > 1 ? 'x' : false}
                dragConstraints={containerRef}
                dragElastic={0.12}
                dragMomentum={false}
                onDragEnd={handleDragEnd}
                onPointerDown={handlePointerDown}
                onPointerUp={handlePointerUp}
                style={{
                    x,
                    display: 'flex',
                    height: '100%',
                    width: `${images.length * 100}%`,
                    cursor: images.length > 1 ? 'grab' : 'zoom-in',
                    touchAction: 'pan-y',
                }}
            >
                {images.map((s, i) => (
                    <img
                        key={i}
                        src={s}
                        alt={alt}
                        draggable={false}
                        style={{
                            width: `${100 / images.length}%`,
                            height: '100%',
                            objectFit: 'contain',
                            objectPosition: 'center',
                            flexShrink: 0,
                            pointerEvents: 'none',
                            userSelect: 'none',
                        }}
                    />
                ))}
            </motion.div>

            {images.length > 1 && (
                <Flex
                    position="absolute" bottom="10px" left="0" right="0"
                    justify="center" gap="5px" zIndex="2"
                    style={{ filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.65))' }}
                >
                    {images.map((_, i) => (
                        <Box
                            key={i}
                            h="5px"
                            rounded="full"
                            cursor="pointer"
                            bg={i === idx ? 'white' : 'rgba(255,255,255,0.55)'}
                            onClick={() => setIdx(i)}
                            style={{
                                width: i === idx ? '18px' : '5px',
                                transition: 'all 0.25s ease',
                            }}
                        />
                    ))}
                </Flex>
            )}

            {/* Explicit zoom button as well */}
            <Flex
                position="absolute" top="10px" right="10px" zIndex="3"
                align="center" justify="center"
                w="34px" h="34px" rounded="full" cursor="pointer"
                bg="rgba(0,0,0,0.45)" color="white" fontSize="18px"
                onClick={() => setZoomOpen(true)}
            >
                <IoExpandOutline />
            </Flex>

            <ImageLightbox
                open={zoomOpen}
                onClose={() => setZoomOpen(false)}
                images={images}
                index={idx}
                alt={alt}
            />
        </Box>
    )
}
