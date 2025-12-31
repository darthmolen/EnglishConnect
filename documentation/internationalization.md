# Internationalization (i18n)

## What is i18n?

Internationalization (i18n - "i" + 18 letters + "n") is the process of designing software so it can be adapted to different languages without code changes. Instead of hardcoding text like "Sign in", we use translation keys that map to different values per language.

## Our Implementation

We use **react-i18next**, the most popular React i18n library (2.1M+ weekly downloads).

### Key Files

| File | Purpose |
|------|---------|
| `src/frontend/src/i18n.ts` | Configuration and initialization |
| `src/frontend/src/locales/en.json` | English translations |
| `src/frontend/src/locales/es.json` | Spanish translations |

### How It Works

1. **Configuration** (`i18n.ts`):
```typescript
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';
import es from './locales/es.json';

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, es: { translation: es } },
  lng: 'es',           // Default language
  fallbackLng: 'en',   // Fallback if key missing
  interpolation: { escapeValue: false }
});
```

2. **Translation files** use nested JSON:
```json
{
  "app": {
    "title": "EnglishConnect",
    "language": "Language"
  },
  "auth": {
    "signIn": "Sign in with Microsoft"
  }
}
```

3. **Component usage**:
```tsx
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation();

  return <h1>{t('app.title')}</h1>;
}
```

4. **Interpolation** for dynamic values:
```tsx
// Translation: "{{completed}} of {{total}} completed"
t('goals.completed', { completed: 5, total: 10 })
// Output: "5 of 10 completed"
```

5. **Language switching**:
```tsx
const { i18n } = useTranslation();
i18n.changeLanguage('es'); // Switch to Spanish
```

## Language Control

The language dropdown in the header controls both:
- **UI language** - All buttons, labels, and text in the interface
- **Instruction language** - How the AI explains things to students

This is intentional: Spanish-speaking learners get Spanish UI and Spanish explanations. English ("hard mode") gives everything in English for advanced students.

## Components Updated

All user-visible text has been internationalized:

### Core Components
- `App.tsx` - Header, welcome screen, language dropdown
- `LoginButton.tsx` - Sign in button
- `UserProfile.tsx` - Sign out button

### Navigation
- `LessonList.tsx` - Loading state
- `LessonSections.tsx` - Section titles (Principle, Goals, Vocabulary, Practice)

### Conversation
- `ConversationDrawer.tsx` - Transcript button, drawer title
- `ConversationView.tsx` - Empty state, "Thinking..." indicator
- `MessageBubble.tsx` - Agent names (Teacher, Demo, Partner)
- `VoiceButton.tsx` - Accessibility labels

### Content Views
- `ContentWindow.tsx` - Empty state prompts
- `GoalsView.tsx` - Progress labels, "I can:" header
- `PrincipleView.tsx` - "Ponder" section header
- `VocabularyView.tsx` - Empty state
- `PracticeView.tsx` - Intro banner, skip button, start conversation
- `PatternsView.tsx` - Pattern labels, practice buttons, examples header
- `DemoPlayer.tsx` - All control buttons (Repeat, Next, Questions, Finished)

### Utility
- `LessonMaterialPanel.tsx` - Section headers
- `AuthenticatedImage.tsx` - Loading/error states

## Adding a New Language

### Step 1: Create the translation file

Copy `en.json` and translate all values:

```bash
cp src/frontend/src/locales/en.json src/frontend/src/locales/fr.json
```

Edit `fr.json`:
```json
{
  "app": {
    "title": "EnglishConnect",
    "signInPrompt": "Connectez-vous pour pratiquer l'anglais",
    "language": "Langue",
    ...
  }
}
```

### Step 2: Register in i18n.ts

```typescript
import en from './locales/en.json';
import es from './locales/es.json';
import fr from './locales/fr.json';  // Add import

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    es: { translation: es },
    fr: { translation: fr }  // Add to resources
  },
  // ...
});
```

### Step 3: Add dropdown option

In `App.tsx`, add the new option to the language dropdown:

```tsx
<select value={instructionLanguage} onChange={...}>
  <option value="es">Español</option>
  <option value="en">English</option>
  <option value="fr">Français</option>  {/* Add this */}
</select>
```

### Step 4: Update TypeScript types (if needed)

If the codebase uses strict typing for language codes, update the type:

```typescript
// In stores/conversationStore.ts or types/index.ts
type InstructionLanguage = 'en' | 'es' | 'fr';
```

## Translation Keys Reference

### Namespace: `app`
- `title` - Application name
- `signInPrompt` - Login page subtitle
- `lessonsSubtitle` - Sidebar subtitle
- `welcome` - Welcome header
- `selectLessonPrompt` - Welcome subtitle
- `language` - Language dropdown label
- `loading` - Loading indicator

### Namespace: `auth`
- `signIn` - Sign in button
- `signingIn` - Loading state
- `signOut` - Sign out button

### Namespace: `lessons`
- `loading` - Loading lessons
- `sections` - Sections header
- `selectToView` - No lesson selected
- `selectLesson` - Select prompt
- `selectLessonHint` - Select hint

### Namespace: `sections`
- `principle` - Learning Principle
- `goals` - Learning Goals
- `vocabulary` - Vocabulary
- `practice` - Practice
- `patterns` - Patterns

### Namespace: `conversation`
- `transcript` / `hide` - Drawer toggle
- `title` - Drawer header
- `placeholder` - Input placeholder
- `selectFirst` - No lesson selected
- `clearTitle` - Clear button tooltip
- `emptyState` - No messages
- `thinking` - AI thinking

### Namespace: `agents`
- `teacher` / `demo` / `partner` - Agent names
- `switchedTo*` - Agent switch labels

### Namespace: `voice`
- `startRecording` / `stopRecording` - Accessibility

### Namespace: `goals`
- `empty` - No goals
- `progress` - Progress label
- `completed` - Progress count (uses interpolation)
- `iCan` - Goals header

### Namespace: `principle`
- `empty` - No principle
- `ponder` - Ponder section

### Namespace: `vocabulary`
- `empty` - No vocabulary

### Namespace: `practice`
- `empty` - No content
- `playingIntro` - Intro banner
- `skip` - Skip button
- `startConversation` - Start button

### Namespace: `patterns`
- `empty` - No patterns
- `pattern` - Pattern label (uses interpolation: `{{number}}`)
- `practice` / `practicing` - Practice button states
- `examples` - Examples header

### Namespace: `demo`
- `listen` / `listenSubtitle` - Demo player labels
- `example` / `examples` - Count labels
- `repeat` / `next` / `questions` / `finished` - Control buttons

### Namespace: `image`
- `unavailable` - Error state
- `loading` - Loading state

## Best Practices

1. **Use descriptive keys**: `goals.completed` not `g.c`
2. **Group by feature**: All conversation-related keys under `conversation`
3. **Use interpolation**: `{{count}} items` not separate singular/plural keys
4. **Keep English as fallback**: Missing keys show English, not errors
5. **Test both languages**: Some text expands significantly in Spanish
