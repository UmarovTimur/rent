import React, { useCallback, useState } from 'react'
import { Text, Flex, Button, Image, Heading, Mark, Box } from '@chakra-ui/react'
import { Product } from '@/types/Products.ts'
import { formatPriceK } from '@/utils/price'

type CardProps = {
    product: Product
    onClick?: React.MouseEventHandler
    unavailable?: boolean
}

export default function Card({ product, onClick, unavailable = false }: CardProps) {
    const [hoverIdx, setHoverIdx] = useState(0)

    const allImages: string[] = [
        ...(product.image_url ? [`products/${product.image_url}`] : []),
        ...(product.image_urls ?? []).map(u => `products/${u}`),
    ]
    if (allImages.length === 0) allImages.push('shava.png')

    const imgSrc = allImages[hoverIdx]
    const imgCount = allImages.length

    const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        if (imgCount <= 1) return
        const rect = e.currentTarget.getBoundingClientRect()
        const idx = Math.min(
            imgCount - 1,
            Math.floor(((e.clientX - rect.left) / rect.width) * imgCount)
        )
        setHoverIdx(idx)
    }, [imgCount])

    const handleMouseLeave = useCallback(() => setHoverIdx(0), [])

    return (
        <Button
            borderWidth="1px"
            borderColor="gray"
            rounded="26px"
            overflow="hidden"
            bg="card"
            w="full"
            h={{ base: '180px', md: 'auto' }}
            justifyContent={{ base: 'space-between', md: 'flex-start' }}
            alignItems={{ base: 'center', md: 'stretch' }}
            flexDirection={{ base: 'row', md: 'column' }}
            p="0"
            gap="0"
            zIndex="0"
            onClick={onClick}
            opacity={unavailable ? 0.55 : 1}
            filter={unavailable ? 'grayscale(0.6)' : 'none'}
            transition="opacity 0.2s ease, filter 0.2s ease"
        >
            {/* Image with hover-zone effect */}
            <Box
                position="relative"
                flexShrink={0}
                h={{ base: 'full', md: 'auto' }}
                w={{ base: '132px', md: 'full' }}
                marginRight={{ base: '20px', md: '0' }}
                aspectRatio={{ md: '2/3' }}
                overflow="hidden"
                onMouseMove={handleMouseMove}
                onMouseLeave={handleMouseLeave}
            >
                <Image
                    src={imgSrc}
                    h="full"
                    w="full"
                    alt={product.name}
                    objectFit="cover"
                    display="block"
                    style={{ transition: 'opacity 0.15s ease' }}
                />

                {unavailable && (
                    <Flex
                        position="absolute"
                        top="8px"
                        left="8px"
                        bg="blackAlpha.700"
                        color="white"
                        px="10px"
                        h="24px"
                        alignItems="center"
                        rounded="full"
                        fontSize="2xs"
                        fontWeight="700"
                        pointerEvents="none"
                    >
                        Недоступно
                    </Flex>
                )}

                {/* Hover zone indicators (thin dots at bottom) */}
                {imgCount > 1 && (
                    <Flex
                        position="absolute"
                        bottom="5px"
                        left="0"
                        right="0"
                        justify="center"
                        gap="3px"
                        pointerEvents="none"
                    >
                        {allImages.map((_, i) => (
                            <Box
                                key={i}
                                h="3px"
                                rounded="full"
                                bg={i === hoverIdx ? 'white' : 'rgba(255,255,255,0.4)'}
                                style={{
                                    width: i === hoverIdx ? '14px' : '4px',
                                    transition: 'all 0.15s ease',
                                }}
                            />
                        ))}
                    </Flex>
                )}
            </Box>

            {/* Content */}
            <Flex
                flexDirection="column"
                flex={1}
                height={{ base: 'full', md: 'auto' }}
                width={{ base: 'auto', md: 'full' }}
                pb="12px"
                pt={{ base: '6px', md: '12px' }}
                px={{ base: '0', md: '14px' }}
                justifyContent="space-between"
                gap={{ md: '8px' }}
            >
                <Heading
                    color="text"
                    textAlign="left"
                    w={{ base: '95%', md: 'full' }}
                    size={{ base: '2xl', md: 'lg' }}
                    fontWeight="700"
                    textWrap="wrap"
                    lineClamp={{ md: 2 }}
                >
                    {product.name}
                </Heading>

                <Text
                    color="text"
                    fontWeight="400"
                    opacity="50%"
                    lineClamp="2"
                    textAlign="left"
                    w={{ base: '95%', md: 'full' }}
                    lineHeight="15px"
                    fontSize="xs"
                    mb="4px"
                >
                    {product.description}
                </Text>

                <Flex
                    flexWrap="wrap"
                    gap="10px"
                    justifyContent="space-between"
                    alignItems="center"
                    w={{ base: 'calc(100% - 12px)', md: 'full' }}
                >
                    <Flex
                        h="hb"
                        bg="gray"
                        color="text"
                        alignItems="center"
                        justifyContent="center"
                        px="16px"
                        rounded="full"
                        fontSize="s"
                        fontWeight="500"
                    >
                        <Mark color="accent">{formatPriceK(product.price)}&nbsp;</Mark>в день
                    </Flex>

                    <Flex
                        h="hb"
                        bg="accent"
                        color="text"
                        alignItems="center"
                        justifyContent="center"
                        px="20px"
                        rounded="full"
                        fontWeight="600"
                        fontSize="xl"
                    >
                        +
                    </Flex>
                </Flex>
            </Flex>
        </Button>
    )
}
