import { useState, useEffect, type KeyboardEvent } from 'react'
import { Send, Trash2 } from 'lucide-react'
import { useLessons } from '@/hooks/useLessons'
import { useConversation } from '@/hooks/useConversation'
import { LessonList } from '@/components/LessonList'
import { LessonMaterialPanel } from '@/components/LessonMaterialPanel'
import { ConversationView } from '@/components/ConversationView'
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
  const { currentPhase, phaseState } = useConversationStore()
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

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-80 shrink-0 border-r bg-card">
        <header className="border-b p-4">
          <h1 className="text-xl font-bold">EnglishConnect</h1>
          <p className="text-sm text-muted-foreground">EC1 Lessons</p>
        </header>
        <div className="h-[calc(100vh-81px)] overflow-y-auto">
          <LessonList
            lessons={lessons}
            selectedLessonNumber={selectedLessonNumber}
            onSelectLesson={selectLesson}
          />
        </div>
      </aside>

      {/* Main content */}
      <main className="flex flex-1 flex-col">
        {/* Header */}
        <header className="flex items-start justify-between border-b p-4">
          <div className="flex-1">
            {currentLesson ? (
              <div>
                <h2 className="text-lg font-semibold">
                  Lesson {currentLesson.lesson_number}: {currentLesson.title}
                </h2>
                {currentLesson.objective && (
                  <p className="text-sm text-muted-foreground">
                    {currentLesson.objective}
                  </p>
                )}
              </div>
            ) : (
              <div>
                <h2 className="text-lg font-semibold">Welcome</h2>
                <p className="text-sm text-muted-foreground">
                  Select a lesson to start practicing
                </p>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Clear chat button */}
            {messages.length > 0 && (
              <button
                type="button"
                onClick={clearMessages}
                className={cn(
                  'rounded-lg p-2 text-muted-foreground transition-colors',
                  'hover:bg-destructive/10 hover:text-destructive',
                  'focus:outline-none focus:ring-2 focus:ring-ring'
                )}
                title="Clear conversation"
              >
                <Trash2 className="h-5 w-5" />
              </button>
            )}
            <UserProfile />
          </div>
        </header>

        {/* Side-by-side content area */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left: Lesson Material Panel */}
          {currentLesson && (
            <div className="w-80 shrink-0 border-r overflow-hidden">
              <LessonMaterialPanel
                lesson={currentLesson}
                currentPhase={currentPhase}
                phaseState={phaseState}
              />
            </div>
          )}

          {/* Right: Conversation */}
          <div className="flex flex-1 flex-col min-w-0">
            {/* Conversation area */}
            <div className="flex-1 overflow-hidden">
              <ConversationView messages={messages} isLoading={isLoading} />
            </div>

            {/* Input area */}
            <footer className="border-t p-4">
              <div className="mx-auto flex max-w-2xl items-center gap-3">
                {/* Voice button */}
                <VoiceButton
                  isRecording={isRecording}
                  isPlaying={isPlaying}
                  onPress={toggleRecording}
                  disabled={!selectedLessonNumber || isLoading}
                />

                {/* Text input */}
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
                      'w-full rounded-full border bg-background px-4 py-3 pr-12',
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
                      'absolute right-2 top-1/2 -translate-y-1/2',
                      'rounded-full p-2 text-muted-foreground transition-colors',
                      'hover:bg-accent hover:text-accent-foreground',
                      'disabled:cursor-not-allowed disabled:opacity-50'
                    )}
                  >
                    <Send className="h-5 w-5" />
                  </button>
                </div>
              </div>
            </footer>
          </div>
        </div>
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
