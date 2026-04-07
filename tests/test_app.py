from __future__ import annotations

import io
import zipfile

import fitz
from fastapi.testclient import TestClient

from pic_extractor.main import app


def test_index_page_renders_upload_form() -> None:
    client = TestClient(app)

    response = client.get("/", headers={"accept-language": "zh-CN,zh;q=0.9,en;q=0.8"})

    assert response.status_code == 200
    assert '<html lang="zh-CN">' in response.text
    assert "上传 PDF" in response.text
    assert 'type="file"' in response.text
    assert 'rel="icon"' in response.text
    assert "data:image/svg+xml" in response.text
    assert 'href="/?lang=zh"' in response.text
    assert 'href="/?lang=en"' in response.text
    assert 'id="dropzone"' in response.text
    assert 'id="workflow-panel"' in response.text
    assert 'id="selected-file"' in response.text
    assert "当前任务" in response.text
    assert "状态进度" in response.text
    assert 'id="upload-progress"' in response.text
    assert 'role="progressbar"' in response.text
    assert 'id="processing-card"' in response.text
    assert 'id="error-card"' in response.text
    assert 'id="error-card-title"' in response.text
    assert 'id="result-modal"' in response.text
    assert 'id="result-modal-image-count"' in response.text
    assert 'id="result-modal-zip-name"' in response.text
    assert 'id="result-modal-confirm"' in response.text
    assert 'event.key === "Escape"' in response.text
    assert 'resultModalBackdrop.addEventListener("click"' in response.text
    assert 'event.target === resultModalBackdrop' in response.text
    assert "@keyframes modalEnter" in response.text
    assert "@keyframes modalExit" in response.text
    assert 'setTimeout(() => {' in response.text
    assert "提取结果通知" in response.text
    assert "max-width: 16ch;" in response.text
    assert "font-size: clamp(3.2rem, 5vw, 3.6rem);" in response.text
    assert "上传完成后会继续自动提取图片" in response.text
    assert "拖入 PDF 到这里" in response.text
    assert "选择文件" in response.text
    assert "未选择文件" in response.text
    assert "单个 PDF" in response.text
    assert "PNG / ZIP" in response.text
    assert "开始提取" in response.text


def test_index_page_supports_english_via_lang_override() -> None:
    client = TestClient(app)

    response = client.get("/?lang=en", headers={"accept-language": "zh-CN,zh;q=0.9"})

    assert response.status_code == 200
    assert '<html lang="en">' in response.text
    assert 'href="/?lang=zh"' in response.text
    assert 'href="/?lang=en"' in response.text
    assert "Extract images from PDF" in response.text
    assert "Drop a PDF here" in response.text
    assert "Choose file" in response.text
    assert "No file selected" in response.text
    assert "Current file" in response.text
    assert "Progress" in response.text
    assert "No PDF selected yet" in response.text
    assert "Wait for upload" in response.text
    assert "Start extraction" in response.text
    assert "Image extraction in progress" in response.text
    assert "Results summary" in response.text


def test_api_rejects_non_pdf_upload() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/extract-images",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is not a valid PDF."


def test_api_returns_zip_download_for_pdf_upload(red_png: bytes) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_image(fitz.Rect(20, 20, 120, 120), stream=red_png)

    client = TestClient(app)
    response = client.post(
        "/api/extract-images",
        files={"file": ("sample.pdf", document.tobytes(), "application/pdf")},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    assert archive.namelist() == ["page-001-image-01.png"]


def test_api_supports_non_ascii_upload_filename(red_png: bytes) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_image(fitz.Rect(20, 20, 120, 120), stream=red_png)

    client = TestClient(app)
    response = client.post(
        "/api/extract-images",
        files={"file": ("中文文件.pdf", document.tobytes(), "application/pdf")},
    )

    assert response.status_code == 200
    content_disposition = response.headers["content-disposition"]
    assert 'filename="download-images.zip"' in content_disposition
    assert "filename*=utf-8''%E4%B8%AD%E6%96%87%E6%96%87%E4%BB%B6-images.zip" in content_disposition
