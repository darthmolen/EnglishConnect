import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { LessonCard } from '../LessonCard'

describe('LessonCard', () => {
  const mockLesson = {
    lesson_number: 5,
    title: 'Hobbies and Interests',
    objective: 'Learn to talk about hobbies',
  }

  it('renders lesson number', () => {
    render(<LessonCard lesson={mockLesson} />)
    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('renders lesson title', () => {
    render(<LessonCard lesson={mockLesson} />)
    expect(screen.getByText('Hobbies and Interests')).toBeInTheDocument()
  })

  it('shows selected styling when isSelected is true', () => {
    render(<LessonCard lesson={mockLesson} isSelected={true} />)
    const card = screen.getByRole('button')
    expect(card).toHaveClass('border-primary')
  })

  it('does not show selected styling when isSelected is false', () => {
    render(<LessonCard lesson={mockLesson} isSelected={false} />)
    const card = screen.getByRole('button')
    expect(card).not.toHaveClass('border-primary')
  })

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn()
    render(<LessonCard lesson={mockLesson} onClick={handleClick} />)
    fireEvent.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('handles null objective gracefully', () => {
    const lessonNoObjective = { ...mockLesson, objective: null }
    render(<LessonCard lesson={lessonNoObjective} />)
    expect(screen.getByText('5')).toBeInTheDocument()
  })
})
