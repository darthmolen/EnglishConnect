# ADR-007: Mobile Layout v1

**Status**: Accepted
**Date**: 2025-01-09
**Decision Makers**: Project Team

## Context

EnglishConnect has a desktop-first 3-column layout that works well for classroom/office use:

```text
┌─────────────────────────────────────────────────────────┐
│  Header (language, title, user)                         │
├──────────┬──────────┬───────────────────────────────────┤
│ Lessons  │ Sections │ Content                           │
│ (col 1)  │ (col 2)  │ (col 3)                           │
│  w-64    │   w-48   │  flex-1                           │
├──────────┴──────────┴───────────────────────────────────┤
│              [Conversation Tray - expands up]           │
└─────────────────────────────────────────────────────────┘
```

**Problem**: A significant portion of our students are mobile-only users. They cannot effectively use the fixed-width 3-column layout on phones:

- Fixed sidebar widths (w-64, w-48) don't collapse on mobile
- Conversation drawer is completely hidden on mobile (`hidden md:flex`)
- No hamburger menu or collapsible navigation
- Voice controls footer has fixed `max-w-2xl`

**Constraints**:

1. **Don't compromise desktop** - The full site must remain fully functional
2. **No native apps yet** - Need web-based solution until we get traction
3. **Primary use case** - Students spending time on Vocabulary and Practice pages
4. **Hands-free friendly** - Easy to use while practicing with voice

## Decision

**Implement route-based switching with a purpose-built mobile layout.**

### Architecture: Route-Based Switching

```text
App.tsx
├── useIsMobile() hook - detect viewport width
├── if mobile → <MobileApp />
└── else → <DesktopApp /> (current layout, unchanged)

Shared: stores, hooks, API calls, auth, types, services
Separate: layout components, navigation patterns
```

### Mobile Layout Structure

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

### Chat Overlay (slides up from bottom)

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
│      [ MIC ]   PTT      │  Mic button + push-to-talk toggle
├─────────────────────────┤
│ Lessons | Learn | Me    │  Nav stays visible
└─────────────────────────┘
```

### Navigation Design

**3 Bottom Tabs**:

| Tab | Content |
| --- | ------- |
| Lessons | Full-screen lesson picker |
| Learn | Section pills + content (vocabulary, practice, etc.) |
| Me | Registry, goals, settings, profile/logout |

**Action Bar** (above tabs, context-sensitive):

| Section | Play | Next | Chat |
| ------- | ---- | ---- | ---- |
| Vocabulary | Play word audio | Next vocab item | Help mode (Q&A) |
| Practice | Play pattern audio | Next pattern | Practice mode (drills) |
| Principle | TTS read principle | — | — |

### Smart Defaults

- **First visit** to lesson → Show Principle section
- **Return visit** → Show Vocabulary section (tracked via localStorage)

### Chat Behavior

- Chat button opens overlay that slides up, covering content but leaving bottom nav visible
- **Pinned context card** always visible at top (agent can update it as practice progresses)
- Mic bar simplified: big mic button + push-to-talk toggle
- Chat mode determined by source:
  - From Vocabulary → help mode (answer questions)
  - From Practice → practice mode (lead drills)

This aligns with `UnifiedTeachingAgent` modes from ADR-005.

## Alternatives Considered

### 1. Responsive CSS Only

Make existing layout adapt with media queries.

**Rejected because**:

- Desktop layout deeply assumes 3 columns
- Would require significant refactoring of existing components
- Mobile UX would be compromised (accordion sidebars feel clunky)
- Harder to optimize each experience independently

### 2. Subdomain (m.englishconnect.com)

Separate deployment with user-agent redirect.

**Rejected because**:

- Two apps to deploy and maintain
- Students need to know/bookmark correct URL
- Shared code harder to manage
- Overkill for a web app

### 3. Single-Page Responsive (Redesign Everything)

Rebuild the entire UI to be mobile-first responsive.

**Rejected because**:

- High risk of compromising desktop experience
- Massive scope increase
- Desktop works well - don't fix what isn't broken

## Rationale

**Route-based switching** gives us:

- **Desktop untouched** - Zero risk to working desktop experience
- **Purpose-built mobile** - Optimized for touch, voice, single-handed use
- **Shared logic** - Stores, hooks, API calls remain common
- **Independent iteration** - Can improve mobile without affecting desktop
- **Simple detection** - Viewport width on load, no user-agent sniffing complexity

**3-tab bottom nav** because:

- Standard mobile pattern (iOS, Android apps)
- Thumb-friendly zone at bottom of screen
- Reduces cognitive load vs hamburger menus
- Chat as overlay (not tab) preserves context awareness

**Pinned context card** because:

- Students need to know what they're practicing
- Agent can update it during practice (aligns with ADR-002 agent-controlled model)
- Simpler than trying to show/hide content dynamically

## Consequences

### Positive

- Mobile-only students can finally use the app effectively
- Desktop experience preserved completely
- Clean separation enables independent testing
- Mobile layout optimized for primary use cases (vocab, practice)
- Foundation for future enhancements (voice navigation)

### Negative

- Two layout codebases to maintain
- Some UI duplication (content views need mobile variants)
- Testing matrix increases (desktop + mobile viewports)

### Mitigations

- Share as much logic as possible (hooks, stores, API)
- Component tests for mobile views
- E2E tests with mobile viewport (Playwright)
- Clear naming convention (`Mobile*` prefix)

## Implementation Phases

1. **Infrastructure** - `useIsMobile` hook, route switching, `MobileApp.tsx` shell
2. **Bottom Navigation** - `MobileTabBar`, `MobileActionBar`
3. **Lessons Tab** - `MobileLessonList`
4. **Learn Tab** - `MobileLearnView`, mobile content views
5. **Chat Overlay** - `MobileChatOverlay`, `PinnedContextCard`, `MobileMicBar`
6. **Me Tab** - `MobileProfileView`
7. **Polish** - Device testing, touch targets, orientation handling

## References

- [ADR-005](ADR-005-UNIFIED-TEACHING-AGENT.md) - Unified Teaching Agent (modes: help/practice)
- [ADR-002](ADR-002-CONVERSATION-PARTNER-AGENT.md) - Agent controls TTS as tool
