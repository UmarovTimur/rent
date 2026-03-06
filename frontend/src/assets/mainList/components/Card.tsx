import React from 'react'
import { Text, Flex, Button, Image, Heading, Mark } from '@chakra-ui/react'
import { Product } from '@/types/Products.ts'
import { formatPriceK } from '@/utils/price'

type CardProps = {
    product: Product
    onClick?: React.MouseEventHandler
}

export default function Card({ product, onClick }: CardProps) {
    return (
        <Button
            borderWidth="1px"
            borderColor="gray"
            rounded="26px"
            overflow="hidden"
            bg="back"
            w="full"
            h="180px"
            justifyContent="space-between"
            p="0"
            gap="0"
            zIndex="0"
            onClick={onClick}
        >
            <Image
                src={product.image_url ? `products/${product.image_url}` : 'shava.png'}
                h="full"
                minW="132px"
                margin="0 20px 0 0"
                alt={product.name}
            />

            <Flex
                flexDirection="column"
                flex="2"
                height="full"
                pb="12px"
                pt="6px"
                justifyContent="space-between"
            >
                <Heading
                    color="text"
                    textAlign="left"
                    w="95%"
                    size="2xl"
                    fontWeight="700"
                    textWrap="wrap"
                >
                    {product.name}
                </Heading>

                <Text
                    color="text"
                    fontWeight="400"
                    opacity="50%"
                    lineClamp="3"
                    textAlign="left"
                    w="95%"
                    lineHeight="15px"
                    fontSize="xs"
                    mb="4px"
                >
                    {product.description}
                </Text>

                <Flex flexWrap="wrap" gap="10px" justifyContent="space-between" alignItems="center" w="calc(100% - 12px)">
                    <Flex
                        h="hb"
                        bg="gray"
                        color="text"
                        alignItems="center"
                        justifyContent="center"
                        px="20px"
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
