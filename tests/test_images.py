import io

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from PIL import Image as PILImage

from apps.images.models import Image
from apps.images.services import create_image, process_upload

from .conftest import image_bytes, upload

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("fmt, ext", [("JPEG", "jpg"), ("PNG", "png"), ("WEBP", "webp")])
def test_accepts_supported_formats(fmt, ext):
    result = process_upload(upload(f"a.{ext}", image_bytes(fmt)))
    assert result.extension == ext
    assert (result.width, result.height) == (64, 48)


def test_rejects_non_images_even_with_image_extension():
    with pytest.raises(ValidationError, match="isn't a valid image"):
        process_upload(upload("evil.jpg", b"<?php echo 'hi'; ?>"))


def test_rejects_svg():
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>'
    with pytest.raises(ValidationError):
        process_upload(upload("x.svg", svg, "image/svg+xml"))


def test_rejects_unsupported_real_image_format():
    with pytest.raises(ValidationError, match="Unsupported"):
        process_upload(upload("a.gif", image_bytes("GIF"), "image/gif"))


def test_rejects_oversized_files(settings):
    settings.IMAGE_MAX_UPLOAD_BYTES = 100
    with pytest.raises(ValidationError, match="MB or smaller"):
        process_upload(upload())


def test_rejects_decompression_bombs(settings):
    settings.IMAGE_MAX_PIXELS = 1000
    with pytest.raises(ValidationError, match="too many pixels"):
        process_upload(upload(content=image_bytes(size=(100, 100))))


def test_large_images_are_downscaled(settings):
    settings.IMAGE_MAX_DIMENSION = 50
    result = process_upload(upload(content=image_bytes(size=(200, 100))))
    assert (result.width, result.height) == (50, 25)


def test_exif_metadata_is_stripped():
    exif = PILImage.Exif()
    exif[0x010F] = "SecretCameraMaker"  # Make
    raw = image_bytes(exif=exif.tobytes())
    assert b"SecretCameraMaker" in raw
    result = process_upload(upload(content=raw))
    assert b"SecretCameraMaker" not in result.content.read()


def test_create_image_stores_file_with_random_name(editor):
    image = create_image(upload("my holiday.jpg"), "  A red square ", user=editor)
    assert image.alt_text == "A red square"
    assert image.width == 64 and image.height == 48
    assert "holiday" not in image.file.name
    assert image.file.name.endswith(".jpg")
    assert image.file.storage.exists(image.file.name)


def test_studio_upload_flow(editor_client):
    response = editor_client.post(
        reverse("studio:image_list"), {"file": upload(), "alt_text": "Square"}
    )
    assert response.status_code == 302
    assert Image.objects.get().alt_text == "Square"


def test_studio_upload_shows_validation_error(editor_client):
    response = editor_client.post(
        reverse("studio:image_list"),
        {"file": upload("x.png", b"not an image", "image/png"), "alt_text": "x"},
    )
    assert response.status_code == 400
    assert "isn" in response.content.decode() and "valid image" in response.content.decode()
    assert not Image.objects.exists()


def test_studio_upload_requires_alt_text(editor_client):
    response = editor_client.post(reverse("studio:image_list"), {"file": upload(), "alt_text": ""})
    assert response.status_code == 400
    assert not Image.objects.exists()


def test_deleting_image_removes_file(editor_client, django_capture_on_commit_callbacks):
    image = create_image(upload(), "To delete")
    name, storage = image.file.name, image.file.storage
    with django_capture_on_commit_callbacks(execute=True):
        editor_client.post(reverse("studio:image_delete", args=[image.pk]))
    assert not Image.objects.exists()
    assert not storage.exists(name)


def test_image_bytes_helper_is_valid():
    PILImage.open(io.BytesIO(image_bytes())).verify()
