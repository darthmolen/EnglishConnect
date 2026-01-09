/**
 * Tests for voiceMode state in conversationStore.
 *
 * TDD Task 3: Verify voiceMode state defaults and toggles correctly.
 */

import { describe, test, expect, beforeEach } from 'vitest'
import { useConversationStore } from './conversationStore'

describe('voiceMode state', () => {
  beforeEach(() => {
    // Reset store to initial state
    useConversationStore.setState({
      voiceMode: 'push-to-talk',
    })
  })

  test('defaults to push-to-talk', () => {
    const { voiceMode } = useConversationStore.getState()
    expect(voiceMode).toBe('push-to-talk')
  })

  test('can set to active mode', () => {
    const { setVoiceMode } = useConversationStore.getState()
    setVoiceMode('active')
    expect(useConversationStore.getState().voiceMode).toBe('active')
  })

  test('can toggle back to push-to-talk', () => {
    const { setVoiceMode } = useConversationStore.getState()
    setVoiceMode('active')
    setVoiceMode('push-to-talk')
    expect(useConversationStore.getState().voiceMode).toBe('push-to-talk')
  })
})
