import { useState, useEffect, type KeyboardEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Send, Trash2 } from 'lucide-react'
import { useLessons } from '@/hooks/useLessons'
import { useConversation } from '@/hooks/useConversation'
import { LessonList } from '@/components/LessonList'
import { LessonSections } from '@/components/LessonSections'
import { ContentWindow } from '@/components/ContentWindow'
import type { PatternAction } from '@/components/content/PatternsView'
import { ConversationDrawer } from '@/components/ConversationDrawer'
import { RegistryDashboard } from '@/components/RegistryDashboard'
import { VoiceButton } from '@/components/VoiceButton'
import { LoginButton } from '@/components/LoginButton'
import { UserProfile } from '@/components/UserProfile'
import { AuthProvider } from '@/auth/AuthProvider'
import { useAuthStore } from '@/stores/authStore'
import { useConversationStore } from '@/stores/conversationStore'
import { cn } from '@/lib/utils'

function AppContent() {
  const { t, i18n } = useTranslation()
  const { isAuthenticated, isLoading: authLoading, checkAuth } = useAuthStore()
  const { lessons, currentLesson, selectedLessonNumber, selectLesson } =
    useLessons()
  const {
    activeSection,
    setActiveSection,
    completedGoals,
    toggleGoal,
    instructionLanguage,
    setInstructionLanguage,
    // Evaluation state
    evaluationRatings,
    personalGoals,
    studyRegistry,
    isRegistryPageSelected,
    // Evaluation actions
    setEvaluationRating,
    addPersonalGoal,
    toggleGoalCompletion,
    removePersonalGoal,
    setStudyRegistryStatus,
    selectRegistryPage,
  } = useConversationStore()
  const {
    messages,
    isRecording,
    isPlaying,
    isLoading,
    toggleRecording,
    sendTextMessage,
    clearMessages,
  } = useConversation()

  const [inputText, setInputText] = useState('')
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const handleSend = () => {
    if (inputText.trim() && selectedLessonNumber) {
      sendTextMessage(inputText)
      setInputText('')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleStartConversation = () => {
    if (selectedLessonNumber && !isLoading) {
      // Send a message to start the conversation practice
      sendTextMessage("I'm ready to practice!")
    }
  }

  const handlePatternAction = (action: PatternAction) => {
    if (!selectedLessonNumber || isLoading) return

    // Open the drawer
    setIsDrawerOpen(true)

    // Send appropriate message based on action type and language
    if (action.type === 'questions') {
      // Questions should be in user's instruction language
      const message = instructionLanguage === 'es'
        ? `Tengo una pregunta sobre el patrón ${action.patternNumber}.`
        : `I have a question about pattern ${action.patternNumber}.`
      sendTextMessage(message)
    } else if (action.type === 'practice') {
      // Practice can start in English (agent will guide)
      sendTextMessage(`I want to practice pattern ${action.patternNumber}.`)
    }
  }

  // Show brief loading only while checking initial auth state
  if (authLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-lg">{t('app.loading')}</div>
      </div>
    )
  }

  // Allow browsing for everyone - only agent interactions require auth
  const lessonGoals = currentLesson
    ? completedGoals[currentLesson.lesson_number] || []
    : []

  return (
    <div className="flex h-screen bg-background">
      {/* Column 1: Lessons (narrower) */}
      <aside className="w-64 shrink-0 border-r bg-card">
        <header className="border-b p-3">
          <h1 className="text-lg font-bold">{t('app.title')}</h1>
          <p className="text-xs text-muted-foreground">{t('app.lessonsSubtitle')}</p>
        </header>
        <div className="h-[calc(100vh-65px)] overflow-y-auto">
          <LessonList
            lessons={lessons}
            selectedLessonNumber={selectedLessonNumber}
            isRegistrySelected={isRegistryPageSelected}
            onSelectLesson={selectLesson}
            onSelectRegistryPage={selectRegistryPage}
          />
        </div>
      </aside>

      {/* Column 2: Lesson Sections (hidden when registry page is selected) */}
      {!isRegistryPageSelected && (
        <aside className="w-48 shrink-0 border-r bg-card">
          <LessonSections
            activeSection={activeSection}
            onSelectSection={setActiveSection}
            hasLesson={!!currentLesson}
          />
        </aside>
      )}

      {/* Column 3: Content + Drawer (or Registry Dashboard) */}
      <main className="flex flex-1 flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between border-b px-4 py-2 shrink-0">
          {/* Language Dropdown */}
          <div className="flex items-center gap-2 shrink-0 mr-4">
            <span className="text-xs text-muted-foreground">{t('app.language')}:</span>
            <select
              value={instructionLanguage}
              onChange={(e) => {
                const newLang = e.target.value as 'en' | 'es';
                setInstructionLanguage(newLang);
                i18n.changeLanguage(newLang);
              }}
              className="rounded-md border bg-background px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="es">Español</option>
              <option value="en">English</option>
            </select>
          </div>

          <div className="flex-1 min-w-0">
            {isRegistryPageSelected ? (
              <div>
                <h2 className="text-base font-semibold">{t('registry.title')}</h2>
                <p className="text-xs text-muted-foreground">
                  {t('registry.lessonProgressHint')}
                </p>
              </div>
            ) : currentLesson ? (
              <div>
                <h2 className="text-base font-semibold truncate">
                  Lesson {currentLesson.lesson_number}: {currentLesson.title}
                </h2>
                {currentLesson.objective && (
                  <p className="text-xs text-muted-foreground truncate">
                    {currentLesson.objective}
                  </p>
                )}
              </div>
            ) : (
              <div>
                <h2 className="text-base font-semibold">{t('app.welcome')}</h2>
                <p className="text-xs text-muted-foreground">
                  {t('app.selectLessonPrompt')}
                </p>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {messages.length > 0 && !isRegistryPageSelected && (
              <button
                type="button"
                onClick={clearMessages}
                className={cn(
                  'rounded-lg p-1.5 text-muted-foreground transition-colors',
                  'hover:bg-destructive/10 hover:text-destructive',
                  'focus:outline-none focus:ring-2 focus:ring-ring'
                )}
                title={t('conversation.clearTitle')}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
            {isAuthenticated ? <UserProfile /> : <LoginButton />}
          </div>
        </header>

        {/* Content area */}
        <div className="flex-1 relative overflow-hidden">
          {isRegistryPageSelected ? (
            <RegistryDashboard
              lessons={lessons}
              studyRegistry={studyRegistry}
              personalGoals={personalGoals}
              onToggleGoal={toggleGoalCompletion}
              onRemoveGoal={removePersonalGoal}
              className="h-full"
            />
          ) : (
            <>
              <ContentWindow
                lesson={currentLesson}
                activeSection={activeSection}
                completedGoals={lessonGoals}
                onToggleGoal={toggleGoal}
                onStartConversation={handleStartConversation}
                onPatternAction={handlePatternAction}
                className="h-full"
                evaluationRatings={currentLesson ? evaluationRatings[currentLesson.lesson_number] || {} : {}}
                personalGoals={personalGoals}
                studyRegistry={currentLesson ? studyRegistry[currentLesson.lesson_number] || {} : {}}
                onSetEvaluationRating={(idx, rating) => currentLesson && setEvaluationRating(currentLesson.lesson_number, idx, rating)}
                onAddPersonalGoal={addPersonalGoal}
                onRemovePersonalGoal={removePersonalGoal}
                onSetStudyRegistryStatus={(item, status) => currentLesson && setStudyRegistryStatus(currentLesson.lesson_number, item, status)}
              />
              <ConversationDrawer
                isOpen={isDrawerOpen}
                onToggle={() => setIsDrawerOpen(!isDrawerOpen)}
                messages={messages}
                isLoading={isLoading}
              />
            </>
          )}
        </div>

        {/* Input bar - hidden when registry page is selected */}
        {!isRegistryPageSelected && (
          <footer className="border-t p-3 shrink-0">
            <div className="mx-auto flex max-w-2xl items-center gap-2">
              <VoiceButton
                isRecording={isRecording}
                isPlaying={isPlaying}
                onPress={toggleRecording}
                disabled={!selectedLessonNumber || isLoading || !isAuthenticated}
                title={!isAuthenticated ? t('auth.signInToSpeak') : undefined}
              />
              <div className="relative flex-1">
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    !isAuthenticated
                      ? t('auth.signInToChat')
                      : selectedLessonNumber
                        ? t('conversation.placeholder')
                        : t('conversation.selectFirst')
                  }
                  disabled={!selectedLessonNumber || isLoading || !isAuthenticated}
                  className={cn(
                    'w-full rounded-full border bg-background px-4 py-2 pr-10 text-sm',
                    'placeholder:text-muted-foreground',
                    'focus:outline-none focus:ring-2 focus:ring-ring',
                    'disabled:cursor-not-allowed disabled:opacity-50'
                  )}
                />
                <button
                  type="button"
                  onClick={handleSend}
                  disabled={!inputText.trim() || !selectedLessonNumber || isLoading || !isAuthenticated}
                  className={cn(
                    'absolute right-1.5 top-1/2 -translate-y-1/2',
                    'rounded-full p-1.5 text-muted-foreground transition-colors',
                    'hover:bg-accent hover:text-accent-foreground',
                    'disabled:cursor-not-allowed disabled:opacity-50'
                  )}
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </div>
          </footer>
        )}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}
