from __future__ import annotations

import io

import fitz
import pytest
from PIL import Image, ImageDraw


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


def make_flattened_panel_png(panel_colors: list[str], size: tuple[int, int] = (600, 320)) -> bytes:
    canvas = Image.new("RGB", size, color="white")
    panel_width = 220
    panel_height = 220
    top = 50
    left = 50
    gap = 60

    for index, color in enumerate(panel_colors):
        panel = Image.new("RGB", (panel_width, panel_height), color=color)
        x = left + index * (panel_width + gap)
        canvas.paste(panel, (x, top))

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    return buffer.getvalue()


def make_single_panel_png(color: str = "red", size: tuple[int, int] = (600, 320)) -> bytes:
    canvas = Image.new("RGB", size, color=color)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((150, 50, 450, 95), fill="white")
    draw.rectangle((150, 225, 450, 270), fill="white")

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    return buffer.getvalue()


def add_noise_marks(image_bytes: bytes) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as image:
        marked = image.convert("RGB")
        draw = ImageDraw.Draw(marked)
        draw.rectangle((18, 18, 28, 28), fill="black")
        draw.rectangle((560, 18, 570, 28), fill="black")

        buffer = io.BytesIO()
        marked.save(buffer, format="PNG")
        return buffer.getvalue()


@pytest.fixture
def red_png() -> bytes:
    return make_png_bytes("red")


@pytest.fixture
def blue_png() -> bytes:
    return make_png_bytes("blue")


@pytest.fixture
def flattened_two_panel_pdf() -> bytes:
    page_image = make_flattened_panel_png(["red", "blue"])
    return make_pdf_with_images(
        [
            [
                {
                    "rect": (0, 0, 595, 842),
                    "image_bytes": page_image,
                }
            ]
        ]
    )


@pytest.fixture
def single_full_page_pdf() -> bytes:
    page_image = make_single_panel_png()
    return make_pdf_with_images(
        [
            [
                {
                    "rect": (0, 0, 595, 842),
                    "image_bytes": page_image,
                }
            ]
        ]
    )


@pytest.fixture
def flattened_page_with_small_marks_pdf() -> bytes:
    page_image = add_noise_marks(make_flattened_panel_png(["red", "blue"]))
    return make_pdf_with_images(
        [
            [
                {
                    "rect": (0, 0, 595, 842),
                    "image_bytes": page_image,
                }
            ]
        ]
    )
