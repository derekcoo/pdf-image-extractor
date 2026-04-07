# Upload Workspace Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refine the upload workspace so the selected-file summary, progress bar, and processing state feel like one unified workflow area, while tightening spacing, badges, dividers, and action copy.

**Architecture:** Keep the change inside the existing server-rendered template and its inline script. Update the DOM structure and CSS tokens just enough to create a lighter shared status panel, then verify the rendered page still exposes the expected upload and feedback hooks.

**Tech Stack:** FastAPI, Jinja2 template, inline HTML/CSS/JavaScript, pytest

---

### Task 1: Tighten the page test around the refined upload workspace

**Files:**
- Modify: `tests/test_app.py`
- Test: `tests/test_app.py`

**Step 1: Write the failing test**

Add assertions for the refined upload workspace copy and shared status region markers.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_app.py::test_index_page_renders_upload_form -q`
Expected: FAIL because the new copy/structure is not present yet.

**Step 3: Write minimal implementation**

Update the template so those new markers and copy appear in the rendered page.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_app.py::test_index_page_renders_upload_form -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_app.py pic_extractor/templates/index.html docs/plans/2026-04-07-upload-workspace-polish-design.md docs/plans/2026-04-07-upload-workspace-polish.md
git commit -m "feat: polish upload workspace presentation"
```

### Task 2: Refine the upload workspace presentation

**Files:**
- Modify: `pic_extractor/templates/index.html`
- Test: `tests/test_app.py`

**Step 1: Write the failing test**

Ensure the template test expects the lighter badge set, unified status panel, and updated button wording.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_app.py::test_index_page_renders_upload_form -q`
Expected: FAIL with missing copy or missing ids/classes.

**Step 3: Write minimal implementation**

Adjust the upload workbench markup, CSS, and inline status logic to:
- reduce badge density
- introduce a shared status shell for selected file, progress, and processing
- soften separators and spacing
- update action and helper text

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_app.py::test_index_page_renders_upload_form -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_app.py pic_extractor/templates/index.html
git commit -m "refactor: unify upload workspace states"
```

### Task 3: Run regression checks

**Files:**
- Modify: none
- Test: `tests/test_app.py`

**Step 1: Write the failing test**

No additional test needed; use the current regression suite.

**Step 2: Run test to verify it fails**

Not applicable.

**Step 3: Write minimal implementation**

No code changes.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_app.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_app.py pic_extractor/templates/index.html
git commit -m "test: verify upload workspace polish"
```
