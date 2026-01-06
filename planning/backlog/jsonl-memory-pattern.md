# Backlog: JSONL Append-Only Memory Pattern

**Priority**: Low (consider for Phase 4)
**Dependencies**: None
**Related**: ADR-007, context-engineering-fundamentals skills

## Context

During analysis of the context-engineering-fundamentals skills and the proposed `englishconnect` skill structure, we identified a valuable memory architecture pattern that could supplement or replace PostgreSQL for certain learner data.

## Pattern Description

Append-only JSONL files with schema headers for:
- Error tracking (errors.jsonl)
- Progress events (progress.jsonl)
- Session summaries (sessions.jsonl)

### Schema Header Pattern

```jsonl
{"_schema": "errors", "fields": ["ts", "type", "utterance", "expected", "context"]}
{"ts": "2026-01-05T10:12:00Z", "type": "article_omission", "utterance": "I go to church", "context": "practice_session"}
{"ts": "2026-01-05T10:18:00Z", "type": "article_omission", "utterance": "with family", "context": "practice_session"}
```

### Benefits

1. **Simple querying**: `grep "article_omission" errors.jsonl | wc -l`
2. **Debuggable**: Human-readable, can inspect with any text tool
3. **No migrations**: Schema in header, not in database
4. **Temporal queries**: Natural for "errors in last 7 days" style analysis
5. **Append-only**: No deletion, full history preserved

### Trade-offs vs PostgreSQL

| Aspect | JSONL | PostgreSQL |
|--------|-------|------------|
| Query complexity | Limited (grep/jq) | Full SQL |
| Joins | Manual | Native |
| Transactions | None | ACID |
| Schema changes | Add fields freely | Migrations |
| Debugging | Open file | psql/GUI |
| Backup | Copy file | pg_dump |

## Evaluation Criteria

Consider adopting if:
- Error pattern analysis becomes important for teaching
- Need simpler debugging of learner history
- Want to avoid migrations for schema evolution

Keep PostgreSQL if:
- Need complex queries across entities
- Need transactional guarantees
- Already have good DB tooling

## Implementation Approach

If adopted:
1. Create `LearnerMemory` service with append/query methods
2. Store JSONL files per learner: `data/learners/{user_id}/errors.jsonl`
3. Keep PostgreSQL for relational data (lessons, vocabulary, users)
4. Use JSONL for temporal event streams (errors, progress, sessions)

## Source

- Pattern from `context-engineering-fundamentals:memory-systems` skill
- Applied in proposed `englishconnect` skill structure
- Analysis in ADR-007
