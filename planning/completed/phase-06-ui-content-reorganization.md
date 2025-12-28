# Phase 6: UI Content Reorganization

## Overview

Redesign the lesson view UI to feature a prominent Content Window above the chat, displaying lesson materials in an engaging, interactive format.

---

## Current State

- **Layout**: Side-by-side (LessonMaterialPanel 320px | ConversationView flex-1)
- **Vocabulary**: Grouped by category with bullet points (just completed)
- **Learning Principle**: Collapsible section with title + content
- **Patterns**: Q/A templates with examples
- **Learning Goals**: At bottom, plain text list

---

## Target Layout: Three-Column Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              HEADER                                       │
├──────────────┬───────────────────┬───────────────────────────────────────┤
│              │                   │  ┌─────────────────────────────────┐  │
│   COLUMN 1   │     COLUMN 2      │  │       CONTENT WINDOW            │  │
│   Lessons    │  Lesson Sections  │  │         (>50% height)           │  │
│   (w-64)     │     (w-72)        │  │  - Expanded section content     │  │
│              │                   │  │  - Flow layout for categories   │  │
│  ┌────────┐  │  ┌─────────────┐  │  │  - Pattern diagrams             │  │
│  │Lesson 1│  │  │Principle  →│  │  └─────────────────────────────────┘  │
│  │Lesson 2│  │  │Goals      →│  │  ┌─────────────────────────────────┐  │
│  │Lesson 3│  │  │Vocabulary →│  │  │         CHAT WINDOW             │  │
│  │  ...   │  │  │Patterns   →│  │  │         (<50% height)           │  │
│  └────────┘  │  └─────────────┘  │  │  - Conversation transcript      │  │
│              │                   │  │  - Voice/text input             │  │
│              │                   │  └─────────────────────────────────┘  │
└──────────────┴───────────────────┴───────────────────────────────────────┘
```

**Interaction Flow:**
1. User clicks section in Column 2 (e.g., "Vocabulary →")
2. Section collapses in Column 2
3. Content expands into Content Window in Column 3
4. Arrow icon with alt="Open right" indicates expandable sections

---

## Requirements

### 1. Three-Column Layout

- **Column 1 (w-64)**: Lesson list (existing, narrower)
- **Column 2 (w-72)**: Lesson sections with expand arrows
- **Column 3 (flex-1)**: Content Window (>50%) + Chat Window (<50%)

### 2. Section Navigation (Column 2)

Clickable sections with → arrow icon (alt="Open right"):

1. **Learning Principle** (opening paragraphs)
2. **Learning Goals** (checkable boxes) - moved to 2nd position
3. **Vocabulary** (by category)
4. **Patterns** (with diagram images)

**Behavior**: Click section → collapses in Column 2, expands in Content Window

### 3. Opening Paragraphs (Learning Principle)

- Extract: "Study the Principle of Learning" full section + Ponder questions
- Display: Paragraphs flow horizontally using CSS columns/flex-wrap
- Include: Ponder reflection questions as styled callouts

### 4. Learning Goals (2nd position)

- Move from bottom to 2nd section
- Add checkboxes for each "I can:" criterion
- **State**: LocalStorage (Phase 7 roadmap: backend persistence)

### 5. Vocabulary Display

- Group by category (already done)
- **Flow**: Categories as flex-wrap blocks (`flex flex-wrap gap-4`)
- Each category = min-width block that wraps horizontally

### 6. Pattern Diagram Images

- Extract: **Figure images only** (e.g., `_page_XX_Figure_N.jpeg`)
- Filter out: Generic pictures, skip `_page_XX_Picture_N.jpeg`
- Source: `content/refined/ec1/books/englishconnect_1_para_los_alumnos/`
- Serve: Via FastAPI static files endpoint

---

## Implementation Phases

### Phase 6.1: Backend - Extract Additional Content

**Files to modify:**

- `src/tools/content_ingestion.py`
- `src/backend/app/models/content.py`
- `src/backend/app/schemas/lesson.py`
- `src/backend/app/services/lesson_service.py`

**New content to extract:**

1. **Ponder questions** - reflection prompts from "Ponder" section
2. **Pattern figure images** - filter `_page_XX_Figure_N.jpeg` paths only
3. **Full learning principle** - complete paragraphs (not just summary)

**Schema additions:**

```python
# In LessonDetail response
ponder_questions: list[str]
pattern_images: list[str]  # Figure image URLs only
learning_principle_full: str  # Complete principle text
```

### Phase 6.2: Backend - Static Image Serving

**Files to modify:**

- `src/backend/app/main.py`

**Add static file mount:**

```python
from fastapi.staticfiles import StaticFiles

app.mount(
    "/content/images",
    StaticFiles(directory="content/refined/ec1/books/englishconnect_1_para_los_alumnos"),
    name="lesson_images"
)
```

### Phase 6.3: Frontend - Three-Column Layout

**Files to modify:**

- `src/frontend/src/App.tsx`

**New layout structure:**

```tsx
<div className="flex h-screen">
  {/* Column 1: Lessons (narrower) */}
  <aside className="w-64 shrink-0 border-r">
    <LessonList />
  </aside>

  {/* Column 2: Sections */}
  <aside className="w-72 shrink-0 border-r">
    <LessonSections />
  </aside>

  {/* Column 3: Content + Chat */}
  <main className="flex flex-col flex-1">
    <ContentWindow className="h-[55%] border-b-2" />
    <ConversationView className="h-[45%]" />
  </main>
