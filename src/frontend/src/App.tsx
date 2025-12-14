import { useState, type KeyboardEvent } from 'react'
import { Send } from 'lucide-react'
import { useLessons } from '@/hooks/useLessons'
import { useConversation } from '@/hooks/useConversation'
import { LessonList } from '@/components/LessonList'
import { ConversationView } from '@/components/ConversationView'
import { VoiceButton } from '@/components/VoiceButton'
import { cn } from '@/lib/utils'

function App() {
  const { lessons, currentLesson, selectedLessonNumber, selectLesson } =
    useLessons()
  const {
    messages,
    isRecording,
    isPlaying,
    isLoading,
    toggleRecording,
    sendTextMessage,
  } = useConversation()

  const [inputText, setInputText] = useState('')

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
        <header className="border-b p-4">
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
        </header>

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
      </main>
    </div>
  )
}

export default App
