from __future__ import annotations

import io

import fitz
import pytest
from PIL import Image


def make_png_bytes(color: str, size: tuple[int, int] = (80, 60)) -> bytes:
    image = Image.new("RGB", size, color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def make_pdf_with_images(page_specs: list[list[dict]]) -> bytes:
    document = fitz.open()
    for page_spec in page_specs:
        page = document.new_page()
        for item in page_spec:
            page.insert_image(fitz.Rect(item["rect"]), stream=item["image_bytes"])
    return document.tobytes()


@pytest.fixture
def red_png() -> bytes:
    return make_png_bytes("red")


@pytest.fixture
def blue_png() -> bytes:
    return make_png_bytes("blue")
