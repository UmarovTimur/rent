import { useEffect, useState } from 'react'
import Lightbox from 'yet-another-react-lightbox'
import Zoom from 'yet-another-react-lightbox/plugins/zoom'
import 'yet-another-react-lightbox/styles.css'

type Props = {
    open: boolean
    onClose: () => void
    images: string[]
    index?: number
    alt?: string
}

// Push the lightbox controls below the device notch + Telegram's overlay buttons.
const TOP_INSET =
    'calc(var(--tg-safe-area-inset-top, 0px) + var(--tg-content-safe-area-inset-top, 0px) + env(safe-area-inset-top, 0px))'

/**
 * Fullscreen image viewer used across the app: swipe to switch images,
 * pinch (or double-tap / wheel) to zoom. Closes only via the × button so
 * touch gestures never dismiss it accidentally.
 */
export default function ImageLightbox({ open, onClose, images, index = 0, alt }: Props) {
    // Controlled index: seed from `index` on open and track internal navigation,
    // otherwise a re-render (e.g. while pinch-zooming) snaps back to the first slide.
    const [currentIndex, setCurrentIndex] = useState(index)
    useEffect(() => {
        if (open) setCurrentIndex(index)
    }, [open, index])

    return (
        <Lightbox
            open={open}
            close={onClose}
            index={currentIndex}
            on={{ view: ({ index: i }) => setCurrentIndex(i) }}
            slides={images.map((src) => ({ src, alt }))}
            plugins={[Zoom]}
            zoom={{
                maxZoomPixelRatio: 4,
                pinchZoomDistanceFactor: 100,
                doubleTapDelay: 250,
            }}
            carousel={{ finite: images.length <= 1 }}
            controller={{
                closeOnBackdropClick: true,
                closeOnPullDown: false,
                closeOnPullUp: false,
            }}
            render={images.length <= 1 ? { buttonPrev: () => null, buttonNext: () => null } : undefined}
            styles={{
                container: { backgroundColor: 'rgba(0,0,0,0.92)' },
                toolbar: { paddingTop: TOP_INSET },
            }}
        />
    )
}
