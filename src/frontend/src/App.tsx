import { useState, useEffect, type KeyboardEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Send, Trash2 } from 'lucide-react'
import { useLessons } from '@/hooks/useLessons'
import { useConversation } from '@/hooks/useConversation'
import { LessonList } from '@/components/LessonList'
import { LessonSections } from '@/components/LessonSections'
import { ContentWindow } from '@/components/ContentWindow'
import { ConversationDrawer } from '@/components/ConversationDrawer'
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

  if (authLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-lg">{t('app.loading')}</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center flex-col gap-4">
        <h1 className="text-2xl font-bold">{t('app.title')}</h1>
        <p className="text-muted-foreground">{t('app.signInPrompt')}</p>
        <LoginButton />
      </div>
    )
  }

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
            onSelectLesson={selectLesson}
          />
        </div>
      </aside>

      {/* Column 2: Lesson Sections */}
      <aside className="w-48 shrink-0 border-r bg-card">
        <LessonSections
          activeSection={activeSection}
          onSelectSection={setActiveSection}
          hasLesson={!!currentLesson}
        />
      </aside>

      {/* Column 3: Content + Drawer */}
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
            {currentLesson ? (
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
            {messages.length > 0 && (
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
            <UserProfile />
          </div>
        </header>

        {/* Content area with conversation drawer overlay */}
        <div className="flex-1 relative overflow-hidden">
          <ContentWindow
            lesson={currentLesson}
            activeSection={activeSection}
            completedGoals={lessonGoals}
            onToggleGoal={toggleGoal}
            onStartConversation={handleStartConversation}
            className="h-full"
          />
          <ConversationDrawer
            isOpen={isDrawerOpen}
            onToggle={() => setIsDrawerOpen(!isDrawerOpen)}
            messages={messages}
            isLoading={isLoading}
          />
        </div>

        {/* Input bar - always visible at bottom */}
        <footer className="border-t p-3 shrink-0">
          <div className="mx-auto flex max-w-2xl items-center gap-2">
            <VoiceButton
              isRecording={isRecording}
              isPlaying={isPlaying}
              onPress={toggleRecording}
              disabled={!selectedLessonNumber || isLoading}
            />
            <div className="relative flex-1">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  selectedLessonNumber
                    ? t('conversation.placeholder')
                    : t('conversation.selectFirst')
                }
                disabled={!selectedLessonNumber || isLoading}
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
                disabled={!inputText.trim() || !selectedLessonNumber || isLoading}
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
