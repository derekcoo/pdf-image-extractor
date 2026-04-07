from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

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
app = FastAPI(title="PDF Image Extractor")
extractor = PDFImageExtractor()

SUPPORTED_LANGUAGES = ("zh", "en")

TRANSLATIONS: dict[str, dict[str, Any]] = {
    "zh": {
        "html_lang": "zh-CN",
        "page_title": "PDF 图片提取工具",
        "brand_name": "Pic Extractor",
        "brand_subtitle": "文档图片提取工具",
        "language_switch_aria": "语言切换",
        "language_names": {"zh": "中文", "en": "EN"},
        "masthead_note": "为文档整理、内容归档与版面审校准备的图片提取工作台。",
        "editorial": {
            "eyebrow": "上传 PDF",
            "hero_title": "把 PDF 里的图片，拆回它们该有的样子。",
            "lede": "一个为文档工作流设计的单页工具。上传 PDF 后，系统会优先提取内嵌原图，必要时再按页面区域补齐裁切结果，让每一张图片都能独立归档、复核与再利用。",
            "edition_chips": [
                {"label": "版本", "value": "单文件工作流"},
                {"label": "输出", "value": "PNG + ZIP 打包"},
                {"label": "方法", "value": "内嵌优先，页面补齐"},
            ],
            "notes": [
                {
                    "title": "可靠提取",
                    "body": "优先走 PDF 内嵌图片对象，避免无谓失真；遇到特殊页面时，再用页面区域裁切补足结果。",
                },
                {
                    "title": "适合审校",
                    "body": "每张图片都会单独编号输出，方便你比对页码、素材顺序与版面构成，不需要手工截图。",
                },
            ],
            "process": {
                "aria_label": "处理流程说明",
                "title": "工作方式",
                "steps": [
                    "上传一个未加密 PDF，系统先检查文件体积与页数是否在当前处理范围内。",
                    "优先提取内嵌图片，再对页面中的图片块做补充裁切，统一输出为 PNG。",
                    "提取结果自动打包为 ZIP 下载，并以通知弹窗确认本次导出情况。",
                ],
            },
        },
        "workbench": {
            "eyebrow": "工作台",
            "title": "上传工作区",
            "intro": "拖入一个 PDF，或点击选择。页面会持续显示上传与处理进度，完成后自动开始下载。",
            "dropzone_title": "拖入 PDF 到这里",
            "dropzone_hint": "也可以点击选择。仅支持单个未加密 PDF，上传后会自动提取并打包下载。",
            "file_picker_button": "选择文件",
            "file_picker_empty": "未选择文件",
            "badges": ["单个 PDF", "PNG / ZIP"],
            "current_file_title": "当前任务",
            "empty_file_title": "尚未选择 PDF",
            "empty_file_meta": "选择一个 PDF 后，这里会显示文件信息。",
            "progress_title": "状态进度",
            "progress_wait": "等待上传",
            "processing_title": "图片提取中",
            "processing_body": "上传完成后会继续自动提取图片，并整理成 ZIP 供下载。",
            "processing_note": "复杂 PDF 可能需要多一点时间，请保持当前页面打开。",
            "meta_file_size": "最大文件大小",
            "meta_pages": "最大页数",
            "meta_pages_unit": "页",
            "error_title": "暂时无法处理这个文件",
            "error_body": "请检查文件是否为标准 PDF，然后重新上传。",
            "error_hint": "如果问题持续出现，可以尝试换一个 PDF 样本验证。",
            "submit": "开始提取",
        },
        "result_modal": {
            "kicker": "提取完成",
            "meta": "结果摘要",
            "title": "提取结果通知",
            "body": "ZIP 已生成并开始下载，下面是本次提取结果。",
            "status_label": "状态",
            "status_value": "提取完成",
            "image_count_label": "导出张数",
            "zip_name_label": "ZIP 文件名",
            "note": "点击确认后，页面会自动刷新，方便开始下一次提取。",
            "confirm": "确认并刷新",
            "image_count_unit": "张",
        },
        "ui": {
            "stages": {
                "wait_upload": "等待上传",
                "prepare_upload": "准备上传",
                "uploading": "正在上传",
                "prepare_download": "准备下载",
                "server_processing": "服务器处理中",
                "processing_percent": "处理中",
            },
            "status_messages": {
                "file_ready": "文件已就绪，可以开始提取。",
                "select_pdf": "请先选择一个 PDF 文件。",
                "uploading": "正在上传文件，请稍候...",
                "uploaded_processing": "文件已上传完成，正在提取图片...",
                "completed": "提取完成，ZIP 已开始下载。",
                "failed": "提取失败，请稍后重试。",
                "network_failed": "网络异常，上传失败，请稍后重试。",
            },
            "errors": {
                "missing_file": {
                    "title": "还没有选择文件",
                    "body": "请先选择或拖入一个 PDF 文件。",
                    "hint": "选择完成后，再点击“开始提取”。",
                },
                "invalid_pdf": {
                    "title": "文件格式有误",
                    "body": "当前上传内容不是可处理的 PDF 文件。",
                    "hint": "请确认文件扩展名和实际内容一致，并重新上传标准 PDF。",
                },
                "password_protected": {
                    "title": "这个 PDF 受到保护",
                    "body": "当前文件带有密码保护，暂时不支持直接提取。",
                    "hint": "请先移除密码保护后再重新上传。",
                },
                "file_too_large": {
                    "title": "文件超出当前处理范围",
                    "body": "文件大小超过了当前服务限制。",
                    "hint": "可以先压缩 PDF，或拆分为更小的文件后再试。",
                },
                "page_limit": {
                    "title": "文件超出当前处理范围",
                    "body": "文件页数超过了当前服务限制。",
                    "hint": "可以先拆分 PDF，再分别上传处理。",
                },
                "no_images": {
                    "title": "没有检测到可提取图片",
                    "body": "这个 PDF 里可能只有文字或矢量内容。",
                    "hint": "你可以换一个含有位图图片的 PDF 样本再验证。",
                },
                "unexpected": {
                    "title": "提取失败",
                    "body": "服务端在提取图片时遇到了异常。",
                    "hint": "请稍后重试；如果持续失败，建议先用更小的 PDF 进行排查。",
                },
                "network": {
                    "title": "网络连接异常",
                    "body": "文件上传过程中网络连接中断，当前请求没有成功发送到服务器。",
                    "hint": "请检查网络后重新上传，或刷新页面再试一次。",
                },
            },
            "result": {
                "title": "提取结果通知",
                "body": "ZIP 已生成并开始下载，下面是本次提取结果。",
                "status": "提取完成",
                "note": "点击确认后，页面会自动刷新，方便开始下一次提取。",
            },
        },
    },
    "en": {
        "html_lang": "en",
        "page_title": "PDF Image Extractor",
        "brand_name": "Pic Extractor",
        "brand_subtitle": "Editorial document utility",
        "language_switch_aria": "Language switcher",
        "language_names": {"zh": "中文", "en": "EN"},
        "masthead_note": "An image extraction workbench for document cleanup, archiving, and editorial review.",
        "editorial": {
            "eyebrow": "Extract images from PDF",
            "hero_title": "Pull the images out of your PDF and back into working shape.",
            "lede": "A single-page tool built for document workflows. Upload a PDF and the system will extract embedded images first, then fill the gaps with page-region crops so every image is ready for archiving, review, and reuse.",
            "edition_chips": [
                {"label": "Edition", "value": "Single-file workflow"},
                {"label": "Output", "value": "PNG + ZIP packaging"},
                {"label": "Method", "value": "Embedded first, page fallback"},
            ],
            "notes": [
                {
                    "title": "Reliable extraction",
                    "body": "Extract embedded PDF image objects first to avoid unnecessary quality loss, then use page-region crops only when needed.",
                },
                {
                    "title": "Ready for review",
                    "body": "Every image is exported with an explicit sequence so you can verify page order, asset placement, and layout composition without taking manual screenshots.",
                },
            ],
            "process": {
                "aria_label": "How the extraction works",
                "title": "How it works",
                "steps": [
                    "Upload one unencrypted PDF and the system will first check whether the file size and page count are within the supported range.",
                    "Extract embedded images first, then add page-level fallback crops for image blocks and export everything as PNG files.",
                    "Package the extracted files into a ZIP download and confirm the result with a summary dialog.",
                ],
            },
        },
        "workbench": {
            "eyebrow": "Workbench",
            "title": "Upload workspace",
            "intro": "Drop in a PDF or choose a file. The page will keep upload and processing states visible, then start the ZIP download automatically when it is ready.",
            "dropzone_title": "Drop a PDF here",
            "dropzone_hint": "You can also click to choose a file. Only one unencrypted PDF is supported at a time, and extraction starts automatically after upload.",
            "file_picker_button": "Choose file",
            "file_picker_empty": "No file selected",
            "badges": ["Single PDF", "PNG / ZIP"],
            "current_file_title": "Current file",
            "empty_file_title": "No PDF selected yet",
            "empty_file_meta": "Choose a PDF and the file details will appear here.",
            "progress_title": "Progress",
            "progress_wait": "Wait for upload",
            "processing_title": "Image extraction in progress",
            "processing_body": "After upload completes, the server will keep extracting images and bundle them into a ZIP archive for download.",
            "processing_note": "Complex PDFs can take a little longer. Keep this page open while processing finishes.",
            "meta_file_size": "Max file size",
            "meta_pages": "Max pages",
            "meta_pages_unit": "pages",
            "error_title": "This file cannot be processed right now",
            "error_body": "Please check whether the file is a standard PDF and try uploading it again.",
            "error_hint": "If the issue keeps happening, try another PDF sample to narrow it down.",
            "submit": "Start extraction",
        },
        "result_modal": {
            "kicker": "Extraction complete",
            "meta": "Results summary",
            "title": "Extraction results",
            "body": "The ZIP archive is ready and the download has started. Here is the summary for this run.",
            "status_label": "Status",
            "status_value": "Completed",
            "image_count_label": "Images exported",
            "zip_name_label": "ZIP file name",
            "note": "Click confirm to refresh the page and start another extraction.",
            "confirm": "Confirm and refresh",
            "image_count_unit": "images",
        },
        "ui": {
            "stages": {
                "wait_upload": "Wait for upload",
                "prepare_upload": "Preparing upload",
                "uploading": "Uploading",
                "prepare_download": "Preparing download",
                "server_processing": "Server processing",
                "processing_percent": "Processing",
            },
            "status_messages": {
                "file_ready": "The file is ready. Start extraction when you are ready.",
                "select_pdf": "Choose a PDF file first.",
                "uploading": "Uploading the file. Please wait...",
                "uploaded_processing": "Upload complete. The server is now extracting images...",
                "completed": "Extraction complete. The ZIP download has started.",
                "failed": "Extraction failed. Please try again in a moment.",
                "network_failed": "Network error. Upload failed, please try again.",
            },
            "errors": {
                "missing_file": {
                    "title": "No file selected yet",
                    "body": "Choose or drop a PDF file first.",
                    "hint": "Once the file is ready, click “Start extraction”.",
                },
                "invalid_pdf": {
                    "title": "Invalid file format",
                    "body": "The uploaded content is not a supported PDF file.",
                    "hint": "Make sure the extension matches the real file content and upload a standard PDF again.",
                },
                "password_protected": {
                    "title": "This PDF is protected",
                    "body": "Password-protected files are not supported for extraction yet.",
                    "hint": "Remove the password protection first, then upload the PDF again.",
                },
                "file_too_large": {
                    "title": "The file is outside the supported range",
                    "body": "The file size exceeds the current service limit.",
                    "hint": "Try compressing the PDF or splitting it into smaller files first.",
                },
                "page_limit": {
                    "title": "The file is outside the supported range",
                    "body": "The page count exceeds the current service limit.",
                    "hint": "Split the PDF into smaller parts and upload them separately.",
                },
                "no_images": {
                    "title": "No extractable images found",
                    "body": "This PDF may contain only text or vector content.",
                    "hint": "Try another sample PDF that contains bitmap images.",
                },
                "unexpected": {
                    "title": "Extraction failed",
                    "body": "The server ran into an unexpected problem while extracting images.",
                    "hint": "Try again later. If it keeps failing, retry with a smaller PDF to investigate further.",
                },
                "network": {
                    "title": "Network connection issue",
                    "body": "The upload was interrupted before the request could complete.",
                    "hint": "Check your connection, then upload again or refresh the page.",
                },
            },
            "result": {
                "title": "Extraction results",
                "body": "The ZIP archive is ready and the download has started. Here is the summary for this run.",
                "status": "Completed",
                "note": "Click confirm to refresh the page and start another extraction.",
            },
        },
    },
}


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


def resolve_language(request: Request) -> str:
    lang_override = request.query_params.get("lang", "").lower()
    if lang_override in SUPPORTED_LANGUAGES:
        return lang_override

    accept_language = request.headers.get("accept-language", "")
    for raw_part in accept_language.split(","):
        language = raw_part.split(";")[0].strip().lower()
        if language.startswith("zh"):
            return "zh"
        if language.startswith("en"):
            return "en"
    return "en"


def build_language_link(request: Request, language: str) -> str:
    query_items = [(key, value) for key, value in request.query_params.multi_items() if key != "lang"]
    query_items.append(("lang", language))
    query_string = urlencode(query_items)
    return f"{request.url.path}?{query_string}" if query_string else request.url.path


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    language = resolve_language(request)
    translations = TRANSLATIONS[language]
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "lang": language,
            "t": translations,
            "language_links": {
                "zh": build_language_link(request, "zh"),
                "en": build_language_link(request, "en"),
            },
            "ui_text": translations["ui"],
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
