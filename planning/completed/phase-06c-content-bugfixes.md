# Phase 6C: Content Ingestion Bug Fixes

## Overview

Fix content parsing bugs discovered after Phase 6B UI implementation.

---

## Issues Identified

### Issue 1: Learning Goals Have Extra Asterisks
**Root Cause:** Regex `[•\*]` on line 293 of content_ingestion.py matches `*` from `## **Evaluate Your Progress**` header, capturing stray asterisks as criteria.

**Example:** `['*', 'Greet someone...', 'Introduce myself...', '*']`

### Issue 2: Pattern Images Showing Broken
**Root Cause:** Vite dev server only proxies `/api` and `/ws` to the backend. Requests to `/content/images/...` are not proxied, so they hit the SPA router instead of the backend static file server.

### Issue 3: Only Lesson 1 Has Full Learning Principles
**Root Cause:** Lines 88-99 regex expects `## **Eres|You Are|...` section headers. Lesson 2+ have principle content directly after the italicized summary without a separate section header.

**Lesson 1 structure (works):**
```markdown
## **Study the Principle...**
*Short summary*
## **Eres un hijo de Dios**
[Full content paragraphs]
## **Ponder**
```

**Lesson 2+ structure (broken):**
```markdown
## **Study the Principle...**
*Short summary*
[Full content paragraphs directly here]
## **Ponder**
```

### Issue 4: "Choose Your Own Adventure" Missing
**Root Cause:** Same as Issue 2 - these flowchart images are `_Picture_` files, not `_Figure_`.

---

## Implementation Tasks

### Task 1: Create Authenticated Image Endpoint

**File:** `src/backend/app/routers/content.py` (new)

Create a new router for serving content images with authentication:

```python
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.middleware.auth import CurrentUser

router = APIRouter(prefix="/api/content", tags=["content"])

IMAGES_DIR = Path(__file__).parent.parent.parent.parent.parent / "content" / "refined" / "ec1" / "books" / "englishconnect_1_para_los_alumnos"

@router.get("/images/{image_name}")
async def get_image(image_name: str, current_user: CurrentUser):
    """Serve lesson images with authentication."""
    # Validate filename (prevent path traversal)
    if ".." in image_name or "/" in image_name:
        raise HTTPException(status_code=400, detail="Invalid image name")

    image_path = IMAGES_DIR / image_name
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(image_path, media_type="image/jpeg")
```

**File:** `src/backend/app/main.py`

1. Import and include the new router
2. Remove the unauthenticated static files mount

### Task 1b: Update Vite Proxy

**File:** `src/frontend/vite.config.ts`

The `/api` proxy already covers `/api/content`, so no changes needed.

### Task 1c: Update Frontend Image URLs

**File:** `src/frontend/src/components/content/PatternsView.tsx`

Change image src from `/content/images/` to `/api/content/images/`:

```typescript
<img
  src={`/api/content/images/${imagePath}`}
  alt={`Pattern diagram ${index + 1}`}
  ...
/>
```

### Task 2: Fix Learning Goals Asterisks

**File:** `src/tools/content_ingestion.py` (line ~293)

**Current code:**

```python
for match in re.finditer(r"[•\*]\s*(.+?)(?:\n|$)", section_text):
    criterion = match.group(1).strip()
    if criterion and not criterion.startswith("!"):
        criteria.append(criterion)
```

**Fix:** Add filter to exclude single-character or asterisk-only entries:

```python
for match in re.finditer(r"[•\*]\s*(.+?)(?:\n|$)", section_text):
    criterion = match.group(1).strip()
    # Skip image refs, single chars, and asterisk-only entries
    if criterion and not criterion.startswith("!") and len(criterion) > 2:
        criteria.append(criterion)
```

### Task 3: Fix Learning Principle Full Extraction

**File:** `src/tools/content_ingestion.py` (lines 80-99)

**Current regex:** Only matches lessons with separate `## **Eres|You Are...` headers.

**New approach:** Capture all content between italicized summary and `## **Ponder**`:

```python
def _extract_principle_full(self) -> str | None:
    # First try the original pattern (lesson 1 style with separate header)
    match = re.search(
        r"## \*\*(?:Eres|You Are|El|La|Los|Las|Ser|Tener|Hacer|Escuchar|Hablar|Actuar|Orar|Confiar).+?\*\*\n\n(.+?)(?=## \*\*Ponder|## \*\*Memorize)",
        self.content,
        re.DOTALL,
    )

    # If no match, try lesson 2+ style (content after italic summary)
    if not match:
        match = re.search(
            r"Study the Principle of Learning:.+?\n\n\*.+?\*\n\n(.+?)(?=## \*\*Ponder)",
            self.content,
            re.DOTALL,
        )

    if match:
        text = match.group(1)
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    return None
```

### Task 4: Re-run Content Ingestion

After fixing the parser, re-ingest all lessons:

```bash
python src/tools/content_ingestion.py --course ec1 \
  --lessons-dir content/refined/ec1/books/englishconnect_1_para_los_alumnos/lessons
```

### Task 5: Verify Fixes

Run tests and manually verify:

- Learning goals no longer have `*` entries
- All lessons show full learning principle content
- Pattern images display correctly

---

## Files to Create

| File | Purpose |
| ---- | ------- |
| `src/backend/app/routers/content.py` | Authenticated image endpoint |
| `src/frontend/src/components/AuthenticatedImage.tsx` | Image component that fetches with auth token |

## Files to Modify

| File | Changes |
| ---- | ------- |
| `src/backend/app/main.py` | Add content router, remove static mount |
| `src/frontend/src/components/content/PatternsView.tsx` | Use AuthenticatedImage component |
| `src/tools/content_ingestion.py` | Fix criteria regex, fix principle extraction |

---

## Success Criteria

- [x] Pattern images load correctly (authenticated endpoint)
- [x] Learning goals have no `*` bullet entries
- [x] All lessons (1-25) have `learning_principle_full` content
- [x] Re-ingestion completes without errors

---

## Completion Notes

**Completed:** 2024-12-28

All issues resolved:

- Created authenticated `/api/content/images/{name}` endpoint
- Created `AuthenticatedImage` component that fetches images with Bearer token (regular `<img>` tags don't send Authorization headers)
- Fixed criteria extraction to filter out short/asterisk-only entries
- Fixed learning principle full extraction with fallback regex for lesson 2+ structure
- Re-ingested all 25 lessons successfully
- Verified: 0 short criteria entries, all lessons have `learning_principle_full`
