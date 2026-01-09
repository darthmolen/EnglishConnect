import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useLessons } from '@/hooks/useLessons'
import { useConversation } from '@/hooks/useConversation'
import { useConversationStore } from '@/stores/conversationStore'
import { useAuthStore } from '@/stores/authStore'
import { MobileTabBar, type MobileTab } from '@/components/mobile/MobileTabBar'
import { MobileActionBar, type ContentSection } from '@/components/mobile/MobileActionBar'
import { MobileVocabularyView } from '@/components/mobile/content/MobileVocabularyView'
import { MobilePracticeView } from '@/components/mobile/content/MobilePracticeView'
import { MobileChatOverlay } from '@/components/mobile/MobileChatOverlay'
import { LoginPage } from '@/pages/LoginPage'

export function MobileApp() {
  const { t, i18n } = useTranslation()
  const { isAuthenticated, isLoading: authLoading, initialize } = useAuthStore()
  const [currentPath, setCurrentPath] = useState(window.location.hash || '#/')
  const [activeTab, setActiveTab] = useState<MobileTab>('lessons')

  const { lessons, currentLesson, selectedLessonNumber, selectLesson } = useLessons()
  const { activeSection, setActiveSection, instructionLanguage, setInstructionLanguage, startPatternPractice } = useConversationStore()
  const {
    messages,
    isRecording,
    isLoading: conversationLoading,
    voiceMode,
    setVoiceMode,
    toggleRecording,
    sendTextMessage,
  } = useConversation()

  // Track current index for vocab/practice views
  const [vocabIndex, setVocabIndex] = useState(0)
  const [patternIndex, setPatternIndex] = useState(0)
  const [isChatOpen, setIsChatOpen] = useState(false)

  // Reset indices when lesson changes
  useEffect(() => {
    setVocabIndex(0)
    setPatternIndex(0)
  }, [selectedLessonNumber])

  useEffect(() => {
    initialize()
  }, [initialize])

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

  // Action bar handlers
  const handlePlay = () => {
    // TODO: Implement TTS playback based on section context
    if (activeSection === 'vocabulary' && currentLesson?.vocabulary) {
      const word = currentLesson.vocabulary[vocabIndex]
      console.log('Play vocab:', word?.english)
      // TODO: Call TTS API
    } else if (activeSection === 'practice' && currentLesson?.patterns) {
      const pattern = currentLesson.patterns[patternIndex]
      console.log('Play pattern:', pattern?.pattern_number)
      // TODO: Call TTS API
    }
  }

  const handleNext = () => {
    if (activeSection === 'vocabulary' && currentLesson?.vocabulary) {
      setVocabIndex((i) => Math.min(i + 1, currentLesson.vocabulary.length - 1))
    } else if (activeSection === 'practice' && currentLesson?.patterns) {
      setPatternIndex((i) => Math.min(i + 1, currentLesson.patterns.length - 1))
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
          {activeTab === 'lessons' && t('app.title')}
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
            {/* Section pills */}
            <div className="flex gap-2 p-3 overflow-x-auto border-b shrink-0">
              {(['principle', 'goals', 'vocabulary', 'practice', 'evaluate'] as ContentSection[]).map((section) => (
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
                  {activeSection === 'vocabulary' && (
                    <MobileVocabularyView
                      vocabulary={currentLesson.vocabulary || []}
                      currentIndex={vocabIndex}
                      onPlayWord={(index) => {
                        setVocabIndex(index)
                        // TODO: Play TTS
                        console.log('Play word at index:', index)
                      }}
                      onSelectWord={setVocabIndex}
                    />
                  )}
                  {activeSection === 'practice' && (
                    <MobilePracticeView
                      patterns={currentLesson.patterns || []}
                      currentIndex={patternIndex}
                      onPlayPattern={(index) => {
                        setPatternIndex(index)
                        // TODO: Play TTS
                        console.log('Play pattern at index:', index)
                      }}
                      onSelectPattern={setPatternIndex}
                      onStartPractice={(patternNumber) => {
                        startPatternPractice(patternNumber)
                        setIsChatOpen(true)
                        sendTextMessage(`I want to practice pattern ${patternNumber}.`)
                      }}
                    />
                  )}
                  {activeSection === 'principle' && (
                    <div className="prose prose-sm max-w-none">
                      <h3>{currentLesson.learning_principle_title || t('sections.principle')}</h3>
                      <p>{currentLesson.learning_principle_content || t('mobile.principle.noContent', 'No principle content available')}</p>
                    </div>
                  )}
                  {activeSection === 'goals' && (
                    <div className="text-center text-muted-foreground py-8">
                      <p>{t('mobile.goals.comingSoon', 'Goals tracking coming soon')}</p>
                    </div>
                  )}
                  {activeSection === 'evaluate' && (
                    <div className="text-center text-muted-foreground py-8">
                      <p>{t('mobile.evaluate.comingSoon', 'Self-evaluation coming soon')}</p>
                    </div>
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
          disabled={!currentLesson || !isAuthenticated}
        />
      )}

      {/* Bottom tab bar */}
      <MobileTabBar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Chat overlay */}
      <MobileChatOverlay
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        messages={chatMessages}
        pinnedCard={getPinnedCard()}
        isRecording={isRecording}
        voiceMode={voiceMode}
        onToggleRecording={toggleRecording}
        onToggleVoiceMode={() => setVoiceMode(voiceMode === 'push-to-talk' ? 'active' : 'push-to-talk')}
        isLoading={conversationLoading}
      />
    </div>
  )
}
