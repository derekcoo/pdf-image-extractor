# PDF 图片提取网页工具

A lightweight FastAPI web app for extracting images from PDF files into PNGs and packaging them as a ZIP download.

一个基于 `FastAPI + PyMuPDF` 的轻量 Web 工具。用户上传单个 PDF 后，系统会优先提取内嵌原图，必要时再补做页面图片区域裁切，最后统一导出为 PNG 并打包成 ZIP 下载。

## At a Glance

- Stack: `FastAPI` + `PyMuPDF` + server-rendered HTML
- Input: a single unencrypted PDF
- Output: PNG images bundled as one ZIP archive
- Best for: document cleanup, editorial review, image archiving, and asset reuse

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
- 对疑似整页扁平化图片的页面，尝试按留白自动拆分多个独立画面
- 所有结果统一导出为 PNG
- 下载文件命名格式为 `page-001-image-01.png`

## 使用场景

- 拆分设计稿、样刊、素材汇编里的图片资源
- 校对 PDF 中图片顺序、页码和出现位置
- 为内容归档或二次编辑快速生成独立图片文件

## 限制说明

- 仅支持未加密 PDF
- 默认最大文件大小为 50 MB
- 默认最大页数为 200
- 第一版不做 OCR，也不导出矢量图形
- 不做图片去重，按页面中的每次出现分别保存
- 轻量拆分模式依赖页面留白和规整布局，复杂扫描件或边界不清的页面可能仍会导出整页图

## 快速开始

### 1. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安装项目依赖

```bash
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

### 3. 启动服务

```bash
PYTHONPATH=. uvicorn pic_extractor.main:app --reload
```

启动后访问 [http://127.0.0.1:8000](http://127.0.0.1:8000)。

## 页面使用流程

1. 打开首页，将一个 PDF 拖入上传区，或点击选择文件。
2. 页面先显示已选择文件信息，再进入上传进度和服务器处理状态。
3. 提取成功后，浏览器会自动开始下载 ZIP。
4. 页面弹出结果通知，显示本次导出张数和 ZIP 文件名。
5. 点击“确认”后页面刷新，方便开始下一次提取。

## HTTP 接口

### `GET /`

- 返回网页工作台
- 页面会注入当前最大文件大小和最大页数限制

### `POST /api/extract-images`

- 表单字段：`file`
- 输入：单个 PDF 文件
- 输出：`application/zip`

常见响应状态：

- `200`：提取成功并返回 ZIP
- `400`：文件不是合法 PDF，或 PDF 受密码保护
- `413`：文件大小或页数超出限制
- `422`：PDF 中没有可提取的图片
- `500`：提取过程中发生未预期异常

## 输出规则

- 所有图片统一转成 PNG
- 文件名按页码和页内顺序编号
- 示例：`page-001-image-01.png`
- 下载 ZIP 文件名默认取上传文件主名，格式为 `<原文件名>-images.zip`

## 多画面页面说明

- 默认仍然优先提取 PDF 内嵌图片对象
- 如果某一页看起来更像一张铺满整页的大图，系统会额外尝试把该页按留白切分成多个画面
- 当前服务器版本使用轻量规则切分，不引入 OpenCV，优先保证部署简单和资源占用可控
- 如果页面边界不清晰、背景复杂或像扫描件，系统会保守回退到整页结果，而不是强行切碎
- 后续可以为本地部署版本增加基于 OpenCV 的增强切分模式，用于处理更复杂的版面

## 项目结构

```text
pic_extractor/
├── pic_extractor/
│   ├── main.py                    # FastAPI 路由和下载响应
│   ├── templates/index.html       # 单页前端界面
│   └── services/pdf_extractor.py  # PDF 图片提取核心逻辑
├── tests/
│   ├── test_app.py                # 页面和 API 测试
│   └── test_pdf_extractor.py      # 提取逻辑测试
├── docs/plans/                    # 本轮设计和实施记录
├── pyproject.toml
└── README.md
```

## 开发命令

### 运行测试

```bash
source .venv/bin/activate
PYTHONPATH=. pytest -q
```

### 启动开发服务

```bash
source .venv/bin/activate
PYTHONPATH=. uvicorn pic_extractor.main:app --reload
```

## 当前实现说明

- 图片提取逻辑分两步：先拿 PDF 内嵌图片，再对页面图片块做补充裁切
- 当页面只检测到接近整页的大图时，会额外尝试按留白拆分多个 panel
- 内嵌图片和补充裁切结果会统一排序后再输出
- 当前界面是服务端渲染的单页模板，没有引入额外前端构建工具
