# PDF 图片提取网页工具

一个基于 `FastAPI + PyMuPDF` 的轻量 Web 工具。用户上传单个 PDF 后，系统会自动提取其中的图片，统一转成 PNG，并打包成 ZIP 下载。

## 功能特性

- 支持单页多图和多页 PDF
- 支持拖拽上传和点击选择文件
- 显示真实上传进度，并在服务端提取阶段给出明确状态提示
- 提取阶段带有处理中动画卡片
- 上传失败时显示更细化的错误提示卡片
- 下载开始后弹出结果通知框，显示导出张数和 ZIP 文件名
- 用户点击通知框“确认”后，页面会自动刷新
- 优先提取 PDF 内嵌原图
- 对未直接提取出的图片区域做页面裁切补充
- 所有结果统一导出为 PNG
- 下载文件命名格式为 `page-001-image-01.png`

## 限制说明

- 仅支持未加密 PDF
- 默认最大文件大小为 50 MB
- 默认最大页数为 200
- 第一版不做 OCR，也不导出矢量图形
- 不做图片去重，按页面中的每次出现分别保存

## 本地运行

### 1. 创建虚拟环境

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
```

### 2. 安装依赖

```bash
python -m pip install --upgrade pip
python -m pip install fastapi jinja2 pillow pymupdf python-multipart uvicorn httpx pytest
```

### 3. 启动服务

```bash
PYTHONPATH=. uvicorn pic_extractor.main:app --reload
```

启动后访问 [http://127.0.0.1:8000](http://127.0.0.1:8000)。

## 运行测试

```bash
source .venv/bin/activate
PYTHONPATH=. pytest -q
```
