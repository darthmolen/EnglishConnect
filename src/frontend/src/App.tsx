import { useLessons } from '@/hooks/useLessons'
import { useConversationStore } from '@/stores/conversationStore'
import { LessonList } from '@/components/LessonList'
import { ConversationView } from '@/components/ConversationView'

function App() {
  const { lessons, currentLesson, selectedLessonNumber, selectLesson } =
    useLessons()
  const { messages, isLoading } = useConversationStore()

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

        {/* Input area (placeholder for voice button) */}
        <footer className="border-t p-4">
          <div className="flex items-center justify-center gap-4">
            <p className="text-sm text-muted-foreground">
              Voice interface coming soon...
            </p>
          </div>
        </footer>
      </main>
    </div>
  )
}

export default App
