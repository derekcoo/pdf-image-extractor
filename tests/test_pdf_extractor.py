from __future__ import annotations

import io
import zipfile

import fitz
import pytest
from PIL import Image

from pic_extractor.services.pdf_extractor import (
    FileTooLargeError,
    InvalidPDFError,
    NoImagesFoundError,
    PageLimitExceededError,
    PDFImageExtractor,
)


def test_extracts_multiple_images_from_single_page(red_png: bytes, blue_png: bytes) -> None:
    pdf_bytes = fitz.open()
    page = pdf_bytes.new_page()
    page.insert_image(fitz.Rect(20, 20, 140, 100), stream=red_png)
    page.insert_image(fitz.Rect(180, 40, 300, 120), stream=blue_png)

    extractor = PDFImageExtractor()

    images = extractor.extract_images(pdf_bytes.tobytes())

    assert [image.filename for image in images] == [
        "page-001-image-01.png",
        "page-001-image-02.png",
    ]
    assert len(images) == 2
    for image in images:
        extracted = Image.open(io.BytesIO(image.content))
        assert extracted.format == "PNG"


def test_extracts_each_image_occurrence_without_deduping(red_png: bytes) -> None:
    document = fitz.open()
    page_one = document.new_page()
    page_one.insert_image(fitz.Rect(20, 20, 140, 100), stream=red_png)
    page_one.insert_image(fitz.Rect(160, 20, 280, 100), stream=red_png)
    page_two = document.new_page()
    page_two.insert_image(fitz.Rect(30, 30, 150, 110), stream=red_png)

    extractor = PDFImageExtractor()

    images = extractor.extract_images(document.tobytes())

    assert [image.filename for image in images] == [
        "page-001-image-01.png",
        "page-001-image-02.png",
        "page-002-image-01.png",
    ]


def test_splits_flattened_multi_panel_page_into_multiple_images(flattened_two_panel_pdf: bytes) -> None:
    extractor = PDFImageExtractor()

    images = extractor.extract_images(flattened_two_panel_pdf)

    assert [image.filename for image in images] == [
        "page-001-image-01.png",
        "page-001-image-02.png",
    ]


def test_keeps_single_legitimate_page_image_as_one_output(single_full_page_pdf: bytes) -> None:
    extractor = PDFImageExtractor()

    images = extractor.extract_images(single_full_page_pdf)

    assert [image.filename for image in images] == ["page-001-image-01.png"]


def test_ignores_tiny_noise_regions_when_splitting(flattened_page_with_small_marks_pdf: bytes) -> None:
    extractor = PDFImageExtractor()

    images = extractor.extract_images(flattened_page_with_small_marks_pdf)

    assert [image.filename for image in images] == [
        "page-001-image-01.png",
        "page-001-image-02.png",
    ]


def test_splits_large_flattened_occurrence_even_with_small_decor(
    flattened_large_occurrence_with_small_decor_pdf: bytes,
) -> None:
    extractor = PDFImageExtractor()

    images = extractor.extract_images(flattened_large_occurrence_with_small_decor_pdf)

    assert [image.filename for image in images] == [
        "page-001-image-01.png",
        "page-001-image-02.png",
        "page-001-image-03.png",
    ]


def test_rejects_invalid_pdf_bytes() -> None:
    extractor = PDFImageExtractor()

    with pytest.raises(InvalidPDFError):
        extractor.extract_images(b"not-a-pdf")


def test_rejects_pdfs_without_images() -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "hello")
    extractor = PDFImageExtractor()

    with pytest.raises(NoImagesFoundError):
        extractor.extract_images(document.tobytes())


def test_rejects_files_larger_than_limit(red_png: bytes) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_image(fitz.Rect(20, 20, 140, 100), stream=red_png)
    pdf_bytes = document.tobytes()
    extractor = PDFImageExtractor(max_file_size_bytes=len(pdf_bytes) - 1)

    with pytest.raises(FileTooLargeError):
        extractor.extract_images(pdf_bytes)


def test_rejects_pdfs_that_exceed_page_limit() -> None:
    document = fitz.open()
    document.new_page()
    document.new_page()
    extractor = PDFImageExtractor(max_pages=1)

    with pytest.raises(PageLimitExceededError):
        extractor.extract_images(document.tobytes())


def test_builds_zip_with_png_files(red_png: bytes) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_image(fitz.Rect(20, 20, 140, 100), stream=red_png)
    extractor = PDFImageExtractor()

    zip_bytes = extractor.build_zip(document.tobytes())

    archive = zipfile.ZipFile(io.BytesIO(zip_bytes))
    assert archive.namelist() == ["page-001-image-01.png"]
