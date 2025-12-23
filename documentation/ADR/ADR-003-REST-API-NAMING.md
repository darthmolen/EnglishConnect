# ADR-003: REST API Naming Standards

**Status**: Accepted
**Date**: 2025-12-23
**Decision Makers**: Project Team

## Context

EnglishConnect has multiple conversation modes:
- **Structured lesson flow**: Teacher agent guides students through phases (intro, vocabulary, patterns, practice, wrap-up)
- **Free-form practice**: Open conversation practice without phase constraints

The existing `/api/conversation` endpoint was designed for free-form practice. Adding structured lesson functionality requires a new endpoint. This ADR establishes naming conventions for current and future API endpoints.

## Decision

### 1. Resource-Focused Path Naming

Use paths that clearly indicate the resource domain:

| Path Prefix | Purpose | Examples |
|-------------|---------|----------|
| `/api/lesson/*` | Structured lesson interactions | `/api/lesson/conversation`, `/api/lesson/phases` |
| `/api/practice/*` | Free-form practice | `/api/practice/conversation` |
| `/api/progress/*` | Progress tracking | `/api/progress`, `/api/progress/lessons` |
| `/api/auth/*` | Authentication | `/api/auth/login`, `/api/auth/me` |
| `/api/lessons/*` | Lesson content (CRUD) | `/api/lessons`, `/api/lessons/{id}` |

### 2. Action Clarity in Paths

- Use nouns for resources: `/api/lessons`, `/api/progress`
- Use sub-resources for actions: `/api/lesson/conversation` (not `/api/lesson-conversation`)
- Use query parameters for filtering: `/api/lessons?course=ec1`

### 3. Specific Endpoint Changes

**Rename existing endpoint:**
- `/api/conversation` → `/api/practice/conversation`

**Add new endpoint:**
- `/api/lesson/conversation` - Structured lesson conversation with phase tracking

### 4. Response Consistency

All conversation-type endpoints should return consistent structure:
- `text`: Agent response text
- `audio_base64`: Optional synthesized audio
- `audio_format`: Audio format (e.g., "wav")
- `language`: Response language ("en" or "es")

Phase-specific responses add:
- `phase`: Current lesson phase
- `phase_state`: Phase-specific state (vocab_index, etc.)
- `phase_progress`: Progress indicator (current/total)

## Consequences

### Positive

- Clear separation between lesson modes (structured vs free-form)
- Intuitive API structure for frontend developers
- Extensible pattern for future features
- Consistent with REST best practices

### Negative

- Breaking change: existing `/api/conversation` consumers must update to `/api/practice/conversation`
- Frontend code changes required for endpoint migration

### Neutral

- May need API versioning strategy in future (e.g., `/api/v2/...`)

## Alternatives Considered

1. **Query parameter differentiation**: `/api/conversation?mode=lesson` - Rejected because modes have different request/response schemas
2. **Version-based separation**: `/api/v2/conversation` - Rejected as overkill for current needs
3. **Action-based naming**: `/api/start-lesson`, `/api/practice` - Rejected as less RESTful

## References

- [RESTful API Design Best Practices](https://restfulapi.net/)
- [Microsoft REST API Guidelines](https://github.com/microsoft/api-guidelines)