</div>
```

### Phase 6.4: Frontend - Section Navigation Component

**New file:** `src/frontend/src/components/LessonSections.tsx`

```tsx
// Sections list with expand arrows
<div className="flex flex-col">
  <SectionButton
    title="Learning Principle"
    icon={<ArrowRight />}
    onClick={() => expandSection('principle')}
    isExpanded={activeSection === 'principle'}
  />
  <SectionButton title="Learning Goals" ... />
  <SectionButton title="Vocabulary" ... />
  <SectionButton title="Patterns" ... />
</div>
```

### Phase 6.5: Frontend - Content Window Component

**Refactor:** `LessonMaterialPanel.tsx` → `ContentWindow.tsx`

**Structure:**

```tsx
<ContentWindow activeSection={activeSection}>
  {activeSection === 'principle' && (
    <PrincipleView
      title={lesson.learning_principle_title}
      content={lesson.learning_principle_full}
      ponderQuestions={lesson.ponder_questions}
    />
  )}
  {activeSection === 'goals' && (
    <GoalsView criteria={lesson.evaluation_criteria} />
  )}
  {activeSection === 'vocabulary' && (
    <VocabularyView vocabulary={lesson.vocabulary} />
  )}
  {activeSection === 'patterns' && (
    <PatternsView patterns={lesson.patterns} images={lesson.pattern_images} />
  )}
</ContentWindow>
```

### Phase 6.6: Frontend - Flow Layouts

**Vocabulary (flex-wrap):**

```tsx
<div className="flex flex-wrap gap-4 p-4">
  {categories.map(cat => (
    <div className="min-w-[200px] max-w-[300px] flex-1">
      <h4 className="border-b font-semibold">{cat.name}</h4>
      <ul className="space-y-1">...</ul>
    </div>
  ))}
</div>
```

**Principle paragraphs (CSS columns):**

```tsx
<div className="columns-1 md:columns-2 gap-6">
  {paragraphs.map(p => <p className="mb-4">{p}</p>)}
</div>
```

### Phase 6.7: Frontend - Learning Goals with Checkboxes

**Store update:** `src/frontend/src/stores/conversationStore.ts`

```typescript
interface ConversationState {
  // ... existing
  completedGoals: Record<string, Set<number>>  // lessonId -> goal indices
  toggleGoal: (lessonId: number, goalIndex: number) => void
}

// Persist to localStorage
persist(store, { name: 'englishconnect-goals' })
```

**Component:**

```tsx
<GoalsView>
  {criteria.map((goal, i) => (
    <label className="flex items-center gap-3 py-2">
      <Checkbox
        checked={completedGoals[lessonId]?.has(i)}
        onCheckedChange={() => toggleGoal(lessonId, i)}
      />
      <span>{goal}</span>
    </label>
  ))}
</GoalsView>
```

---

## Files to Create/Modify

### New Files

- `src/frontend/src/components/LessonSections.tsx` - Column 2 section navigation
- `src/frontend/src/components/ContentWindow.tsx` - Column 3 content display
- `src/frontend/src/components/content/PrincipleView.tsx` - Learning principle + ponder
- `src/frontend/src/components/content/GoalsView.tsx` - Checkable learning goals
- `src/frontend/src/components/content/VocabularyView.tsx` - Flow layout vocabulary
- `src/frontend/src/components/content/PatternsView.tsx` - Patterns + diagram images

### Modify

- `src/frontend/src/App.tsx` - Three-column layout
- `src/frontend/src/types/index.ts` - Add ponder_questions, pattern_images, learning_principle_full
- `src/frontend/src/stores/conversationStore.ts` - Goal completion state + localStorage persist
- `src/tools/content_ingestion.py` - Extract ponder questions, filter figure images
- `src/backend/app/schemas/lesson.py` - Add new response fields
- `src/backend/app/services/lesson_service.py` - Return new fields
- `src/backend/app/main.py` - Add static files mount for images

### Delete/Rename

- `src/frontend/src/components/LessonMaterialPanel.tsx` → delete (replaced by ContentWindow)

---

## Success Criteria

- [ ] Three-column layout renders correctly
- [ ] Column 2 shows expandable sections with → arrows
- [ ] Clicking section collapses it and opens content in Column 3
- [ ] Content window takes >50% of Column 3 height
- [ ] Clear visual separation between content and chat areas
- [ ] Opening paragraphs display with horizontal flow (CSS columns)
- [ ] Learning Goals appear 2nd with functional checkboxes
- [ ] Goal checkbox state persists in localStorage
- [ ] Vocabulary categories flow horizontally (flex-wrap)
- [ ] Pattern diagram images (Figure only) display correctly
- [ ] All sections are clickable/navigable
- [ ] Responsive on different screen sizes

---

## Phase 7 Roadmap: Backend Goal Persistence

**Future enhancement** (after Phase 6):

- Persist learning goal completion to backend UserProgress model
- Sync across devices
- Track completion analytics

**Files to modify (future):**

- `src/backend/app/models/progress.py` - Add goal_completion field
- `src/backend/app/routers/progress.py` - Add goal update endpoint
- `src/frontend/src/stores/conversationStore.ts` - Sync with backend API
