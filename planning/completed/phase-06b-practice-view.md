# Phase 6B: Practice View & Conversation Drawer

## Overview

Redesign the content layout to show vocabulary and patterns together in a "Practice" view, and move the conversation transcript to a collapsible right drawer.

**Related ADR**: [ADR-004: Pedagogical-First UI Design](../../documentation/ADR/ADR-004-PEDAGOGICAL-FIRST-UI-DESIGN.md)

---

## Design Decisions

- **Learning Principle is default section** - Start with encouragement before content
- **Practice view combines vocab + patterns** - Students need both as reference during conversation
- **Conversation drawer hidden by default** - Troubleshooting tool, not primary focus
- **Mobile: no drawer** - Voice-only interaction, full content area

---

## Implementation Tasks

### 1. Add "Practice" Section Type

**File:** `src/frontend/src/types/index.ts`

```typescript
export type LessonSection = 'principle' | 'goals' | 'practice' | 'vocabulary' | 'patterns'
```

### 2. Create PracticeView Component

**New file:** `src/frontend/src/components/content/PracticeView.tsx`

Layout:
- Compact vocabulary bar (horizontal chips, expandable)
- Patterns section below (reuse PatternsView)

Compact vocabulary design:
- Category chips in horizontal row with counts
- Click chip to expand/collapse category inline
- Multiple categories can be open at once

### 3. Create CompactVocabulary Component

**New file:** `src/frontend/src/components/content/CompactVocabulary.tsx`

Props: `vocabulary: VocabularyItem[]`

State: `expandedCategories: Set<string>`

### 4. Update LessonSections

**File:** `src/frontend/src/components/LessonSections.tsx`

Update SECTIONS array:
```typescript
const SECTIONS = [
  { id: 'principle', title: 'Learning Principle' },
  { id: 'goals', title: 'Learning Goals' },
  { id: 'practice', title: 'Practice' },
  { id: 'vocabulary', title: 'Vocabulary' },
  { id: 'patterns', title: 'Patterns' },
]
```

### 5. Update ContentWindow

**File:** `src/frontend/src/components/ContentWindow.tsx`

Add case for `activeSection === 'practice'` rendering PracticeView.

### 6. Change Default Section to Principle

**File:** `src/frontend/src/stores/conversationStore.ts`

```typescript
activeSection: 'principle' as LessonSection,  // was 'vocabulary'
```

Also update `selectLesson` to reset to `'principle'`.

### 7. Create ConversationDrawer Component

**New file:** `src/frontend/src/components/ConversationDrawer.tsx`

Props:
- `isOpen: boolean`
- `onToggle: () => void`
- `messages: ChatMessage[]`
- `isLoading: boolean`

Features:
- Fixed width (~280px)
- Absolute positioned on right
- Toggle button in content area
- Hidden on mobile (CSS media query)

### 8. Update App.tsx Layout

**File:** `src/frontend/src/App.tsx`

Changes:
- Add `isDrawerOpen` state (default: false)
- Replace stacked Content+Chat with:
  - Content area (full height minus input bar)
  - ConversationDrawer (overlay on right)
  - Input bar at bottom (always visible)
- Add drawer toggle button

New layout structure:
```tsx
<main className="flex flex-1 flex-col min-w-0 relative">
  <header>...</header>

  <div className="flex-1 relative overflow-hidden">
    <ContentWindow className="h-full" ... />
    <ConversationDrawer isOpen={isDrawerOpen} ... />
    <button onClick={toggleDrawer} className="absolute bottom-4 right-4">
      Toggle
    </button>
  </div>

  <footer>Input bar</footer>
</main>
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `src/frontend/src/components/content/PracticeView.tsx` | Combined vocab + patterns |
| `src/frontend/src/components/content/CompactVocabulary.tsx` | Horizontal chip-based vocab |
| `src/frontend/src/components/ConversationDrawer.tsx` | Collapsible right drawer |

## Files to Modify

| File | Changes |
|------|---------|
| `src/frontend/src/types/index.ts` | Add 'practice' to LessonSection |
| `src/frontend/src/components/LessonSections.tsx` | Add Practice to sections list |
| `src/frontend/src/components/ContentWindow.tsx` | Render PracticeView |
| `src/frontend/src/stores/conversationStore.ts` | Default to 'principle' |
| `src/frontend/src/App.tsx` | New layout with drawer |

---

## Success Criteria

- [x] Learning Principle shows by default when lesson selected
- [x] Practice view shows compact vocab + patterns together
- [x] Vocab chips expand/collapse on click
- [x] Conversation drawer hidden by default
- [x] Drawer toggle works on desktop
- [x] Drawer hidden on mobile (no toggle visible)
- [x] Input bar always visible at bottom
- [x] All 5 sections navigable

## Completion Notes

**Completed:** 2024-12-28

All implementation tasks completed:

- Created `CompactVocabulary.tsx` with expandable category chips
- Created `PracticeView.tsx` combining compact vocab + patterns
- Created `ConversationDrawer.tsx` with toggle button and backdrop
- Updated section navigation to include Practice section
- Changed default section from 'vocabulary' to 'principle'
- Restructured App.tsx layout with drawer overlay pattern

Build verified successfully.
