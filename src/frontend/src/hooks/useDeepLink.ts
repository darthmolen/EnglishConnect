import { useEffect, useRef } from 'react'
import { useConversationStore } from '@/stores/conversationStore'
import type { LessonSection } from '@/types'

const VALID_COURSES = ['ec1', 'ec2']
const VALID_SECTIONS: LessonSection[] = ['principle', 'vocabulary', 'patterns', 'examples', 'practice', 'evaluate']

/**
 * Parse query string on first mount, apply to store, clean URL.
 * Supports QR code deep links like ?c=ec2&l=5&s=vocabulary
 * Returns the target tab for mobile ('lessons' or 'learn').
 */
export function useDeepLink(): { initialTab: 'lessons' | 'learn' } {
  const applied = useRef(false)
  const { setCourseId, selectLesson, setActiveSection } = useConversationStore()

  const params = new URLSearchParams(window.location.search)
  const course = params.get('c')
  const lesson = params.get('l')
  const section = params.get('s')
  const hasDeepLink = !!(course || lesson || section)

  useEffect(() => {
    if (applied.current || !hasDeepLink) return
    applied.current = true

    if (course && VALID_COURSES.includes(course)) {
      setCourseId(course)
    }
    if (lesson) {
      const num = parseInt(lesson, 10)
      if (num >= 1 && num <= 25) selectLesson(num)
    }
    if (section && VALID_SECTIONS.includes(section as LessonSection)) {
      setActiveSection(section as LessonSection)
    }

    // Clean URL (remove query string, keep hash)
    const url = new URL(window.location.href)
    url.search = ''
    window.history.replaceState({}, '', url.toString())
  }, [])

  return { initialTab: hasDeepLink && lesson ? 'learn' : 'lessons' }
}
