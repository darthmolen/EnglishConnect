# EnglishConnect

**A billion people learning, not a billion dollars earned.**

EnglishConnect is a free, open-source, non-profit conversation partner that helps Spanish-speaking adults practice English out loud. It listens, speaks, and switches between English and Spanish the way a patient tutor would — so a learner can practice anywhere, at their own pace, without a human partner on the other end.

## Why it exists

Learning to *speak* a language is different from learning to read one. The people who need English most often have the least access to what makes speaking practice work: a patient partner, on their schedule, who meets them at their level.

1. **Curriculums are written, but the goal is spoken.** Reading and writing skills don't transfer straight to conversation.
2. **Recorded audio is expensive and slow.** Professional voice production can't keep up as lessons change, so most practice audio is stale or missing.
3. **Switching languages breaks the flow.** A learner who needs a quick clarification in Spanish shouldn't have to stop and leave the lesson to get it.
4. **Working families share the goal but not the schedule.** Everyone wants to learn, but at different paces and times — so a consistent practice partner is hard to find.

EnglishConnect answers all four: an AI conversation partner that speaks generated audio on demand, flips between English and Spanish inside the lesson, and stays within the vocabulary the learner has actually reached.

## What it does

- **Talk, don't type.** The learner speaks; the app transcribes, thinks, and speaks back.
- **Two ways to practice.** *Help* mode answers questions about a lesson; *Practice* mode leads a real back-and-forth and hands the conversation over so the learner does the talking.
- **Bilingual by design.** The partner flips between English and Spanish to unblock a stuck learner, then returns to English.
- **Level-aware.** Responses stay inside the vocabulary and patterns of the learner's current lesson, so practice never runs ahead of them.
- **Hands-free loop playback.** On a commute or a lunch break, one tap plays a whole section — vocabulary, patterns, or examples — pausing between clips so the learner can repeat each one aloud.
- **Every lesson, in order.** Each lesson walks through its principle, vocabulary, sentence patterns, worked examples, guided practice, and a short self-evaluation.
- **Progress that sticks.** The app tracks completed goals and lets learners keep personal goals and a study registry.

## Mobile and desktop

EnglishConnect ships two purpose-built experiences and picks one automatically at a 768px breakpoint.

**Mobile** — built for practicing on the go. A bottom tab bar (**Lessons · Learn · Me**) keeps navigation in thumb's reach, and a per-section action bar drives audio: **Play**, **Next**, **Loop**, and **Chat**. Content is laid out as tap-friendly cards, and the loop button turns any section into hands-free listening practice.

**Desktop** — built for focused study at a keyboard. A lesson list sits in the sidebar, lesson content fills the main window, and the AI partner lives in a slide-out conversation drawer you can open alongside whatever you're reading. It's the richer, multi-panel view for working through a lesson in depth.

Both share the same lessons, the same AI partner, and the same bilingual interface.

## The courses

Content covers the **EnglishConnect 1** and **EnglishConnect 2** curricula, delivered as structured lessons with generated vocabulary and example audio in several voices. The interface itself is bilingual (English and Spanish).

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — how the system fits together: the agent, the voice pipeline, the frontend, and the deployment.
- **[HOW-TO-DEV.md](HOW-TO-DEV.md)** — how to run it locally, run the tests, and ship a change.
- **[planning/](planning/)** — phase-by-phase development history.

## Status

The foundation, voice stack, and unified teaching agent are in place, and the React app is live on Azure Container Apps. Active work covers authentication, progress tracking, and production hardening. See [planning/](planning/) for the current phase.

## License

Open source for educational use.
