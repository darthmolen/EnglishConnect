import { describe, it, expect } from 'vitest'
import { buildLoopClips } from '../loopClips'

// Minimal shapes matching the real data. Only the fields buildLoopClips reads
// are present.
const vocab = (english: string) => ({ english })
const audio = (english_word: string, stream_url: string) => ({ english_word, stream_url })
const demo = (pattern_number: number, example_index: number, stream_url: string) => ({
  pattern_number,
  example_index,
  stream_url,
})

describe('buildLoopClips', () => {
  describe('vocabulary', () => {
    it('follows the on-screen vocabulary order, not the audio API order', () => {
      // The card list on screen is I, you, we...
      const vocabulary = [vocab('I'), vocab('you'), vocab('we')]
      // ...but the audio endpoint happens to return them in a different order.
      const vocabAudio = [
        audio('we', '/audio/we.wav'),
        audio('I', '/audio/I.wav'),
        audio('you', '/audio/you.wav'),
      ]

      const clips = buildLoopClips('vocabulary', vocabulary, [], vocabAudio, [])

      expect(clips).toEqual(['/audio/I.wav', '/audio/you.wav', '/audio/we.wav'])
    })

    it('skips words that have no audio', () => {
      const vocabulary = [vocab('I'), vocab('missing'), vocab('you')]
      const vocabAudio = [audio('I', '/audio/I.wav'), audio('you', '/audio/you.wav')]

      const clips = buildLoopClips('vocabulary', vocabulary, [], vocabAudio, [])

      expect(clips).toEqual(['/audio/I.wav', '/audio/you.wav'])
    })
  })

  describe('examples', () => {
    it('follows pattern order then example order as shown on screen', () => {
      const patterns = [
        { pattern_number: 1, examples: [{ q: 'a', a: 'b' }, { q: 'c', a: 'd' }] },
        { pattern_number: 2, examples: [{ q: 'e', a: 'f' }] },
      ]
      // Demos returned out of order; the result must still match the screen.
      const demos = [
        demo(2, 1, '/audio/2-1.wav'),
        demo(1, 2, '/audio/1-2.wav'),
        demo(1, 1, '/audio/1-1.wav'),
      ]

      const clips = buildLoopClips('examples', [], patterns, [], demos)

      expect(clips).toEqual(['/audio/1-1.wav', '/audio/1-2.wav', '/audio/2-1.wav'])
    })

    it('skips examples missing a question or answer', () => {
      const patterns = [
        { pattern_number: 1, examples: [{ q: 'a', a: 'b' }, { q: 'c' }] },
      ]
      const demos = [demo(1, 1, '/audio/1-1.wav'), demo(1, 2, '/audio/1-2.wav')]

      const clips = buildLoopClips('examples', [], patterns, [], demos)

      expect(clips).toEqual(['/audio/1-1.wav'])
    })
  })

  describe('patterns overview', () => {
    it('plays the first example of each pattern in on-screen order', () => {
      const patterns = [
        { pattern_number: 1, examples: [{ q: 'a', a: 'b' }, { q: 'c', a: 'd' }] },
        { pattern_number: 2, examples: [{ q: 'e', a: 'f' }] },
      ]
      const demos = [
        demo(1, 2, '/audio/1-2.wav'),
        demo(2, 1, '/audio/2-1.wav'),
        demo(1, 1, '/audio/1-1.wav'),
      ]

      const clips = buildLoopClips('patterns', [], patterns, [], demos)

      expect(clips).toEqual(['/audio/1-1.wav', '/audio/2-1.wav'])
    })
  })

  it('returns an empty list for non-loopable sections', () => {
    expect(buildLoopClips('practice', [], [], [], [])).toEqual([])
  })
})
