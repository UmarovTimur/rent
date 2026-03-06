import { HStack, IconButton, NumberInput, Icon } from '@chakra-ui/react'
import { FaPlus, FaMinus } from 'react-icons/fa'

type NumberInputProps = {
    setQuantity: (quantity: number) => void
    small?: boolean
    defaultValue?: string
    value?: string
    max?: number
    disabled?: boolean
}

export default function CustomNumberInput({
    setQuantity,
    small,
    defaultValue,
    value,
    max = 99,
    disabled = false,
}: NumberInputProps) {
    return (
        <NumberInput.Root
            unstyled
            spinOnPress={false}
            onValueChange={(e) => {
                const parsed = Number(e.value)
                if (!Number.isFinite(parsed)) {
                    setQuantity(1)
                    return
                }

                const clamped = Math.min(Math.max(parsed, 1), max)
                setQuantity(clamped)
            }}
            bg="back"
            p={small ? '6px' : '8px'}
            h={small ? '32px' : '48px'}
            rounded="full"
            defaultValue={defaultValue ? defaultValue : '1'}
            value={value}
            min={1}
            max={max}
            disabled={disabled}
        >
            <HStack gap={small ? '1' : '2'}>
                <NumberInput.DecrementTrigger asChild>
                    <IconButton
                        bg="accent"
                        rounded="full"
                        maxH={small ? '20px' : '32px'}
                        minW={small ? '20px' : '32px'}
                        color="text"
                        disabled={disabled}
                    >
                        <Icon as={FaMinus} boxSize={small ? 2 : 4} />
                    </IconButton>
                </NumberInput.DecrementTrigger>
                <NumberInput.ValueText
                    textAlign="center"
                    fontSize={small ? 'md' : 'xl'}
                    fontWeight="700"
                    minW={small ? '24px' : '32px'}
                    maxW={small ? '24px' : '32px'}
                    color="text"
                />
                <NumberInput.IncrementTrigger asChild>
                    <IconButton
                        bg="accent"
                        rounded="full"
                        maxH={small ? '20px' : '32px'}
                        minW={small ? '20px' : '32px'}
                        color="text"
                        disabled={disabled}
                    >
                        <Icon as={FaPlus} boxSize={small ? 2 : 4} />
                    </IconButton>
                </NumberInput.IncrementTrigger>
            </HStack>
        </NumberInput.Root>
    )
}
