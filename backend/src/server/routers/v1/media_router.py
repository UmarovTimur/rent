import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

MEDIA_PRODUCTS = Path("/media/products")

router = APIRouter(prefix="/media", tags=["media"])


@router.post("/products/upload")
async def upload_product_image(file: UploadFile = File(...)):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    MEDIA_PRODUCTS.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "").suffix.lower() or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    (MEDIA_PRODUCTS / filename).write_bytes(content)
    return {"url": f"/media/products/{filename}"}


@router.get("/products")
async def list_product_images() -> list[str]:
    if not MEDIA_PRODUCTS.exists():
        return []
    files = sorted(MEDIA_PRODUCTS.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    return [f"/media/products/{f.name}" for f in files if f.is_file()]


@router.delete("/products/{filename}")
async def delete_product_image(filename: str):
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = MEDIA_PRODUCTS / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    path.unlink()
    return {"deleted": filename}
