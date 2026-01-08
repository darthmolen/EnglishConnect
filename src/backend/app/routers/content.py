"""Content router for serving lesson assets."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.middleware.auth import OptionalUser

router = APIRouter(prefix="/api/content", tags=["content"])

# Path to lesson content images
# In Docker: /app/content/refined/ec1/books/...
# In dev: project_root/content/refined/ec1/books/...
def _get_images_dir() -> Path:
    """Get images directory, handling both Docker and local dev."""
    docker_path = Path("/app/content/refined/ec1/books/englishconnect_1_para_los_alumnos")
    if docker_path.exists():
        return docker_path
    # Local development - go up from routers to project root
    return (
        Path(__file__).parent.parent.parent.parent.parent
        / "content"
        / "refined"
        / "ec1"
        / "books"
        / "englishconnect_1_para_los_alumnos"
    )

IMAGES_DIR = _get_images_dir()


@router.get("/images/{image_name}")
async def get_image(image_name: str, current_user: OptionalUser):
    """Serve lesson images.

    Args:
        image_name: The image filename (e.g., "_page_19_Figure_1.jpeg")
        current_user: User (authenticated or anonymous)

    Returns:
        FileResponse with the image content
    """
    # Validate filename to prevent path traversal attacks
    if ".." in image_name or "/" in image_name or "\\" in image_name:
        raise HTTPException(status_code=400, detail="Invalid image name")

    image_path = IMAGES_DIR / image_name
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    # Determine media type based on extension
    suffix = image_path.suffix.lower()
    media_types = {
        ".jpeg": "image/jpeg",
        ".jpg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(image_path, media_type=media_type)
