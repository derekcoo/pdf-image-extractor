# Baota Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prepare the PDF image extractor for deployment behind Baota-managed Nginx on a public subdomain, with installable packaging, runtime configuration, a health check endpoint, and safer request execution behavior.

**Architecture:** Keep the existing FastAPI app and server-rendered UI, but introduce a small configuration layer, move extraction work off the async event loop through a threadpool handoff, and make packaging explicit so the app can be installed cleanly on a fresh server. Document the Baota reverse-proxy deployment flow in the README.

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, PyMuPDF, Pillow, pytest

---

### Task 1: Cover deployment-oriented app behavior with failing tests

**Files:**
- Modify: `tests/test_app.py`
- Test: `tests/test_app.py`

**Step 1: Write the failing test**

Add tests for:
- `GET /healthz` returns a healthy response
- app startup reads environment-based limits into the rendered page context
- the extractor call path can be monkeypatched and still returns a ZIP response through the API

**Step 2: Run test to verify it fails**

Run: `/Users/dakouting/my_ideas/pic_extractor/.venv/bin/python -m pytest tests/test_app.py -q`
Expected: FAIL because `/healthz` and environment-driven limits do not exist yet.

**Step 3: Write minimal implementation**

Update the app to expose health status and move limit configuration into a dedicated runtime config helper.

**Step 4: Run test to verify it passes**

Run: `/Users/dakouting/my_ideas/pic_extractor/.venv/bin/python -m pytest tests/test_app.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_app.py pic_extractor/main.py pic_extractor/config.py docs/plans/2026-04-07-baota-deployment-design.md docs/plans/2026-04-07-baota-deployment.md
git commit -m "feat: add deployment runtime configuration"
```

### Task 2: Cover clean packaging with a failing installation-oriented test

**Files:**
- Modify: `tests/test_app.py`
- Modify: `pyproject.toml`
- Create: `MANIFEST.in`

**Step 1: Write the failing test**

Add a test that confirms the template directory resolves correctly from the installed package context and still renders the home page.

**Step 2: Run test to verify it fails**

Run: `/Users/dakouting/my_ideas/pic_extractor/.venv/bin/python -m pytest tests/test_app.py::test_index_page_renders_upload_form -q`
Expected: FAIL once the packaging assertion is added and the package data is not yet explicitly configured.

**Step 3: Write minimal implementation**

Constrain package discovery to `pic_extractor*` and include template assets in the built distribution.

**Step 4: Run test to verify it passes**

Run: `/Users/dakouting/my_ideas/pic_extractor/.venv/bin/python -m pytest tests/test_app.py::test_index_page_renders_upload_form -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml MANIFEST.in tests/test_app.py
git commit -m "fix: make package installable on fresh servers"
```

### Task 3: Move extraction work off the async event loop

**Files:**
- Modify: `pic_extractor/main.py`
- Test: `tests/test_app.py`

**Step 1: Write the failing test**

Add or tighten a test that patches the extractor and verifies the API path still delegates to extraction and returns the expected archive payload.

**Step 2: Run test to verify it fails**

Run: `/Users/dakouting/my_ideas/pic_extractor/.venv/bin/python -m pytest tests/test_app.py -q`
Expected: FAIL until the request path is updated.

**Step 3: Write minimal implementation**

Wrap archive creation in FastAPI’s threadpool helper so the async route does not directly execute the CPU-heavy task.

**Step 4: Run test to verify it passes**

Run: `/Users/dakouting/my_ideas/pic_extractor/.venv/bin/python -m pytest tests/test_app.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pic_extractor/main.py tests/test_app.py
git commit -m "refactor: run extraction work in a threadpool"
```

### Task 4: Add Baota deployment documentation

**Files:**
- Modify: `README.md`

**Step 1: Write the failing test**

Use doc review rather than automated code tests for this deployment-only change.

**Step 2: Run test to verify it fails**

Not applicable.

**Step 3: Write minimal implementation**

Add a Baota deployment section covering:
- subdomain deployment model
- venv setup and install command
- Uvicorn launch command
- Nginx reverse proxy target
- suggested upload size and timeout values

**Step 4: Run test to verify it passes**

Review the markdown and confirm the instructions are executable on a fresh server.

**Step 5: Commit**

```bash
git add README.md
git commit -m "docs: add baota deployment guide"
```

### Task 5: Run full verification

**Files:**
- Modify: none
- Test: `tests/test_app.py`
- Test: `tests/test_pdf_extractor.py`

**Step 1: Run focused tests**

Run: `/Users/dakouting/my_ideas/pic_extractor/.venv/bin/python -m pytest tests/test_app.py -q`
Expected: PASS

**Step 2: Run full test suite**

Run: `/Users/dakouting/my_ideas/pic_extractor/.venv/bin/python -m pytest -q`
Expected: PASS

**Step 3: Verify clean installation path**

Run: `/Users/dakouting/my_ideas/pic_extractor/.venv/bin/python -m pip wheel . --no-deps -w /tmp/pic_extractor_wheel`
Expected: PASS and produce a wheel artifact.

**Step 4: Commit final integration changes**

```bash
git add .
git commit -m "feat: prepare public deployment release"
```
