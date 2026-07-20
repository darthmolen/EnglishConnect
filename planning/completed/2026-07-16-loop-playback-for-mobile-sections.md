# Loop Playback for Mobile Sections

## Status: Implemented 2026-07-16 — automated verification passing, manual browser pass outstanding

Built via RED-GREEN-REFACTOR; every test was watched failing for the right reason before implementation.

| Step | Status | Evidence |
|---|---|---|
| 1. Backend `Cache-Control` | Done | 2 new tests in `tests/unit/test_audio_router.py`. RED was `KeyError: 'cache-control'`. |
| 2. `useSectionLoop` hook | Done | 17 new tests in `src/frontend/src/hooks/__tests__/useSectionLoop.test.ts`. |
| 3. 4th action-bar button | Done | 9 new tests (17 total) in `MobileActionBar.test.tsx`. RED was "length of 4 but got 3". |
| 4. `MobileApp` wiring + i18n | Done | `en.json` **and** `es.json` both updated. Typecheck and eslint clean. |

**Files changed**

- `src/backend/app/routers/audio.py` — `Cache-Control: public, max-age=31536000, immutable`
- `src/frontend/src/hooks/useSectionLoop.ts` *(new)* — loop state machine, shadowing pause, prefetch
- `src/frontend/src/components/mobile/MobileActionBar.tsx` — loop button, per-state styling, `aria-pressed`
- `src/frontend/src/MobileApp.tsx` — per-section clip derivation, pause lookup, mutual exclusion
- `src/frontend/src/locales/{en,es}.json` — loop / loopOnce / loopAll

**Verification performed**

- Frontend: 119/119 tests pass across 17 files (`npm run test:run`). `tsc -b` and `eslint` clean.
- Backend: 270 pass, 2 fail. **Both failures are pre-existing and unrelated** — `test_conversation_router.py` calls the real Azure endpoint and gets `openai.AuthenticationError: 401` because it isn't mocked. Verified by stashing the `audio.py` change and reproducing identically.
- Cache header verified live over HTTP (uvicorn on :8011, not just the ASGI test): `cache-control: public, max-age=31536000, immutable`, and a `Range: bytes=0-99` request still returns `206 Partial Content`.

**Measured impact:** one pass through lesson-14 vocabulary is 24 clips / 2.6MB of uncompressed WAV (87–169KB each). Before this change, every continuous-loop cycle re-fetched all of it.

**Review applied** (see `planning/needs-review/completed/` for the audit trail): Spanish keys added to `es.json` — critical because `i18n.ts` sets `lng: 'es'`, so English-only keys would have silently shipped English labels to nearly every student via the `en` fallback, with no failing test. The `clips`/`pauseMs` coupling was fixed structurally (`pauseMs` in the effect deps) rather than documented with a comment. Single-clip boundary test added.

### Outstanding

- **Manual browser verification has not been run** (steps 1–10 in Verification below). In particular: that repeat passes are served from disk cache, that Spanish labels fit the now-quarter-width buttons at 320px, and that the 1s/5s pauses actually feel right when shadowing aloud.
- The 1s/5s shadowing pauses are reasoned guesses, not measured with a student. `duration_seconds` is already returned by the backend and discarded by the frontend, so a duration-proportional pause is available if fixed values feel wrong.
- Backlog candidates surfaced but not addressed: `MobileApp.tsx` faking playback state with `setTimeout(..., 5000)`; the two unmocked conversation-router tests; WAV → Opus transcoding (~10x transfer cut); service-worker offline.

---

## Context

EnglishConnect students are adults with day jobs. They practice in the gaps — commutes, lunch breaks, waiting rooms — often with the phone in a pocket and eyes elsewhere. Today every clip requires a deliberate tap: [`MobileActionBar`](src/frontend/src/components/mobile/MobileActionBar.tsx) offers only Play / Next / Chat, and Play fires exactly one clip. Practicing a 12-word vocabulary set means 12 taps, which is impossible while driving and tedious while walking.

Students have asked to **loop a section's audio hands-free**. This adds a 4th thumb-menu button that plays the whole set for the active tab (vocabulary, patterns, examples) either once or on continuous repeat.

Two findings from exploration shape the plan:

