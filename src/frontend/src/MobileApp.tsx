import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useLessons } from '@/hooks/useLessons'
import { useConversation } from '@/hooks/useConversation'
import { useVocabAudio } from '@/hooks/useVocabAudio'
import { useDemoAudio } from '@/hooks/useDemoAudio'
import { useConversationStore } from '@/stores/conversationStore'
import { useAuthStore } from '@/stores/authStore'
import { fetchHelpingPhrases } from '@/services/api'
import { MobileTabBar, type MobileTab } from '@/components/mobile/MobileTabBar'
import { MobileActionBar, type ContentSection } from '@/components/mobile/MobileActionBar'
import { MobileVocabularyView } from '@/components/mobile/content/MobileVocabularyView'
import { MobilePatternsView } from '@/components/mobile/content/MobilePatternsView'
import { MobilePracticeView } from '@/components/mobile/content/MobilePracticeView'
import { MobilePrincipleView } from '@/components/mobile/content/MobilePrincipleView'
import { MobilePatternsOverview } from '@/components/mobile/content/MobilePatternsOverview'
import { MobileEvaluateView } from '@/components/mobile/content/MobileEvaluateView'
import { MobileChatOverlay } from '@/components/mobile/MobileChatOverlay'
import { useDeepLink } from '@/hooks/useDeepLink'
import { LoginPage } from '@/pages/LoginPage'

