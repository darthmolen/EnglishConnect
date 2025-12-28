# ADR-004: Pedagogical-First UI Design

**Status**: Accepted
**Date**: 2025-12-27
**Decision Makers**: Project Team

## Context

When designing UI features for EnglishConnect, we observed a pattern: technical framing of problems leads to technical solutions that may not serve the student's actual learning needs.

### The Problem That Surfaced This

We needed to show vocabulary and patterns together so students could reference both during practice. The initial framing was purely technical:

> "How do we show vocab and patterns at the same time?"

Two technical solutions were proposed:
1. **Keep content visible when not active** - Requires dual controls, anti-mobile
2. **Accordion with multiple sections open** - Gets very tall, clunky on mobile

Both solutions addressed the *technical* problem but didn't question the underlying *pedagogical* need.

## Decision

**We will always frame UI decisions with pedagogical questions before technical ones.**

Before asking "how do we build this?", we ask:
- What does the student need to learn?
- When in the learning flow do they need this?
- What helps them focus vs. what distracts?

## The Example: Practice View Design

When we reframed with pedagogical questions, different insights emerged:

| Pedagogical Question | Answer | Design Impact |
|---------------------|--------|---------------|
| "When do students need vocab + patterns together?" | During practice, as a reference while speaking | → Create unified "Practice" view |
| "What should the student see first?" | Encouragement (Learning Principle), not content | → Principle as default section |
| "What role does the conversation transcript play?" | Troubleshooting, not primary learning | → Hidden drawer, not prominent pane |

### What Changed

**Before (Technical Framing):**
- Default section: Vocabulary (it's the first content)
- Conversation: Always visible (50% of screen)
- Vocab + Patterns: Need complex multi-section controls

**After (Pedagogical Framing):**
- Default section: Learning Principle (encouragement first)
- Conversation: Hidden drawer (troubleshooting when needed)
- Vocab + Patterns: Single "Practice" view (what students actually need)

## Consequences

### Positive

- UI decisions align with learning goals, not just technical convenience
- Forces deeper understanding of user needs before building
- Results in simpler, more focused interfaces
- Prevents building features that feel right technically but miss the point

### Negative

- Requires more upfront discussion before implementation
- May feel slower initially (though saves rework later)
- Not all team members may have pedagogical background

### Mitigations

- Use the brainstorming process for UI decisions
- Always include at least one pedagogical question in design discussions
- Reference the guiding principle: "Never implement anything that doesn't get us nearer to solving our problem"

## The Principle

> **Always ask "what does the student need to learn?" before "how do we build it?"**

Technical questions lead to technical solutions. Pedagogical questions reveal the *actual* user need.

## Application Guidelines

When designing any UI feature, ask:

1. **Learning moment**: What is the student trying to learn or practice right now?
2. **Focus**: What should be prominent? What should be hidden?
3. **Flow**: Where does this fit in the learning sequence?
4. **Distraction**: Does this feature help learning or just feel complete?
5. **Mobile**: Does this work for our primary use case (voice practice)?

## References

- [CLAUDE.md: Guiding Principle](../../CLAUDE.md#guiding-principle)
- [ADR-002: Conversation Partner Agent](ADR-002-CONVERSATION-PARTNER-AGENT.md) - Similar principle applied to architecture
- Phase 6B brainstorming session (this ADR's origin)
