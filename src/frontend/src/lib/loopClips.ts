// Builds the ordered list of audio clips the loop button plays through for a
// section. The order MUST match what the learner sees on screen, so every case
// derives from the same lesson content that renders the cards -- never from the
// audio endpoints' own ordering, which can differ (see the vocabulary bug where
// /api/audio/vocab returned words in a different order than the lesson).

// Minimal structural shapes -- only the fields we read.
interface VocabItem {
  english: string
}
interface VocabAudioItem {
  english_word: string
  stream_url: string
}
interface ExampleItem {
  q?: unknown
  a?: unknown
}
interface PatternItem {
  pattern_number: number
  examples?: ExampleItem[] | null
}
interface DemoItem {
  pattern_number: number
  example_index: number
  stream_url: string
}

export function buildLoopClips(
  section: string,
  vocabulary: VocabItem[],
  patterns: PatternItem[],
  vocabAudio: VocabAudioItem[],
  demos: DemoItem[]
): string[] {
  if (section === 'vocabulary') {
    return vocabulary
      .map(word => vocabAudio.find(v => v.english_word === word.english)?.stream_url)
      .filter((url): url is string => Boolean(url))
  }

  if (section === 'patterns') {
    // Overview shows one card per pattern, so loop the first example of each,
    // in the same pattern order the cards render.
    return patterns
      .map(pattern => {
        const first = demos
          .filter(d => d.pattern_number === pattern.pattern_number)
          .sort((a, b) => a.example_index - b.example_index)[0]
        return first?.stream_url
      })
      .filter((url): url is string => Boolean(url))
  }

  if (section === 'examples') {
    // Flat example cards: iterate patterns, then examples, exactly as
    // MobilePatternsView flattens them (example_index is 1-based to match audio).
    const urls: string[] = []
    for (const pattern of patterns) {
      pattern.examples?.forEach((ex, idx) => {
        if (ex.q && ex.a) {
          const demo = demos.find(
            d => d.pattern_number === pattern.pattern_number && d.example_index === idx + 1
          )
          if (demo) urls.push(demo.stream_url)
        }
      })
    }
    return urls
  }

  return []
}