export function MobileApp() {
  const { t, i18n } = useTranslation()
  const { isAuthenticated, isLoading: authLoading, initialize } = useAuthStore()
  const [currentPath, setCurrentPath] = useState(window.location.hash || '#/')
  const { initialTab } = useDeepLink()
  const [activeTab, setActiveTab] = useState<MobileTab>(initialTab)

  const { lessons, currentLesson, selectedLessonNumber, selectLesson } = useLessons()
  const { courseId, setCourseId, activeSection, setActiveSection, instructionLanguage, setInstructionLanguage, startPatternPractice, helpingPhrases, setHelpingPhrases } = useConversationStore()
  const { playWord, playingWord } = useVocabAudio(selectedLessonNumber ?? undefined, courseId)
  const { playDemo, playingId, playPatternLoop, nextExample, loopingPattern } = useDemoAudio(selectedLessonNumber ?? undefined, courseId)
  const {
    messages,
    isRecording,
    isPlaying,
    isLoading: conversationLoading,
    voiceMode,
    setVoiceMode,
    startRecording,
    stopRecording,
    sendTextMessage,
    disconnect,
  } = useConversation()

  // Track current index for vocab/practice/patterns views
  const [vocabIndex, setVocabIndex] = useState(0)
  const [patternIndex, setPatternIndex] = useState(0)
  const [patternsExampleId, setPatternsExampleId] = useState<string | null>(null)
  const [playingPatternNumber, setPlayingPatternNumber] = useState<number | null>(null)
  const [isChatOpen, setIsChatOpen] = useState(false)

  // Reset indices when lesson changes
  useEffect(() => {
    setVocabIndex(0)
    setPatternIndex(0)
    setPatternsExampleId(null)
    setPlayingPatternNumber(null)
  }, [selectedLessonNumber])

  useEffect(() => {
    initialize()
  }, [initialize])

  // Fetch helping phrases when instruction language changes
  useEffect(() => {
    fetchHelpingPhrases(instructionLanguage)
      .then(setHelpingPhrases)
      .catch(() => setHelpingPhrases([]))
  }, [instructionLanguage, setHelpingPhrases])

  // Simple hash-based routing
  useEffect(() => {
    const handleHashChange = () => {
      setCurrentPath(window.location.hash || '#/')
    }
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  // Handle login page route
  if (currentPath === '#/login') {
    return <LoginPage />
  }

  // Loading state
  if (authLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-lg">{t('app.loading')}</div>
      </div>
    )
  }

  // Handle lesson selection from Lessons tab
  const handleSelectLesson = (lessonNumber: number) => {
    selectLesson(lessonNumber)
    setActiveTab('learn')
  }

  // Helper: get flat list of example IDs for patterns section
  const getExampleIds = () => {
    const ids: string[] = []
    for (const pattern of currentLesson?.patterns || []) {
      if (pattern.examples) {
        pattern.examples.forEach((ex, idx) => {
          if (ex.q && ex.a) {
            ids.push(`${pattern.pattern_number}-${idx + 1}`)
          }
        })
      }
    }
    return ids
  }

  // Handle pattern overview play (plays first example for that pattern)
  const handlePlayPatternOverview = (patternNumber: number) => {
    setPlayingPatternNumber(patternNumber)
    playDemo(patternNumber, 1)
    // Clear playing state when done (approximate based on typical audio length)
    setTimeout(() => setPlayingPatternNumber(null), 5000)
  }

  // Action bar handlers
  const handlePlay = () => {
    if (activeSection === 'vocabulary' && currentLesson?.vocabulary) {
      const word = currentLesson.vocabulary[vocabIndex]
      if (word) {
        playWord(word.english)
      }
    } else if (activeSection === 'patterns' && currentLesson?.patterns) {
      // New patterns section: play first example of first pattern
      const firstPattern = currentLesson.patterns[0]
      if (firstPattern) {
        handlePlayPatternOverview(firstPattern.pattern_number)
      }
    } else if (activeSection === 'examples') {
      // Examples section (formerly patterns): play current example
      if (patternsExampleId) {
        const [pNum, eIdx] = patternsExampleId.split('-').map(Number)
        playDemo(pNum, eIdx)
      } else {
        const ids = getExampleIds()
        if (ids.length > 0) {
          const [pNum, eIdx] = ids[0].split('-').map(Number)
          setPatternsExampleId(ids[0])
          playDemo(pNum, eIdx)
        }
      }
    } else if (activeSection === 'practice' && currentLesson?.patterns) {
      const pattern = currentLesson.patterns[patternIndex]
      if (pattern) {
        // Play all examples for this pattern sequentially
        playPatternLoop(pattern.pattern_number)
      }
    }
  }

  const handleNext = () => {
    if (activeSection === 'vocabulary' && currentLesson?.vocabulary) {
      // Move to next word and play it
      const nextIndex = Math.min(vocabIndex + 1, currentLesson.vocabulary.length - 1)
      setVocabIndex(nextIndex)
      const word = currentLesson.vocabulary[nextIndex]
      if (word) {
        playWord(word.english)
      }
    } else if (activeSection === 'patterns' && currentLesson?.patterns) {
      // New patterns section: move to next pattern and play
      const patterns = currentLesson.patterns
      const currentPatternIdx = patterns.findIndex(p => p.pattern_number === playingPatternNumber)
      const nextIdx = currentPatternIdx < 0 ? 0 : Math.min(currentPatternIdx + 1, patterns.length - 1)
      if (patterns[nextIdx]) {
        handlePlayPatternOverview(patterns[nextIdx].pattern_number)
      }
    } else if (activeSection === 'examples') {
      // Examples section (formerly patterns): move to next example and play it
      const ids = getExampleIds()
      const currentIdx = patternsExampleId ? ids.indexOf(patternsExampleId) : -1
      const nextIdx = Math.min(currentIdx + 1, ids.length - 1)
      if (ids[nextIdx]) {
        const [pNum, eIdx] = ids[nextIdx].split('-').map(Number)
        setPatternsExampleId(ids[nextIdx])
        playDemo(pNum, eIdx)
      }
    } else if (activeSection === 'practice' && loopingPattern) {
      // Skip to next example in the current loop
      nextExample()
    } else if (activeSection === 'practice' && currentLesson?.patterns) {
      // Not looping, move to next pattern and start playing
      const nextIndex = Math.min(patternIndex + 1, currentLesson.patterns.length - 1)
      setPatternIndex(nextIndex)
      const nextPattern = currentLesson.patterns[nextIndex]
      if (nextPattern) {
        playPatternLoop(nextPattern.pattern_number)
      }
    }
  }

  const handleChat = () => {
    setIsChatOpen(true)
  }

  // Get pinned card content for chat overlay
  const getPinnedCard = () => {
    if (activeSection === 'vocabulary' && currentLesson?.vocabulary?.[vocabIndex]) {
      const word = currentLesson.vocabulary[vocabIndex]
      return { title: 'Vocabulary', content: `${word.english} - ${word.spanish}` }
    }
    if (activeSection === 'practice' && currentLesson?.patterns?.[patternIndex]) {
      const pattern = currentLesson.patterns[patternIndex]
      return { title: `Pattern ${pattern.pattern_number}`, content: pattern.question_template }
    }
    return null
  }

  // Convert messages to format expected by MobileChatOverlay
  const chatMessages = messages.map((msg, index) => ({
    id: `msg-${index}`,
    role: msg.role,
    content: msg.content,
  }))

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Header - compact */}
      <header className="flex items-center justify-center border-b px-3 py-2 shrink-0">
        <h1 className="text-sm font-semibold truncate">
          {activeTab === 'lessons' && t(`course.${courseId}`)}
          {activeTab === 'learn' && currentLesson && `L${currentLesson.lesson_number}: ${currentLesson.title}`}
          {activeTab === 'learn' && !currentLesson && t('app.selectLessonPrompt')}
          {activeTab === 'me' && t('mobile.tabs.me', 'Me')}
        </h1>
      </header>

      {/* Content area */}
      <main className="flex-1 overflow-auto">
        {activeTab === 'lessons' && (
          <div className="p-4 space-y-2">
            {lessons.map((lesson) => (
              <button
                key={lesson.lesson_number}
                type="button"
                onClick={() => handleSelectLesson(lesson.lesson_number)}
                className={`w-full text-left p-4 rounded-lg border transition-colors ${
                  selectedLessonNumber === lesson.lesson_number
                    ? 'bg-primary/10 border-primary'
                    : 'bg-card hover:bg-accent/50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20 text-sm font-bold">
                    {lesson.lesson_number}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{lesson.title}</div>
                    {lesson.objective && (
                      <div className="text-xs text-muted-foreground truncate">{lesson.objective}</div>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        {activeTab === 'learn' && (
          <div className="flex flex-col h-full">
            {/* Section pills - Sequential learning flow */}
            <div className="flex gap-2 p-3 overflow-x-auto border-b shrink-0">
              {(['principle', 'vocabulary', 'patterns', 'examples', 'practice', 'evaluate'] as ContentSection[]).map((section) => (
                <button
                  key={section}
                  type="button"
                  onClick={() => setActiveSection(section)}
                  className={`px-3 py-1.5 rounded-full text-sm whitespace-nowrap transition-colors ${
                    activeSection === section
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted hover:bg-muted/80'
                  }`}
                >
                  {t(`sections.${section}`, section.charAt(0).toUpperCase() + section.slice(1))}
                </button>
              ))}
            </div>

            {/* Content area */}
            <div className="flex-1 p-4 overflow-auto">
              {!currentLesson ? (
                <div className="text-center text-muted-foreground py-8">
                  {t('app.selectLessonPrompt')}
                </div>
              ) : (
                <>
                  {activeSection === 'principle' && (
                    <MobilePrincipleView
                      lessonNumber={currentLesson.lesson_number}
                      principleTitle={currentLesson.learning_principle_title}
                      principleContent={currentLesson.learning_principle_content}
                      principleFull={currentLesson.learning_principle_full}
                      ponderQuestions={currentLesson.ponder_questions || []}
                      evaluationCriteria={currentLesson.evaluation_criteria || []}
                    />
                  )}
                  {activeSection === 'vocabulary' && (
                    <MobileVocabularyView
                      vocabulary={currentLesson.vocabulary || []}
                      currentIndex={vocabIndex}
                      playingWord={playingWord}
                      onPlayWord={(index) => {
                        setVocabIndex(index)
                        const word = currentLesson.vocabulary?.[index]
                        if (word) {
                          playWord(word.english)
                        }
                      }}
                    />
                  )}
                  {activeSection === 'patterns' && (
                    <MobilePatternsOverview
                      patterns={currentLesson.patterns || []}
                      playingPattern={playingPatternNumber}
                      onPlayPattern={handlePlayPatternOverview}
                    />
                  )}
                  {activeSection === 'examples' && (
                    <MobilePatternsView
                      patterns={currentLesson.patterns || []}
                      playingId={playingId}
                      currentExampleId={patternsExampleId}
                      onPlayExample={(patternNumber, exampleIndex) => {
                        const id = `${patternNumber}-${exampleIndex}`
                        setPatternsExampleId(id)
                        playDemo(patternNumber, exampleIndex)
                      }}
                    />
                  )}
                  {activeSection === 'practice' && (
                    <MobilePracticeView
                      patterns={currentLesson.patterns || []}
                      currentIndex={patternIndex}
                      loopingPattern={loopingPattern}
                      isAuthenticated={isAuthenticated}
                      onLogin={() => { window.location.hash = '#/login' }}
                      onSelectPattern={setPatternIndex}
                      onStartPractice={(patternNumber) => {
                        if (!isAuthenticated) {
                          window.location.hash = '#/login'
                          return
                        }
                        startPatternPractice(patternNumber)
                        setIsChatOpen(true)
                        sendTextMessage(`I want to practice pattern ${patternNumber}.`)
                      }}
                    />
                  )}
                  {activeSection === 'evaluate' && (
                    <MobileEvaluateView
                      evaluationCriteria={currentLesson.evaluation_criteria || []}
                    />
                  )}
                </>
              )}
            </div>
          </div>
        )}

        {activeTab === 'me' && (
          <div className="p-4 space-y-4">
            {/* Auth section */}
            <div className="rounded-lg border bg-card p-4">
              {isAuthenticated ? (
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{t('auth.signedInAs', 'Signed in')}</div>
                    <div className="text-sm text-muted-foreground truncate">
                      {useAuthStore.getState().account?.email || useAuthStore.getState().account?.username}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => useAuthStore.getState().logout()}
                    className="px-3 py-1.5 text-sm border rounded-lg hover:bg-accent"
                  >
                    {t('auth.signOut')}
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => { window.location.hash = '#/login' }}
                  className="w-full py-2 bg-primary text-primary-foreground rounded-lg font-medium"
                >
                  {t('auth.signInButton', 'Sign In / Sign Up')}
                </button>
              )}
            </div>

            {/* Course selector */}
            <div className="rounded-lg border bg-card p-4">
              <label className="text-sm font-medium">{t('course.studyingQuestion')}</label>
              <div className="mt-2 flex gap-2">
                {['ec1', 'ec2'].map((id) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setCourseId(id)}
                    className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      courseId === id
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted hover:bg-muted/80'
                    }`}
                  >
                    {t(`course.${id}`)}
                  </button>
                ))}
              </div>
            </div>

            {/* Language setting */}
            <div className="rounded-lg border bg-card p-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">{t('app.language', 'Language')}</span>
                <select
                  value={instructionLanguage}
                  onChange={(e) => {
                    const newLang = e.target.value as 'en' | 'es'
                    setInstructionLanguage(newLang)
                    i18n.changeLanguage(newLang)
                  }}
                  className="rounded-md border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="es">Español</option>
                  <option value="en">English</option>
                </select>
              </div>
            </div>

            {/* Placeholder for future settings */}
            <div className="text-center text-muted-foreground py-4 text-sm">
              {t('mobile.me.moreSettingsSoon', 'More settings coming soon')}
            </div>
          </div>
        )}
      </main>

      {/* Action bar (only show on Learn tab) */}
      {activeTab === 'learn' && (
        <MobileActionBar
          section={activeSection as ContentSection}
          onPlay={handlePlay}
          onNext={handleNext}
          onChat={handleChat}
          disabled={!currentLesson}
          chatDisabled={!isAuthenticated}
        />
      )}

      {/* Bottom tab bar */}
      <MobileTabBar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Chat overlay */}
      <MobileChatOverlay
        isOpen={isChatOpen}
        onClose={() => {
          disconnect()
          setIsChatOpen(false)
        }}
        messages={chatMessages}
        pinnedCard={getPinnedCard()}
        isRecording={isRecording}
        isPlaying={isPlaying}
        voiceMode={voiceMode}
        onStartRecording={startRecording}
        onStopRecording={stopRecording}
        onToggleVoiceMode={() => setVoiceMode(voiceMode === 'push-to-talk' ? 'active' : 'push-to-talk')}
        isLoading={conversationLoading}
        helpingPhrases={helpingPhrases}
        instructionLanguage={instructionLanguage}
      />
    </div>
  )
}
