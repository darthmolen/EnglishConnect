"""Semantic tests for teacher agent.

These tests verify pedagogical quality and language handling:
- Bilingual responses when requested
- Appropriate vocabulary teaching
- Helpfulness and encouragement

These tests make REAL Azure OpenAI calls and cost money.
Run with: pytest -m "agent_integration and agent_semantic" -v
"""

import pytest

# Note: scenarios imported but not currently used - available for future tests
# from .scenarios import BILINGUAL_SPANISH, STUDENT_CONFUSION


@pytest.mark.agent_semantic
class TestTeacherSemantic:
    """Semantic tests: pedagogical quality, language handling."""

    @pytest.mark.asyncio
    async def test_bilingual_responds_in_spanish(self, teacher_harness):
        """Teacher should respond in Spanish when student requests it."""
        harness = teacher_harness()

        # Ask for Spanish explanation
        response = await harness.send("Hola! No entiendo. ¿Puedes explicar en español?")

        # Check if ANY speak tool call used language="es"
        # (Agent may call speak twice: Spanish first, then English)
        spoke_spanish = any(
            tc.get("name") == "speak" and tc.get("arguments", {}).get("language") == "es"
            for tc in response.tool_calls
        )

        # Also check if Spanish content appears in ANY tool result text
        spanish_indicators = [
            "hola", "lección", "vamos", "practicar", "palabras",
            "bienvenido", "aprender", "español", "ejercicio",
        ]

        # Check all speak tool results for Spanish content
        all_spoken_text = " ".join(
            tr.get("result", {}).get("text", "")
            for tr in response.tool_results
            if tr.get("tool") == "speak"
        )
        found_spanish = any(w.lower() in all_spoken_text.lower() for w in spanish_indicators)

        assert found_spanish or spoke_spanish, (
            f"Expected Spanish response. tool_calls={response.tool_calls}, "
            f"all_spoken_text: {all_spoken_text[:300]}"
        )

    @pytest.mark.asyncio
    async def test_vocabulary_includes_spanish_translation(self, teacher_harness):
        """Teacher should provide Spanish translations when asked."""
        harness = teacher_harness()

        # Get to vocabulary phase
        await harness.send("Hello, I'm ready!")
        await harness.send("Yes, let's start!")

        # Explicitly ask for Spanish translation
        response = await harness.send("How do you say 'exercise' in Spanish?")

        # Should mention the Spanish translation
        spanish_words = ["ejercicio", "spanish", "español", "hacer"]
        found = any(w.lower() in response.text.lower() for w in spanish_words)

        # Also accept if speak was called with language="es"
        spoke_spanish = any(
            tc.get("name") == "speak" and tc.get("arguments", {}).get("language") == "es"
            for tc in response.tool_calls
        )

        assert found or spoke_spanish, (
            f"Expected Spanish translation. text: {response.text[:200]}"
        )

    @pytest.mark.asyncio
    async def test_handles_confusion_supportively(self, teacher_harness):
        """Teacher should be supportive when student expresses confusion."""
        harness = teacher_harness()

        # Initial greeting
        await harness.send("Hello")
        await harness.send("Yes")

        # Express confusion
        response = await harness.send("I don't understand. This is too hard.")

        # Should be supportive, not dismissive
        supportive_words = [
            "help", "try", "again", "let", "okay", "ok", "fine",
            "can", "will", "explain", "repeat", "slowly", "together",
        ]
        found = any(w.lower() in response.text.lower() for w in supportive_words)
        assert found, (
            f"Expected supportive response to confusion: {response.text[:200]}"
        )

    @pytest.mark.asyncio
    async def test_intro_mentions_lesson_topic(self, teacher_harness):
        """Introduction should mention the lesson topic or objective."""
        harness = teacher_harness()

        response = await harness.send("Hello!")

        # Should mention something about hobbies, activities, or learning
        topic_words = ["hobby", "hobbies", "activity", "activities", "learn", "lesson", "today"]
        found = any(w.lower() in response.text.lower() for w in topic_words)
        assert found, (
            f"Expected topic mention in intro: {response.text[:200]}"
        )

    @pytest.mark.asyncio
    async def test_celebrates_correct_answers(self, teacher_harness):
        """Teacher should respond positively when student demonstrates understanding."""
        harness = teacher_harness()

        # Get to vocabulary phase - teacher will present first word
        await harness.send("Hello!")
        await harness.send("Yes, let's start!")

        # First response from teacher presents vocabulary
        # Now explicitly say we understand and repeat
        response = await harness.send("I understand! Exercise means hacer ejercicio, right?")

        # Check for positive/affirming response
        positive_words = [
            "great", "good", "excellent", "well", "correct", "right",
            "yes", "nice", "perfect", "wonderful", "fantastic", "awesome",
            "exactly", "that's", "very",
        ]
        found = any(w.lower() in response.text.lower() for w in positive_words)

        # Also check if record_attempt was called (regardless of correct value)
        # or if advance_phase was called (moving forward is positive)
        recorded_or_advanced = any(
            tc.get("name") in ["record_attempt", "advance_phase"]
            for tc in response.tool_calls
        )

        assert found or recorded_or_advanced, (
            f"Expected positive response or progress. tool_calls={response.tool_calls}, "
            f"text: {response.text[:200]}"
        )

    @pytest.mark.asyncio
    async def test_encourages_struggling_student(self, teacher_harness):
        """Teacher should encourage students who are struggling."""
        harness = teacher_harness()

        await harness.send("Hello")
        await harness.send("OK")

        # Struggle with vocabulary
        response = await harness.send("I can't do this. It's too difficult for me.")

        # Should be encouraging - in English OR Spanish
        encouraging_words_en = [
            "try", "can", "help", "together", "okay", "ok", "fine",
            "practice", "learn", "easy", "slowly", "step",
        ]
        encouraging_words_es = [
            "ayudar", "intentar", "juntos", "despacio", "paso",
            "bien", "puedes", "vamos", "aprender", "fácil",
        ]
        all_encouraging = encouraging_words_en + encouraging_words_es
        found = any(w.lower() in response.text.lower() for w in all_encouraging)
        assert found, (
            f"Expected encouragement for struggling student: {response.text[:200]}"
        )

    @pytest.mark.asyncio
    async def test_uses_simple_language(self, teacher_harness):
        """Teacher should use simple, beginner-appropriate language."""
        harness = teacher_harness()

        response = await harness.send("Hello, I am new to English.")

        # Response should not be overly complex
        # Check for reasonable response length (not a wall of text)
        assert len(response.text) < 500, "Response should be concise for beginners"

        # Should not have overly complex vocabulary (rough heuristic)
        complex_words = [
            "furthermore", "nevertheless", "consequently", "henceforth",
            "notwithstanding", "aforementioned", "subsequently",
        ]
        found = any(w.lower() in response.text.lower() for w in complex_words)
        assert not found, (
            f"Found overly complex language: {response.text[:200]}"
        )
