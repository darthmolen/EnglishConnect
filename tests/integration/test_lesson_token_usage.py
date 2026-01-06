"""End-to-end test for capturing token usage during a full lesson flow.

This test simulates a green-path user completing Lesson 7 (Family) to:
1. Capture total token usage across help and practice modes
2. Estimate API costs for a typical lesson session
3. Provide transcript for conversation review

Requires:
- Database with Lesson 7 content ingested
- Azure OpenAI credentials configured
"""

import pytest

from tests.harness.agent_harness import AgentTestHarness


@pytest.mark.asyncio
@pytest.mark.agent_integration
async def test_lesson_7_full_flow_token_usage():
    """
    Test full lesson 7 flow and capture token usage for cost estimation.

    Scenario:
    1. Help mode: 3 vocab questions in Spanish
    2. Help mode: Request sentence with vocab word in both languages
    3. Help mode: Pattern question
    4. Help mode: Ask to say pattern 1 in Spanish
    5. Practice mode: Converse until role flip (3-5 exchanges)

    Lesson 7 Content (Family):
    - Vocabulary: cousin, eyes, glasses, hair, mustache, colors, tall/short, married/single
    - Pattern 1: "Tell me about your (noun)" → "They have (adjective) (noun)"
    - Pattern 2: "Is your (noun) (adjective)?" → "Yes/No, he/she is..."
    """
    # Load real Lesson 7 from database in help mode
    harness = await AgentTestHarness.create(lesson_number=7, agent_mode="help")

    print("\n" + "=" * 60)
    print("LESSON 7 TOKEN USAGE TEST - HELP MODE")
    print("=" * 60)

    # Step 1: Ask 3 vocabulary questions in Spanish
    print("\n--- Step 1: Vocabulary Questions (Spanish) ---")

    response1 = await harness.send("¿Qué significa 'cousin' en español?")
    print(f"Q1: ¿Qué significa 'cousin' en español?")
    print(f"A1: {response1.text[:100]}..." if len(response1.text) > 100 else f"A1: {response1.text}")
    print(f"   Tokens: {response1.total_tokens}")

    response2 = await harness.send("¿Cómo se dice 'ojos' en inglés?")
    print(f"Q2: ¿Cómo se dice 'ojos' en inglés?")
    print(f"A2: {response2.text[:100]}..." if len(response2.text) > 100 else f"A2: {response2.text}")
    print(f"   Tokens: {response2.total_tokens}")

    response3 = await harness.send("¿Qué significa 'married'?")
    print(f"Q3: ¿Qué significa 'married'?")
    print(f"A3: {response3.text[:100]}..." if len(response3.text) > 100 else f"A3: {response3.text}")
    print(f"   Tokens: {response3.total_tokens}")

    # Step 2: Ask for sentence in both languages
    print("\n--- Step 2: Sentence in Both Languages ---")
    response4 = await harness.send(
        "¿Puedes usar 'eyes' en una oración y decirla en inglés y español?"
    )
    print(f"Q4: ¿Puedes usar 'eyes' en una oración y decirla en inglés y español?")
    print(f"A4: {response4.text[:150]}..." if len(response4.text) > 150 else f"A4: {response4.text}")
    print(f"   Tokens: {response4.total_tokens}")

    # Step 3: Ask about patterns
    print("\n--- Step 3: Pattern Question ---")
    response5 = await harness.send("¿Cómo funciona el primer patrón?")
    print(f"Q5: ¿Cómo funciona el primer patrón?")
    print(f"A5: {response5.text[:150]}..." if len(response5.text) > 150 else f"A5: {response5.text}")
    print(f"   Tokens: {response5.total_tokens}")

    # Step 4: Ask to say pattern 1 in Spanish
    print("\n--- Step 4: Pattern in Spanish ---")
    response6 = await harness.send("¿Puedes decirme el patrón 1 en español?")
    print(f"Q6: ¿Puedes decirme el patrón 1 en español?")
    print(f"A6: {response6.text[:150]}..." if len(response6.text) > 150 else f"A6: {response6.text}")
    print(f"   Tokens: {response6.total_tokens}")

    # Capture help mode tokens
    help_summary = harness.get_token_summary()
    print("\n--- Help Mode Summary ---")
    print(f"Total exchanges: {help_summary['exchange_count']}")
    print(f"LLM tokens: {help_summary['total_tokens']} (prompt: {help_summary['prompt_tokens']}, completion: {help_summary['completion_tokens']})")
    print(f"TTS: {help_summary['tts_chars']} chars → ~{help_summary['tts_seconds']}s audio")
    print(f"STT: {help_summary['stt_chars']} chars → ~{help_summary['stt_seconds']}s audio")
    print(f"LLM cost: ${help_summary['llm_cost_usd']:.6f}")
    print(f"Audio cost: ${help_summary['audio_cost_usd']:.6f} (TTS: ${help_summary['tts_cost_usd']:.6f}, STT: ${help_summary['stt_cost_usd']:.6f})")
    print(f"Total cost: ${help_summary['total_cost_usd']:.6f}")

    # Step 5: Switch to practice mode
    print("\n" + "=" * 60)
    print("LESSON 7 TOKEN USAGE TEST - PRACTICE MODE")
    print("=" * 60)

    harness.agent_mode = "practice"
    help_exchanges = harness.exchange_count  # Save before reset
    harness.exchange_count = 0  # Reset for practice mode flip detection
    # Note: We don't call reset() because we want to keep accumulating tokens

    # Practice conversation until flip (scripted student responses)
    print("\n--- Practice Conversation ---")

    # Exchange 0: Student starts
    practice1 = await harness.send("Hola, estoy listo para practicar")
    print(f"Student: Hola, estoy listo para practicar")
    print(f"Partner: {practice1.text[:100]}..." if len(practice1.text) > 100 else f"Partner: {practice1.text}")
    print(f"   Tokens: {practice1.total_tokens}")

    # Exchange 1: Student responds to agent's question
    practice2 = await harness.send("My brother has brown hair.")
    print(f"Student: My brother has brown hair.")
    print(f"Partner: {practice2.text[:100]}..." if len(practice2.text) > 100 else f"Partner: {practice2.text}")
    print(f"   Tokens: {practice2.total_tokens}")

    # Exchange 2: Student continues
    practice3 = await harness.send("Yes, she is tall.")
    print(f"Student: Yes, she is tall.")
    print(f"Partner: {practice3.text[:100]}..." if len(practice3.text) > 100 else f"Partner: {practice3.text}")
    print(f"   Tokens: {practice3.total_tokens}")

    # Exchange 3: Student continues
    practice4 = await harness.send("My cousin has green eyes.")
    print(f"Student: My cousin has green eyes.")
    print(f"Partner: {practice4.text[:100]}..." if len(practice4.text) > 100 else f"Partner: {practice4.text}")
    print(f"   Tokens: {practice4.total_tokens}")

    # Exchange 4: By now flip should happen - student asks question
    practice5 = await harness.send("Tell me about your sister.")
    print(f"Student: Tell me about your sister.")
    print(f"Partner: {practice5.text[:100]}..." if len(practice5.text) > 100 else f"Partner: {practice5.text}")
    print(f"   Tokens: {practice5.total_tokens}")

    # Final token summary (includes both help and practice)
    total_summary = harness.get_token_summary()

    # Calculate totals
    practice_exchanges = total_summary["exchange_count"]
    total_exchanges = help_exchanges + practice_exchanges
    practice_tokens = total_summary["total_tokens"] - help_summary["total_tokens"]

    print("\n" + "=" * 60)
    print("FINAL TOKEN USAGE REPORT")
    print("=" * 60)
    print(f"Total exchanges: {total_exchanges} ({help_exchanges} help + {practice_exchanges} practice)")

    print("\n--- LLM Usage (GPT-4o-mini) ---")
    print(f"Prompt tokens: {total_summary['prompt_tokens']:,}")
    print(f"Completion tokens: {total_summary['completion_tokens']:,}")
    print(f"Total LLM tokens: {total_summary['total_tokens']:,}")
    print(f"LLM cost: ${total_summary['llm_cost_usd']:.6f}")

    print("\n--- Audio Usage (GPT-4o-mini-realtime) ---")
    print(f"TTS output: {total_summary['tts_chars']:,} chars → ~{total_summary['tts_seconds']}s → {total_summary['tts_tokens']:,} tokens")
    print(f"STT input: {total_summary['stt_chars']:,} chars → ~{total_summary['stt_seconds']}s → {total_summary['stt_tokens']:,} tokens")
    print(f"Audio cost: ${total_summary['audio_cost_usd']:.6f} (TTS: ${total_summary['tts_cost_usd']:.6f}, STT: ${total_summary['stt_cost_usd']:.6f})")

    print("\n--- Total Cost ---")
    print(f"LLM: ${total_summary['llm_cost_usd']:.6f}")
    print(f"Audio: ${total_summary['audio_cost_usd']:.6f}")
    print(f"TOTAL: ${total_summary['total_cost_usd']:.6f}")

    # Breakdown by mode
    print("\n--- Breakdown by Mode ---")
    print(f"Help mode: {help_summary['total_tokens']:,} LLM tokens, ~{help_summary['tts_seconds']}s TTS")
    print(f"Practice mode: {practice_tokens:,} LLM tokens")

    # Print full transcript
    print("\n" + "=" * 60)
    print("FULL TRANSCRIPT")
    print("=" * 60)
    print(harness.get_transcript())

    # Assertions for test validation
    assert total_summary["total_tokens"] > 0, "Should have captured tokens"
    assert total_exchanges == 11, f"Expected 11 exchanges (6 help + 5 practice), got {total_exchanges}"
    assert help_summary["total_tokens"] > 0, "Help mode should have tokens"
    assert practice_tokens > 0, "Practice mode should have tokens"

    # Return summary for programmatic access
    return {
        "help_mode": {
            **help_summary,
            "exchange_count": help_exchanges,
        },
        "practice_mode": {
            "prompt_tokens": total_summary["prompt_tokens"] - help_summary["prompt_tokens"],
            "completion_tokens": total_summary["completion_tokens"] - help_summary["completion_tokens"],
            "total_tokens": practice_tokens,
            "exchange_count": practice_exchanges,
        },
        "total": {
            **total_summary,
            "exchange_count": total_exchanges,
        },
    }
