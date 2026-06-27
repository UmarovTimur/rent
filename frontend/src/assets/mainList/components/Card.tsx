import React from 'react'
import { Text, Flex, Button, Image, Heading, Mark, Box } from '@chakra-ui/react'
import { Product } from '@/types/Products.ts'
import { formatPriceK } from '@/utils/price'

type CardProps = {
    product: Product
    onClick?: React.MouseEventHandler
}

export default function Card({ product, onClick }: CardProps) {
    const imgSrc = product.image_url ? `products/${product.image_url}` : 'shava.png'

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
        >
            {/* Image */}
            <Box
                flexShrink={0}
                h={{ base: 'full', md: 'auto' }}
                w={{ base: '132px', md: 'full' }}
                marginRight={{ base: '20px', md: '0' }}
                aspectRatio={{ md: '2/3' }}
                overflow="hidden"
            >
                <Image
                    src={imgSrc}
                    h="full"
                    w="full"
                    alt={product.name}
                    objectFit="cover"
                    display="block"
                />
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
