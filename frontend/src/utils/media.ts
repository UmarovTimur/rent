// Product images are stored as bare filenames (e.g. "<uuid>.jpg") and served by
// the backend under /media/products/. Use an absolute path so the URL does not
// resolve against the app's "/app/" base.
export const productImageSrc = (filename: string) => `/media/products/${filename}`
