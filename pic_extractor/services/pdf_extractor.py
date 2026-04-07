from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass

import fitz
from PIL import Image


DEFAULT_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_PAGES = 200
DEFAULT_RENDER_SCALE = 2.0


class PDFExtractionError(Exception):
    """Base error for extraction failures."""


class InvalidPDFError(PDFExtractionError):
    """Raised when uploaded bytes are not a valid PDF."""


class FileTooLargeError(PDFExtractionError):
    """Raised when the uploaded PDF exceeds the configured size limit."""


class PageLimitExceededError(PDFExtractionError):
    """Raised when the uploaded PDF exceeds the configured page limit."""


class NoImagesFoundError(PDFExtractionError):
    """Raised when no images can be extracted from a PDF."""


@dataclass(frozen=True)
class ExtractedImage:
    filename: str
    content: bytes


@dataclass(frozen=True)
class _ImageOccurrence:
    rect: fitz.Rect
    content: bytes


class PDFImageExtractor:
    def __init__(
        self,
        *,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        max_pages: int = DEFAULT_MAX_PAGES,
        render_scale: float = DEFAULT_RENDER_SCALE,
    ) -> None:
        self.max_file_size_bytes = max_file_size_bytes
        self.max_pages = max_pages
        self.render_scale = render_scale

    def extract_images(self, pdf_bytes: bytes) -> list[ExtractedImage]:
        self._validate_file_size(pdf_bytes)
        document = self._open_document(pdf_bytes)
        try:
            self._validate_page_count(document)
            extracted_images: list[ExtractedImage] = []
            for page_index in range(document.page_count):
                page = document.load_page(page_index)
                occurrences = self._collect_page_occurrences(document, page)
                for image_index, occurrence in enumerate(occurrences, start=1):
                    extracted_images.append(
                        ExtractedImage(
                            filename=f"page-{page_index + 1:03d}-image-{image_index:02d}.png",
                            content=occurrence.content,
                        )
                    )
        finally:
            document.close()

        if not extracted_images:
            raise NoImagesFoundError("No extractable images were found in the PDF.")
        return extracted_images

    def build_zip(self, pdf_bytes: bytes) -> bytes:
        extracted_images = self.extract_images(pdf_bytes)
        archive_buffer = io.BytesIO()
        with zipfile.ZipFile(archive_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for image in extracted_images:
                archive.writestr(image.filename, image.content)
        return archive_buffer.getvalue()

    def _validate_file_size(self, pdf_bytes: bytes) -> None:
        if len(pdf_bytes) > self.max_file_size_bytes:
            raise FileTooLargeError("Uploaded PDF exceeds the maximum allowed file size.")

    def _open_document(self, pdf_bytes: bytes) -> fitz.Document:
        try:
            document = fitz.open(stream=pdf_bytes, filetype="pdf")
        except (RuntimeError, ValueError) as exc:
            raise InvalidPDFError("Uploaded file is not a valid PDF.") from exc

        if document.needs_pass:
            document.close()
            raise InvalidPDFError("Password-protected PDFs are not supported.")
        return document

    def _validate_page_count(self, document: fitz.Document) -> None:
        if document.page_count > self.max_pages:
            raise PageLimitExceededError("Uploaded PDF exceeds the maximum allowed page count.")

    def _collect_page_occurrences(
        self,
        document: fitz.Document,
        page: fitz.Page,
    ) -> list[_ImageOccurrence]:
        embedded_occurrences = self._extract_embedded_occurrences(document, page)
        fallback_occurrences = self._extract_rendered_occurrences(
            page,
            occupied_rects=[occurrence.rect for occurrence in embedded_occurrences],
        )
        occurrences = embedded_occurrences + fallback_occurrences
        occurrences.sort(key=lambda occurrence: (round(occurrence.rect.y0, 3), round(occurrence.rect.x0, 3)))
        return occurrences

    def _extract_embedded_occurrences(
        self,
        document: fitz.Document,
        page: fitz.Page,
    ) -> list[_ImageOccurrence]:
        occurrences: list[_ImageOccurrence] = []
        seen_xrefs: set[int] = set()
        for image_info in page.get_images(full=True):
            xref = image_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            rects = page.get_image_rects(xref, transform=False)
            content = self._extract_embedded_png(document, xref)
            for rect in rects:
                occurrences.append(_ImageOccurrence(rect=fitz.Rect(rect), content=content))
        return occurrences

    def _extract_embedded_png(self, document: fitz.Document, xref: int) -> bytes:
        extracted = document.extract_image(xref)
        image_bytes = extracted.get("image")
        if image_bytes:
            try:
                return self._to_png_bytes(image_bytes)
            except OSError:
                pass

        pixmap = fitz.Pixmap(document, xref)
        try:
            if pixmap.alpha:
                return pixmap.tobytes("png")
            if pixmap.colorspace is not None and pixmap.colorspace.n > 3:
                rgb_pixmap = fitz.Pixmap(fitz.csRGB, pixmap)
                try:
                    return rgb_pixmap.tobytes("png")
                finally:
                    rgb_pixmap = None
            return pixmap.tobytes("png")
        finally:
            pixmap = None

    def _extract_rendered_occurrences(
        self,
        page: fitz.Page,
        *,
        occupied_rects: list[fitz.Rect],
    ) -> list[_ImageOccurrence]:
        occurrences: list[_ImageOccurrence] = []
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 1:
                continue
            rect = fitz.Rect(block["bbox"])
            if self._matches_existing_rect(rect, occupied_rects):
                continue
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(self.render_scale, self.render_scale),
                clip=rect,
                alpha=False,
            )
            occurrences.append(_ImageOccurrence(rect=rect, content=pixmap.tobytes("png")))
        return occurrences

    @staticmethod
    def _matches_existing_rect(candidate: fitz.Rect, existing_rects: list[fitz.Rect], tolerance: float = 0.5) -> bool:
        for existing in existing_rects:
            if (
                abs(candidate.x0 - existing.x0) <= tolerance
                and abs(candidate.y0 - existing.y0) <= tolerance
                and abs(candidate.x1 - existing.x1) <= tolerance
                and abs(candidate.y1 - existing.y1) <= tolerance
            ):
                return True
        return False

    @staticmethod
    def _to_png_bytes(image_bytes: bytes) -> bytes:
        with Image.open(io.BytesIO(image_bytes)) as image:
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            output = io.BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()
