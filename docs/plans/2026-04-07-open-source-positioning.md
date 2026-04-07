# Open Source Positioning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve the public GitHub presentation of the repository with a clearer README opening and search-friendly topics.

**Architecture:** Keep the change lightweight: only update the README’s top section and GitHub repository metadata. Avoid code changes and keep the docs body intact.

**Tech Stack:** Markdown, GitHub repository metadata, gh CLI

---

### Task 1: Add a clearer README landing section

**Files:**
- Create: none
- Modify: `README.md`
- Test: none

**Step 1: Write the failing test**

Add a README expectation in local review, not automated code tests, since this is presentation-only.

**Step 2: Run test to verify it fails**

Not applicable.

**Step 3: Write minimal implementation**

Update the README header area with:
- a short English subtitle
- a concise quick-summary block
- no unnecessary marketing clutter

**Step 4: Run test to verify it passes**

Review the rendered markdown source and verify the repository landing reads clearly.

**Step 5: Commit**

```bash
git add README.md docs/plans/2026-04-07-open-source-positioning-design.md docs/plans/2026-04-07-open-source-positioning.md
git commit -m "docs: polish open source positioning"
```

### Task 2: Add repository topics

**Files:**
- Create: none
- Modify: GitHub repository metadata
- Test: none

**Step 1: Write the failing test**

Check current repository topics and confirm they are missing.

**Step 2: Run test to verify it fails**

Run: `gh repo view --json repositoryTopics`
Expected: empty or null topics.

**Step 3: Write minimal implementation**

Set a small set of search-friendly topics related to PDF extraction, FastAPI, and the web tool format.

**Step 4: Run test to verify it passes**

Run: `gh repo view --json repositoryTopics`
Expected: topics populated with the selected tags.

**Step 5: Commit**

No git commit required unless docs changed alongside metadata updates.
