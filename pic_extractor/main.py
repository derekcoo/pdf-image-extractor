from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from pic_extractor.services.pdf_extractor import (
    FileTooLargeError,
    InvalidPDFError,
    NoImagesFoundError,
    PDFExtractionError,
    PDFImageExtractor,
    PageLimitExceededError,
)


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app = FastAPI(title="PDF 图片提取工具")
extractor = PDFImageExtractor()


def build_download_filename(base_name: str) -> tuple[str, str]:
    filename = f"{base_name}-images.zip"
    ascii_base = "".join(char for char in base_name if char.isascii() and char not in {'"', "\\"}).strip()
    if not any(char.isalnum() for char in ascii_base):
        ascii_filename = "download-images.zip"
    else:
        ascii_filename = f"{ascii_base}-images.zip"
    return filename, ascii_filename


def build_content_disposition(filename: str, ascii_filename: str) -> str:
    quoted_filename = quote(filename, safe="")
    return f"""attachment; filename="{ascii_filename}"; filename*=utf-8''{quoted_filename}"""


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "max_file_size_mb": extractor.max_file_size_bytes // (1024 * 1024),
            "max_pages": extractor.max_pages,
        },
    )


@app.post("/api/extract-images")
async def extract_images(file: UploadFile = File(...)) -> Response:
    pdf_bytes = await file.read()
    try:
        archive_bytes = extractor.build_zip(pdf_bytes)
    except InvalidPDFError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except PageLimitExceededError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except NoImagesFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PDFExtractionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Unexpected extraction failure.") from exc

    base_name = Path(file.filename or "extracted").stem
    filename, ascii_filename = build_download_filename(base_name)
    headers = {
        "Content-Disposition": build_content_disposition(filename, ascii_filename),
    }
    return Response(content=archive_bytes, media_type="application/zip", headers=headers)
