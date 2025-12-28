import { useState, useEffect, type KeyboardEvent } from 'react'
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
  const { isAuthenticated, isLoading: authLoading, checkAuth } = useAuthStore()
  const { lessons, currentLesson, selectedLessonNumber, selectLesson } =
    useLessons()
  const {
    currentPhase,
    phaseState,
    activeSection,
    setActiveSection,
    completedGoals,
    toggleGoal,
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

  if (authLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center flex-col gap-4">
        <h1 className="text-2xl font-bold">EnglishConnect</h1>
        <p className="text-muted-foreground">Sign in to start practicing English</p>
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
          <h1 className="text-lg font-bold">EnglishConnect</h1>
          <p className="text-xs text-muted-foreground">EC1 Lessons</p>
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
                <h2 className="text-base font-semibold">Welcome</h2>
                <p className="text-xs text-muted-foreground">
                  Select a lesson to start practicing
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
                title="Clear conversation"
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
            currentPhase={currentPhase}
            phaseState={phaseState}
            completedGoals={lessonGoals}
            onToggleGoal={toggleGoal}
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
                    ? 'Type a message or press the mic...'
                    : 'Select a lesson first'
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
