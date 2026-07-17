import { Button, Image } from '@chakra-ui/react'
import { ComponentProps, forwardRef } from 'react'

type PromoCardProps = {
    image: string
    isViewed: boolean
} & ComponentProps<typeof Button>

// forwardRef + prop spread so Chakra's <Dialog.Trigger asChild> can attach its
// onClick / ref / data-state to the underlying button.
const PromoCard = forwardRef<HTMLButtonElement, PromoCardProps>(
    ({ image, isViewed, ...rest }, ref) => (
        <Button
            ref={ref}
            bg="back"
            rounded="20px"
            h="180px"
            w="120px"
            p="0"
            overflow="hidden"
            flexShrink={0}
            opacity={isViewed ? '50%' : '100%'}
            borderWidth={isViewed ? '0px' : '1px'}
            borderColor="accent"
            {...rest}
        >
            <Image
                src={image}
                h={isViewed ? 'full' : '180px'}
                w={isViewed ? 'full' : '120px'}
                objectFit="cover"
                rounded={isViewed ? '0' : '17px'}
            />
        </Button>
    )
)

PromoCard.displayName = 'PromoCard'

export default PromoCard
