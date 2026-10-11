"""
Image upload validation and processing.

Every upload is decoded with Pillow (so the content, not the extension, decides
the type), size- and pixel-limited, orientation-corrected, downscaled if very
large, and re-encoded — which strips EXIF/GPS metadata and any trailing payload.
"""

import io
import warnings
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image as PILImage
from PIL import ImageOps, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
ACCEPT_ATTR = "image/jpeg,image/png,image/webp"


@dataclass
class ProcessedImage:
    content: ContentFile
    extension: str
    width: int
    height: int
    size: int


def process_upload(uploaded_file):
    max_bytes = settings.IMAGE_MAX_UPLOAD_BYTES
    if uploaded_file.size > max_bytes:
        raise ValidationError(
            f"Images must be {max_bytes // (1024 * 1024)} MB or smaller "
            f"(this file is {uploaded_file.size / (1024 * 1024):.1f} MB).",
            code="too_large",
        )

    raw = uploaded_file.read()
    PILImage.MAX_IMAGE_PIXELS = settings.IMAGE_MAX_PIXELS
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", PILImage.DecompressionBombWarning)
            probe = PILImage.open(io.BytesIO(raw))
            image_format = probe.format
            probe.verify()
            image = PILImage.open(io.BytesIO(raw))
            image.load()
    except (PILImage.DecompressionBombError, PILImage.DecompressionBombWarning):
        raise ValidationError("This image has too many pixels.", code="too_many_pixels") from None
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise ValidationError(
            "This file isn't a valid image. Upload a JPEG, PNG or WebP file.", code="invalid"
        ) from None

    if image_format not in ALLOWED_FORMATS:
        raise ValidationError(
            "Unsupported image type. Upload a JPEG, PNG or WebP file.", code="unsupported"
        )

    image = ImageOps.exif_transpose(image)
    limit = settings.IMAGE_MAX_DIMENSION
    if image.width > limit or image.height > limit:
        image.thumbnail((limit, limit), PILImage.Resampling.LANCZOS)

    output = io.BytesIO()
    if image_format == "JPEG":
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(output, "JPEG", quality=85, optimize=True, progressive=True)
    elif image_format == "PNG":
        if image.mode not in ("RGB", "RGBA", "L", "LA", "P"):
            image = image.convert("RGBA")
        image.save(output, "PNG", optimize=True)
    else:
        image.save(output, "WEBP", quality=85, method=4)

    data = output.getvalue()
    return ProcessedImage(
        content=ContentFile(data),
        extension=ALLOWED_FORMATS[image_format],
        width=image.width,
        height=image.height,
        size=len(data),
    )


def create_image(uploaded_file, alt_text, user=None, is_demo=False, processed=None):
    from .models import Image

    processed = processed or process_upload(uploaded_file)
    image = Image(
        alt_text=alt_text.strip(),
        original_filename=(getattr(uploaded_file, "name", "") or "")[:255],
        uploaded_by=user if (user and user.is_authenticated) else None,
        file_size=processed.size,
        is_demo=is_demo,
    )
    image.file.save(f"upload.{processed.extension}", processed.content, save=False)
    image.width, image.height = processed.width, processed.height
    image.save()
    return image
