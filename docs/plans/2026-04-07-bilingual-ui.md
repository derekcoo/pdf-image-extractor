# Bilingual UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a lightweight bilingual UI so the page defaults to the browser’s preferred language between Chinese and English, while allowing an explicit `?lang=zh` or `?lang=en` override and visible language switcher.

**Architecture:** Keep all translation logic inside the existing FastAPI app and server-rendered template. The backend decides the active language and passes a translation dictionary into the template; the frontend script consumes the same dictionary for dynamic states and messages.

**Tech Stack:** FastAPI, Jinja2 template rendering, inline JavaScript, pytest

---

### Task 1: Cover language selection and translated page rendering with tests

**Files:**
- Modify: `tests/test_app.py`
- Test: `tests/test_app.py`

**Step 1: Write the failing test**

Add tests that cover:
- default Chinese rendering when `Accept-Language` prefers Chinese
- English rendering when `?lang=en`
- presence of the language switcher and translated UI strings

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_app.py::test_index_page_renders_upload_form -q`
Expected: FAIL because there is no bilingual rendering or switcher yet.

**Step 3: Write minimal implementation**

Update the app and template until the new translation assertions pass.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_app.py::test_index_page_renders_upload_form -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_app.py pic_extractor/main.py pic_extractor/templates/index.html docs/plans/2026-04-07-bilingual-ui-design.md docs/plans/2026-04-07-bilingual-ui.md
git commit -m "feat: add bilingual UI support"
```

### Task 2: Implement lightweight translation plumbing

**Files:**
- Modify: `pic_extractor/main.py`
- Modify: `pic_extractor/templates/index.html`
- Test: `tests/test_app.py`

**Step 1: Write the failing test**

Ensure the tests expect:
- backend language detection
- URL override
- translated static and dynamic content markers

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_app.py -q`
Expected: FAIL with missing translated content.

**Step 3: Write minimal implementation**

Implement:
- a small translation dictionary in Python
- active language selection helper
- template context for `lang`, `t`, and serialized UI strings
- a language switcher in the template
- JS updates to use injected translated strings

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_app.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_app.py pic_extractor/main.py pic_extractor/templates/index.html
git commit -m "refactor: centralize UI copy for zh and en"
```

### Task 3: Verify regression behavior

**Files:**
- Modify: none
- Test: `tests/test_app.py`, `tests/test_pdf_extractor.py`

**Step 1: Write the failing test**

No additional test beyond the current suite.

**Step 2: Run test to verify it fails**

Not applicable.

**Step 3: Write minimal implementation**

No code changes.

**Step 4: Run test to verify it passes**

Run: `pytest -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_app.py pic_extractor/main.py pic_extractor/templates/index.html
git commit -m "test: verify bilingual UI regression coverage"
```
