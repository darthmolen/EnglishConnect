import { BookOpen, GraduationCap, User } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

export type MobileTab = 'lessons' | 'learn' | 'me'

interface MobileTabBarProps {
  activeTab: MobileTab
  onTabChange: (tab: MobileTab) => void
}

export function MobileTabBar({ activeTab, onTabChange }: MobileTabBarProps) {
  const { t } = useTranslation()

  const tabs: { id: MobileTab; label: string; icon: React.ReactNode }[] = [
    { id: 'lessons', label: t('mobile.tabs.lessons', 'Lessons'), icon: <BookOpen className="h-5 w-5" /> },
    { id: 'learn', label: t('mobile.tabs.learn', 'Learn'), icon: <GraduationCap className="h-5 w-5" /> },
    { id: 'me', label: t('mobile.tabs.me', 'Me'), icon: <User className="h-5 w-5" /> },
  ]

  return (
    <nav className="flex border-t bg-background" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={activeTab === tab.id}
          onClick={() => onTabChange(tab.id)}
          className={cn(
            'flex flex-1 flex-col items-center justify-center gap-1 py-2',
            'min-h-[56px] transition-colors', // 56px > 44px touch target
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset',
            activeTab === tab.id
              ? 'text-primary bg-primary/5'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
          )}
        >
          {tab.icon}
          <span className="text-xs font-medium">{tab.label}</span>
        </button>
      ))}
    </nav>
  )
}