1. **Nothing caches audio today.** [`audio.py:230-234`](src/backend/app/routers/audio.py#L230-L234) returns `FileResponse` with no `Cache-Control`, so the browser falls back to *heuristic* caching — unreliable, often revalidating, and evicted aggressively on mobile. There is no service worker and no `vite-plugin-pwa`. The clips are uncompressed WAV (210MB total; some ~3MB). Looping is the one feature that **guarantees** repeat fetches of the same URLs, so shipping it against uncached WAVs would burn students' mobile data and stall between clips. The cache header is therefore a **prerequisite, not a nice-to-have** — and prefetch depends on it, since a prefetch that isn't cacheable just downloads the file twice.

2. **There is no section-wide playlist.** [`useDemoAudio.playPatternLoop`](src/frontend/src/hooks/useDemoAudio.ts#L118-L153) is the only real sequencer and it is *per-pattern*, not per-section. It's the model to follow, not the thing to extend.

**Outcome:** tap once → play the set through once; tap again → repeat continuously; tap a third time → off. Repeat playback stays on the device's disk cache after the first pass.

## Decisions

| Question | Decision |
|---|---|
| Interaction | Tap-cycling `off → once → all → off`. **Not** long-press — avoids iOS magnifier / Android context-menu conflicts and hidden gestures. |
| Icon | `Repeat` / `Repeat1` from `lucide-react@0.561.0` (already a dependency; `repeat-1.js` confirmed present). |
| State encoding | Three redundant channels: glyph + color + label. Never color alone. |
| Gap between clips | Per-section shadowing pause: **1000ms** for vocabulary (single word), **5000ms** for patterns and examples (full Q&A sentence takes longer to repeat aloud). |
| Caching | `Cache-Control` header + prefetch-next-clip. Service worker / full offline is explicitly out of scope. |

### Button states

| Mode | Glyph | Color | Label | `aria-pressed` |
|---|---|---|---|---|
| `off` | `Repeat` | `text-foreground` (matches siblings) | "Loop" | `false` |
| `once` | `Repeat1` | `text-primary` | "Once" | `true` |
| `all` | `Repeat` | `text-primary-foreground` on `bg-primary` pill | "All" | `true` |

`once` vs `all` differ by **glyph**, so the distinction survives color-vision deficiency and bright sunlight; `off` vs `all` differ by fill *and* label. This is the Spotify/Apple Music convention students already know.

---

## Work

Follow RED-GREEN-REFACTOR per [CLAUDE.md](CLAUDE.md). Every step below: write the failing test, run it, confirm it fails **for the right reason**, then implement.

### 1. Backend — cacheable audio (prerequisite)

**File:** [`src/backend/app/routers/audio.py`](src/backend/app/routers/audio.py#L230-L234)

RED — add to `tests/unit/` (mirror existing audio router tests):
- `stream_audio` response carries `Cache-Control: public, max-age=31536000, immutable`
- `Accept-Ranges: bytes` still present (regression guard)

GREEN — add the header to the existing `FileResponse`:
```python
return FileResponse(
    audio_path,
    media_type="audio/wav",
    headers={
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=31536000, immutable",
    },
)
```

`immutable` is honest here: filenames are content-hashed (`noun-08-bc8b40a1.wav`), and regenerated audio gets a new hash. The route takes no auth header, so responses are safely `public`.

> **Verify this first.** Everything downstream assumes repeat fetches are free.

### 2. Frontend — `useSectionLoop` hook (the core)

**New file:** `src/frontend/src/hooks/useSectionLoop.ts`

Self-contained, owns its own `new Audio()`. Follows the `exampleQueueRef` + `ended`-listener shape of [`useDemoAudio.ts:19-56`](src/frontend/src/hooks/useDemoAudio.ts#L19-L56).

```ts
export type LoopMode = 'off' | 'once' | 'all'

// Shadowing pause: how long the learner needs to repeat the clip aloud.
// A single vocabulary word is quick; a full Q&A sentence is not.
export const SHADOW_PAUSE_MS: Record<ContentSection, number> = {
  vocabulary: 1000,
  patterns: 5000,
  examples: 5000,
}

export function useSectionLoop(clips: string[], pauseMs: number): {
  mode: LoopMode
  currentIndex: number | null
  cycleMode: () => void   // off → once → all → off
  stop: () => void
}
```

The hook takes `pauseMs` as a plain required number and stays section-agnostic; `MobileApp` looks the value up by active section. Keep the map keyed by `ContentSection` (declared at [`MobileActionBar.tsx:5`](src/frontend/src/components/mobile/MobileActionBar.tsx#L5)) so adding a loopable section is a one-line change and TypeScript flags a missing pause.

Behavior:
- `cycleMode()` advances the mode; entering `once`/`all` from `off` starts at index 0; reaching `off` pauses audio and clears timers.
- On `ended`: wait `pauseMs`, then advance. At the end of the list — `once` → return to `off`; `all` → wrap to 0.
- A `pauseMs` change mid-loop must not strand a pending timer holding the old value. Rather than *documenting* that `clips` always changes alongside `pauseMs`, put **`pauseMs` in the cleanup effect's deps** so the stale-timer case is structurally impossible. Behavior-neutral today (only a section switch changes `pauseMs`, and that changes `clips` too), but it removes the invariant instead of asking future contributors to respect it. A short comment explains why `pauseMs` is in the deps.
- **Prefetch:** when clip *n* starts, `void fetch(clips[n+1]).catch(() => {})` to warm the HTTP cache. Depends on step 1.
- On error: stop, return to `off`, clear queue and timers.
- Cleanup: `clearTimeout` the pause timer and pause audio on unmount and on `clips` change (lesson/section switch).

RED — `src/frontend/src/hooks/__tests__/useSectionLoop.test.ts`. Note two gaps in the existing harness that this must close:
- The canonical `MockAudio` in [`useAudioPlayer.test.ts:5-38`](src/frontend/src/hooks/__tests__/useAudioPlayer.test.ts#L5-L38) only supports `onended`-property style. This hook uses `addEventListener`, so **extend `MockAudio` with `addEventListener`/`removeEventListener`/`dispatchEvent`.**
- No test in the repo uses `vi.useFakeTimers`. The 1000ms pause needs them.

Cases:
- starts `off`; `cycleMode` walks `off → once → all → off`
- `once`: plays clips in order, advances on `ended`, returns to `off` after the last clip
- `all`: wraps from last back to index 0 and keeps going
- respects the `pauseMs` it is given — with `pauseMs: 1000`, assert no `play()` after `advanceTimersByTime(999)` and `play()` after `1000`; repeat with `pauseMs: 5000` to prove the value isn't hardcoded
- prefetches clip *n+1* when *n* starts; does not prefetch past the end
- tapping to `off` mid-clip pauses immediately and cancels the pending pause timer
- `play()` rejection resets to `off`
- unmount clears the pending timer (no state update after unmount)
- empty `clips` — `cycleMode` is a no-op, never calls `play()`
- single clip — `once` plays it and returns to `off`; `all` replays it indefinitely. Boundary guard: index 0 is both first and last, and it's the only case that ever replays the same `src` back-to-back. (This does work: setting `src` invokes the media load algorithm even for an unchanged value, and `play()` on an ended element seeks back to the start. Two independent mechanisms — but it's a cheap test to pin.)

### 3. Frontend — 4th action-bar button

**File:** [`src/frontend/src/components/mobile/MobileActionBar.tsx`](src/frontend/src/components/mobile/MobileActionBar.tsx)

Add `loopMode: LoopMode` and `onLoop: () => void` props; append a 4th entry to the `buttons` array (lines 26-48). The existing `flex-1` layout absorbs a 4th button; keep `min-h-[48px]`.

The current map (lines 52-70) applies one uniform `className`. The loop button needs per-state styling, so give the button objects an optional `className` and merge it via the existing `cn()` — do **not** fork the map into a special case.

Enabled for `['vocabulary', 'patterns', 'examples']` (matching `playEnabled`, minus `practice` — practice already has its own per-pattern loop via `playPatternLoop`, and two competing loop controls in one bar would be confusing).

RED — extend [`MobileActionBar.test.tsx`](src/frontend/src/components/mobile/__tests__/MobileActionBar.test.tsx) using the existing presentational pattern (`vi.fn()` props + `fireEvent.click`, i18next mocked to return the fallback string):
- renders 4 buttons
- click calls `onLoop`
- each mode renders its label ("Loop"/"Once"/"All") and correct `aria-pressed`
- disabled on `principle` / `evaluate`

### 4. Frontend — wire into `MobileApp`

**File:** [`src/frontend/src/MobileApp.tsx`](src/frontend/src/MobileApp.tsx)

Derive the clip list **and** the pause for the active section (memoized) and pass both to `useSectionLoop`:

| Section | Clips | Pause |
|---|---|---|
| `vocabulary` | `vocabAudio.map(v => v.stream_url)` from [`useVocabAudio`](src/frontend/src/hooks/useVocabAudio.ts#L11) — already the full flat lesson list | 1000ms |
| `patterns` | one clip per pattern: first example of each, from `demos` | 5000ms |
| `examples` | all `demos` sorted by `(pattern_number, example_index)` — mirror the sort at [`useDemoAudio.ts:122-124`](src/frontend/src/hooks/useDemoAudio.ts#L122-L124) | 5000ms |

Pause comes from `SHADOW_PAUSE_MS[activeSection]`.

**Mutual exclusion (important).** [`MobileApp.tsx:31-32`](src/frontend/src/MobileApp.tsx#L31-L32) already instantiates `useVocabAudio` and `useDemoAudio` side by side — two independent `<audio>` elements that can already play over each other. `useSectionLoop` adds a third. So:
- starting a loop calls `stop()` on both `useVocabAudio` and `useDemoAudio`
- `handlePlay` / `handleNext` ([`:125`](src/frontend/src/MobileApp.tsx#L125), [`:159`](src/frontend/src/MobileApp.tsx#L159)) call `loop.stop()` before playing a single clip
- changing section or lesson stops the loop (the `clips`-change cleanup in step 2 covers this)

**i18n — both locale files, not just English.** [`i18n.ts`](src/frontend/src/i18n.ts) sets `lng: 'es'` with `fallbackLng: 'en'`, so **Spanish is the default language, not an alternate**. Adding keys only to `en.json` would silently render the loop button in English for essentially every student: i18next finds the key via fallback, so there's no missing-key warning, no console error, and no failing test. The inline defaults at [`MobileActionBar.tsx:29`](src/frontend/src/components/mobile/MobileActionBar.tsx#L29) (`t('mobile.actionBar.play', 'Play')`) mask it further.

Add to the `mobile.actionBar` block in **both** [`en.json`](src/frontend/src/locales/en.json) and [`es.json`](src/frontend/src/locales/es.json):

| Key | en | es |
|---|---|---|
| `mobile.actionBar.loop` | Loop | Repetir |
| `mobile.actionBar.loopOnce` | Once | Una vez |
| `mobile.actionBar.loopAll` | All | Todo |

### 5. Out of scope

- Service worker / offline precache (210MB of WAV is its own design problem — backlog).
- The known bug at [`MobileApp.tsx:117-122`](src/frontend/src/MobileApp.tsx#L117-L122): `setTimeout(..., 5000)` fakes playback state instead of listening for `ended`, discarding the real `duration_seconds` the backend already returns at [`audio.py:27`](src/backend/app/routers/audio.py#L27). Not touched here — `useSectionLoop` correctly uses `ended`. Worth a backlog entry.
- WAV → Opus/MP3 transcoding, which would cut transfer ~10x. Separate content-pipeline change; the cache header captures most of the win for looping.

---

## Verification

```bash
# 1. Backend
cd /home/smolen/dev/EnglishConnect
python -m pytest tests/unit/ -v -k audio

# 2. Frontend
cd src/frontend && npm run test:run

# 3. Cache header is actually on the wire
curl -sI http://localhost:8000/api/audio/stream/ec1/vocab/lesson-14/noun-08-bc8b40a1.wav | grep -i cache-control
# expect: cache-control: public, max-age=31536000, immutable
```

**Manual, in a real browser (the part that matters):**
1. `./start.sh`, open the app, DevTools → mobile emulation → Network tab.
2. Vocabulary tab → tap Loop once. Confirm: `Repeat1` glyph + "Once", clips play in order with an audible ~1s gap, stops after the last clip and reverts to "Loop". Then check Examples uses the longer ~5s gap — actually try shadowing a sentence out loud in the gap; if it feels rushed, the number is wrong and worth revisiting with a student.
3. Tap again → "All" fills the pill; confirm it wraps past the last clip and keeps going.
4. Tap a third time → stops immediately mid-clip.
5. **Cache check:** on the second pass through the set, Network shows clips served `(disk cache)` with no new network requests. This is the whole point of step 1 — if requests still hit the network, the header isn't landing.
6. **Prefetch check:** while clip *n* plays, clip *n+1* appears in Network before it's needed.
7. Start a loop, then tap Play — confirm only one audio source is audible (no overlap).
8. Switch tabs mid-loop — confirm audio stops rather than continuing under the new section.
9. **Spanish is the default** (`lng: 'es'`) — confirm the bar reads "Repetir" / "Una vez" / "Todo" and no English leaks in via the `en` fallback.
10. **Label fit:** going from 3 buttons to 4 shrinks each from ⅓ to ¼ width, and Spanish labels run longer ("Reproducir" is already 10 chars at `text-xs`). Check a narrow viewport (320px, iPhone SE) for wrapping or truncation.
