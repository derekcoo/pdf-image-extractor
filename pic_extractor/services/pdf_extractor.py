from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass

import fitz
from PIL import Image


DEFAULT_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_PAGES = 200
DEFAULT_RENDER_SCALE = 2.0
BACKGROUND_THRESHOLD = 245
WHOLE_PAGE_MIN_AXIS_COVERAGE = 0.95
WHOLE_PAGE_MIN_AREA_RATIO = 0.3
MIN_PANEL_EDGE_PIXELS = 40
MIN_PANEL_AREA_RATIO = 0.03
MIN_GAP_PIXELS = 16
MAX_PANEL_COUNT = 12
MIN_TOTAL_PANEL_COVERAGE_RATIO = 0.4


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
        occurrences = self._split_large_occurrences(page, embedded_occurrences + fallback_occurrences)
        occurrences.sort(key=lambda occurrence: (round(occurrence.rect.y0, 3), round(occurrence.rect.x0, 3)))
        return occurrences

    def _split_large_occurrences(
        self,
        page: fitz.Page,
        occurrences: list[_ImageOccurrence],
    ) -> list[_ImageOccurrence]:
        split_occurrences: list[_ImageOccurrence] = []
        for occurrence in occurrences:
            split_result = self._split_large_occurrence(page, occurrence)
            if split_result is None:
                split_occurrences.append(occurrence)
                continue
            split_occurrences.extend(split_result)
        return split_occurrences

    def _split_large_occurrence(
        self,
        page: fitz.Page,
        occurrence: _ImageOccurrence,
    ) -> list[_ImageOccurrence] | None:
        if not self._looks_like_large_occurrence(page, occurrence):
            return None

        occurrence_image = self._open_occurrence_image(occurrence)
        if occurrence_image is None:
            return None

        panel_boxes = self._detect_panel_boxes(occurrence_image)
        if len(panel_boxes) < 2 or len(panel_boxes) > MAX_PANEL_COUNT:
            return None

        total_panel_area = sum((right - left) * (bottom - top) for left, top, right, bottom in panel_boxes)
        image_area = max(occurrence_image.width * occurrence_image.height, 1)
        if total_panel_area / image_area < MIN_TOTAL_PANEL_COVERAGE_RATIO:
            return None

        image_width = max(occurrence_image.width, 1)
        image_height = max(occurrence_image.height, 1)
        split_occurrences: list[_ImageOccurrence] = []
        for left, top, right, bottom in panel_boxes:
            crop = occurrence_image.crop((left, top, right, bottom))
            occurrence_crop_rect = fitz.Rect(
                occurrence.rect.x0 + (left / image_width) * occurrence.rect.width,
                occurrence.rect.y0 + (top / image_height) * occurrence.rect.height,
                occurrence.rect.x0 + (right / image_width) * occurrence.rect.width,
                occurrence.rect.y0 + (bottom / image_height) * occurrence.rect.height,
            )
            split_occurrences.append(
                _ImageOccurrence(
                    rect=occurrence_crop_rect,
                    content=self._image_to_png_bytes(crop),
                )
            )

        return split_occurrences

    def _looks_like_large_occurrence(self, page: fitz.Page, occurrence: _ImageOccurrence) -> bool:
        page_rect = page.rect
        width_ratio = occurrence.rect.width / max(page_rect.width, 1)
        height_ratio = occurrence.rect.height / max(page_rect.height, 1)
        occurrence_area = max(occurrence.rect.width * occurrence.rect.height, 0)
        page_area = max(page_rect.width * page_rect.height, 1)
        if max(width_ratio, height_ratio) < WHOLE_PAGE_MIN_AXIS_COVERAGE:
            return False
        if occurrence_area / page_area < WHOLE_PAGE_MIN_AREA_RATIO:
            return False
        return True

    def _open_occurrence_image(self, occurrence: _ImageOccurrence) -> Image.Image | None:
        try:
            return Image.open(io.BytesIO(occurrence.content)).convert("RGB")
        except OSError:
            return None

    def _detect_panel_boxes(self, image: Image.Image) -> list[tuple[int, int, int, int]]:
        grayscale = image.convert("L")
        root_box = self._trim_foreground_box(grayscale, (0, 0, grayscale.width, grayscale.height))
        if root_box is None:
            return []

        panel_boxes = self._split_box_by_whitespace(grayscale, root_box)
        panel_boxes.sort(key=lambda box: (box[1], box[0]))
        return panel_boxes

    def _split_box_by_whitespace(
        self,
        grayscale: Image.Image,
        box: tuple[int, int, int, int],
    ) -> list[tuple[int, int, int, int]]:
        trimmed_box = self._trim_foreground_box(grayscale, box)
        if trimmed_box is None:
            return []
        if not self._is_viable_panel_box(grayscale, trimmed_box):
            return []

        split_result = self._find_split_box(grayscale, trimmed_box)
        if split_result is None:
            return [trimmed_box]

        first_box, second_box = split_result
        return self._split_box_by_whitespace(grayscale, first_box) + self._split_box_by_whitespace(grayscale, second_box)

    def _find_split_box(
        self,
        grayscale: Image.Image,
        box: tuple[int, int, int, int],
    ) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]] | None:
        vertical_split = self._find_axis_split(grayscale, box, axis="x")
        horizontal_split = self._find_axis_split(grayscale, box, axis="y")
        if vertical_split is None and horizontal_split is None:
            return None
        if horizontal_split is None:
            return vertical_split["boxes"]
        if vertical_split is None:
            return horizontal_split["boxes"]

        return vertical_split["boxes"] if vertical_split["gap_size"] >= horizontal_split["gap_size"] else horizontal_split["boxes"]

    def _find_axis_split(
        self,
        grayscale: Image.Image,
        box: tuple[int, int, int, int],
        *,
        axis: str,
    ) -> dict[str, object] | None:
        left, top, right, bottom = box
        length = right - left if axis == "x" else bottom - top

        if length < MIN_PANEL_EDGE_PIXELS * 2:
            return None

        current_gap_start: int | None = None
        best_gap_start: int | None = None
        best_gap_end: int | None = None
        longest_gap = 0

        for index in range(length):
            position = left + index if axis == "x" else top + index
            has_foreground = self._axis_has_foreground(grayscale, box, axis=axis, position=position)
            if not has_foreground:
                if current_gap_start is None:
                    current_gap_start = position
                continue

            if current_gap_start is not None:
                gap_size = position - current_gap_start
                if gap_size >= MIN_GAP_PIXELS and gap_size > longest_gap:
                    longest_gap = gap_size
                    best_gap_start = current_gap_start
                    best_gap_end = position
                current_gap_start = None

        if current_gap_start is not None:
            gap_size = (right if axis == "x" else bottom) - current_gap_start
            if gap_size >= MIN_GAP_PIXELS and gap_size > longest_gap:
                longest_gap = gap_size
                best_gap_start = current_gap_start
                best_gap_end = right if axis == "x" else bottom

        if best_gap_start is None or best_gap_end is None or longest_gap < MIN_GAP_PIXELS:
            return None

        if axis == "x":
            first = (left, top, best_gap_start, bottom)
            second = (best_gap_end, top, right, bottom)
        else:
            first = (left, top, right, best_gap_start)
            second = (left, best_gap_end, right, bottom)
        return {"boxes": (first, second), "gap_size": longest_gap}

    def _axis_has_foreground(
        self,
        grayscale: Image.Image,
        box: tuple[int, int, int, int],
        *,
        axis: str,
        position: int,
    ) -> bool:
        pixels = grayscale.load()
        left, top, right, bottom = box
        if axis == "x":
            return any(pixels[position, y] < BACKGROUND_THRESHOLD for y in range(top, bottom))
        return any(pixels[x, position] < BACKGROUND_THRESHOLD for x in range(left, right))

    def _trim_foreground_box(
        self,
        grayscale: Image.Image,
        box: tuple[int, int, int, int],
    ) -> tuple[int, int, int, int] | None:
        left, top, right, bottom = box
        pixels = grayscale.load()

        while left < right and not any(pixels[left, y] < BACKGROUND_THRESHOLD for y in range(top, bottom)):
            left += 1
        while right > left and not any(pixels[right - 1, y] < BACKGROUND_THRESHOLD for y in range(top, bottom)):
            right -= 1
        while top < bottom and not any(pixels[x, top] < BACKGROUND_THRESHOLD for x in range(left, right)):
            top += 1
        while bottom > top and not any(pixels[x, bottom - 1] < BACKGROUND_THRESHOLD for x in range(left, right)):
            bottom -= 1

        if left >= right or top >= bottom:
            return None
        return left, top, right, bottom

    def _is_viable_panel_box(self, grayscale: Image.Image, box: tuple[int, int, int, int]) -> bool:
        left, top, right, bottom = box
        width = right - left
        height = bottom - top
        if width < MIN_PANEL_EDGE_PIXELS or height < MIN_PANEL_EDGE_PIXELS:
            return False

        page_area = max(grayscale.width * grayscale.height, 1)
        box_area = width * height
        if box_area / page_area < MIN_PANEL_AREA_RATIO:
            return False
        return True

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
            return PDFImageExtractor._image_to_png_bytes(image)

    @staticmethod
    def _image_to_png_bytes(image: Image.Image) -> bytes:
        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()
