# Phase 9: Mobile Layout v1

**Status**: Planning
**ADR**: [ADR-007-MOBILE-LAYOUT-V1](../../documentation/ADR/ADR-007-MOBILE-LAYOUT-V1.md)
**Started**: 2025-01-09

## Goal

Create a purpose-built mobile layout for mobile-only students without compromising the desktop experience.

## Architecture

Route-based switching: detect viewport → render `<MobileApp />` or `<DesktopApp />`.

- **Shared**: stores, hooks, API calls, auth, types, services
- **Separate**: layout components, navigation patterns

## Mobile Layout

```text
┌─────────────────────────┐
│  [Section Pills]        │  Vocab | Practice | Principle...
│  ─────────────────────  │
│                         │
│  Content Area           │
│  ┌───────────────────┐  │
│  │ Card              │  │
│  │ [play] [next]     │  │  Card-level actions
│  └───────────────────┘  │
│                         │
├─────────────────────────┤
│  Play   Next   Chat     │  Action bar (context-aware)
├─────────────────────────┤
│ Lessons | Learn | Me    │  3 bottom tabs
└─────────────────────────┘
```

## Chat Overlay

```text
┌─────────────────────────┐
│ ┌─────────────────────┐ │
│ │ Pinned Card         │ │  Always visible, agent-controlled
│ │ (current pattern)   │ │
│ └─────────────────────┘ │
│                         │
│  Chat messages...       │
│                         │
├─────────────────────────┤
│      [ MIC ]   PTT      │  Mic + push-to-talk toggle
├─────────────────────────┤
│ Lessons | Learn | Me    │  Nav stays visible
└─────────────────────────┘
```

## Tasks

### Task 1: Infrastructure

**Goal**: Mobile detection and route-based switching.

**Files**:

- `src/frontend/src/hooks/useIsMobile.ts` (new)
- `src/frontend/src/App.tsx` (modify)
- `src/frontend/src/MobileApp.tsx` (new)

**Tests**:

- Unit test: `useIsMobile` returns correct value for different viewport widths
- Unit test: resize event triggers re-evaluation

**Implementation**:

1. Create `useIsMobile` hook with 768px breakpoint
2. Modify `App.tsx` to conditionally render `<MobileApp />` or existing layout
3. Create `MobileApp.tsx` shell with placeholder content

### Task 2: Bottom Navigation

**Goal**: Tab bar and action bar components.

**Files**:

- `src/frontend/src/components/mobile/MobileTabBar.tsx` (new)
- `src/frontend/src/components/mobile/MobileActionBar.tsx` (new)

**Tests**:

- Component test: MobileTabBar renders 3 tabs with correct icons/labels
- Component test: MobileTabBar calls onTabChange with correct tab
- Component test: MobileActionBar renders Play/Next/Chat buttons
- Component test: MobileActionBar respects disabled states per section

**Implementation**:

1. Create `MobileTabBar` with Lessons | Learn | Me tabs
2. Create `MobileActionBar` with Play | Next | Chat buttons
3. Wire up to navigation state in MobileApp

### Task 3: Lessons Tab

**Goal**: Full-screen lesson picker.

**Files**:

- `src/frontend/src/components/mobile/MobileLessonList.tsx` (new)

**Tests**:

- Component test: renders lesson cards
- Component test: tapping lesson navigates to Learn tab

**Implementation**:

1. Create `MobileLessonList` using existing `useLessons` hook
2. Tap lesson → update selected lesson → switch to Learn tab

### Task 4: Learn Tab - Structure

**Goal**: Section pills + content container.

**Files**:

- `src/frontend/src/components/mobile/MobileLearnView.tsx` (new)

**Tests**:

- Component test: renders section pills
- Component test: tapping pill changes active section
- Component test: first visit to lesson defaults to Principle
- Component test: return visit defaults to Vocabulary

**Implementation**:

1. Create `MobileLearnView` with horizontal pill scroll
2. Track visited lessons in localStorage
3. Content area renders appropriate mobile view based on section

### Task 5: Learn Tab - Content Views

**Goal**: Mobile-optimized content components.

**Files**:

- `src/frontend/src/components/mobile/content/MobileVocabularyView.tsx` (new)
- `src/frontend/src/components/mobile/content/MobilePracticeView.tsx` (new)
- `src/frontend/src/components/mobile/content/MobilePrincipleView.tsx` (new)
- `src/frontend/src/components/mobile/content/MobileGoalsView.tsx` (new)
- `src/frontend/src/components/mobile/content/MobileEvaluateView.tsx` (new)

**Tests**:

- Component test: MobileVocabularyView renders vocab cards with play/next
- Component test: MobilePracticeView renders pattern cards with play/next
- Component test: card-level play button triggers audio

**Implementation**:

1. Create mobile card layouts optimized for touch (min 44px tap targets)
2. Each card has play/next buttons
3. Reuse existing data hooks (`useLesson`, etc.)

### Task 6: Chat Overlay

**Goal**: Slide-up chat with pinned context card.

**Files**:

- `src/frontend/src/components/mobile/MobileChatOverlay.tsx` (new)
- `src/frontend/src/components/mobile/PinnedContextCard.tsx` (new)
- `src/frontend/src/components/mobile/MobileMicBar.tsx` (new)

**Tests**:

- Component test: overlay slides up when open
- Component test: nav stays visible at bottom
- Component test: pinned card shows current pattern/vocab
- Component test: mic bar has mic button and PTT toggle
- Component test: Chat from Vocabulary opens help mode
- Component test: Chat from Practice opens practice mode

**Implementation**:

1. Create `MobileChatOverlay` with slide animation
2. Create `PinnedContextCard` (always visible anchor)
3. Create `MobileMicBar` (mic button + PTT toggle)
4. Pass agent mode based on source section

### Task 7: Me Tab

**Goal**: Registry, goals, settings, profile.

**Files**:

- `src/frontend/src/components/mobile/MobileProfileView.tsx` (new)

**Tests**:

- Component test: renders registry summary
- Component test: renders personal goals
- Component test: renders settings (language, voice, PTT)
- Component test: logout button triggers auth signout

**Implementation**:

1. Create `MobileProfileView` with sections
2. Reuse existing registry/goals from conversation store
3. Add settings for language, voice prefs, PTT default

### Task 8: Polish & Integration

**Goal**: Device testing and touch optimization.

**Tasks**:

- [ ] Test on Android Chrome (primary target)
- [ ] Test on iOS Safari
- [ ] Verify touch targets are min 44px
- [ ] Test voice recording on mobile browsers
- [ ] Handle orientation changes
- [ ] E2E test with mobile viewport (Playwright)

## Context-Sensitive Behavior Reference

| Section | Play | Next | Chat |
| ------- | ---- | ---- | ---- |
| Vocabulary | Play word audio | Next vocab item | Help mode (Q&A) |
| Practice | Play pattern audio | Next pattern | Practice mode (drills) |
| Principle | TTS read principle | — | — |

## Stretch Goal

Voice navigation: "go to vocabulary", "next lesson", "start practice"

- Defer to future phase

## Dependencies

- Existing stores: `authStore`, `conversationStore`
- Existing hooks: `useLessons`, `useConversation`, `useAudioRecorder`
- Existing API: `/api/practice/conversation`

## Success Criteria

1. Mobile users can navigate all content (lessons, vocabulary, practice)
2. Voice practice works on mobile (mic + PTT)
3. Desktop experience unchanged
4. Touch targets comfortable for one-handed use
