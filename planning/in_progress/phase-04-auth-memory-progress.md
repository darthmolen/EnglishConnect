# Phase 4: Auth + Memory + Progress Tracking

**Status**: 🔄 In Progress (Phase 4A Complete)
**Goal**: User authentication, conversation memory, and progress tracking

## Phase Split

- **Phase 4A** ✅ Memori integration + Progress tracking API
- **Phase 4B** 🔜 Azure Entra ID authentication (Microsoft + Google)

## Overview

Add user authentication via Microsoft Identity Platform (supporting both Microsoft and Google accounts), implement conversation memory using Memori with PostgreSQL, and build progress tracking for lesson completion.

## Tech Stack Additions

| Component | Technology |
|-----------|------------|
| Auth | Microsoft Identity Platform (Entra ID) |
| Auth Library | MSAL (Microsoft Authentication Library) |
| JWT Validation | python-jose |
| Memory | Memori (open-source, PostgreSQL-backed) |
| Database | PostgreSQL (existing) |

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         React SPA (localhost:5173)                       │
│                                                                          │
│  ┌──────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │ Login Button │    │  User Profile   │    │   Progress Dashboard    │  │
│  │ (MS/Google)  │    │  (avatar/name)  │    │   (lesson completion)   │  │
│  └──────┬───────┘    └────────┬────────┘    └───────────┬─────────────┘  │
│         │                     │                         │                │
│         └─────────────────────┼─────────────────────────┘                │
│                               │                                          │
│                    ┌──────────▼──────────┐                               │
│                    │  Auth Context/Store │                               │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   Backend API   │
                    │                 │
                    │ - JWT Validation│
                    │ - User Context  │
                    │ - Memori Memory │
                    │ - Progress API  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌──────────┐  ┌───────────┐  ┌───────────┐
        │ Entra ID │  │ PostgreSQL│  │   Redis   │
        │ (OAuth)  │  │ (memory,  │  │ (sessions)│
        │          │  │  progress)│  │           │
        └──────────┘  └───────────┘  └───────────┘
```

## Tasks

### 4.1 Microsoft Identity Platform Setup

- [ ] Register app in Azure Entra ID (App Registration)
- [ ] Configure redirect URIs for local dev and production
- [ ] Add Google as external identity provider
- [ ] Set up API permissions (User.Read)
- [ ] Generate client credentials

### 4.2 Backend Auth Integration

- [ ] Install dependencies: `msal`, `python-jose`, `httpx`
- [ ] Create auth middleware for JWT validation
- [ ] Create `/api/auth/login` endpoint (redirect to Entra)
- [ ] Create `/api/auth/callback` endpoint (handle OAuth callback)
- [ ] Create `/api/auth/me` endpoint (get current user)
- [ ] Create `/api/auth/logout` endpoint
- [ ] Add user model to database (id, email, name, avatar_url, provider)
- [ ] Create or update user on first login

### 4.3 Frontend Auth Integration

- [ ] Install MSAL React: `@azure/msal-react`, `@azure/msal-browser`
- [ ] Create MSAL configuration
- [ ] Add MsalProvider to App
- [ ] Create LoginButton component (Microsoft + Google options)
- [ ] Create UserProfile component (avatar, name, logout)
- [ ] Add auth state to Zustand store
- [ ] Protect conversation routes (require auth)

### 4.4 Memori Integration (Conversation Memory) ✅

- [x] Install Memori: `pip install memorisdk`
- [x] Configure Memori with PostgreSQL connection (psycopg2)
- [x] Configure Azure OpenAI compatibility endpoint for Memori
- [x] Create memory tables via Memori migrations
- [x] Integrate Memori into conversation agent (azure_openai.py)
- [x] Store conversation turns with user context (user_id attribution)
- [x] Enable cross-session memory recall

### 4.5 Progress Tracking ✅

- [x] Create database models (using existing models/progress.py):
  - `UserProgress` (user_id, lesson_id, status, started_at, completed_at)
  - `PracticeSession` (user_id, lesson_id, started_at, ended_at, duration)
  - `ConversationExchange` (session_id, agent/user utterances, timestamp)
- [x] Create session_service.py for recording conversation exchanges
- [x] Create API endpoints (routers/progress.py):
  - `GET /api/progress` - user's overall progress
  - `GET /api/progress/lessons` - lesson completion status
  - `POST /api/progress/lessons/{id}/start` - mark lesson started
  - `POST /api/progress/lessons/{id}/complete` - mark lesson complete
  - `GET /api/progress/stats` - conversation stats
- [ ] Update frontend to show progress indicators on lesson cards (Phase 4B)

### 4.6 Testing

- [ ] Unit tests for auth middleware (Phase 4B)
- [ ] Integration tests for OAuth flow (Phase 4B)
- [ ] Unit tests for Memori integration
- [ ] Unit tests for progress tracking endpoints

## Database Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    avatar_url TEXT,
    provider VARCHAR(50) NOT NULL,  -- 'microsoft' or 'google'
    provider_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- User progress per lesson
CREATE TABLE user_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    lesson_id INTEGER REFERENCES lessons(id),
    status VARCHAR(20) DEFAULT 'not_started',  -- not_started, in_progress, completed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(user_id, lesson_id)
);

-- Conversation sessions
CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    lesson_id INTEGER REFERENCES lessons(id),
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    turn_count INTEGER DEFAULT 0,
    quality_score FLOAT  -- optional: AI-evaluated quality
);

-- Feedback history (pronunciation, grammar corrections)
CREATE TABLE feedback_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES conversation_sessions(id),
    feedback_type VARCHAR(50),  -- 'pronunciation', 'grammar', 'vocabulary'
    user_input TEXT,
    correction TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Environment Variables

```bash
# Microsoft Identity Platform
AZURE_AD_CLIENT_ID=your-client-id
AZURE_AD_CLIENT_SECRET=your-client-secret
AZURE_AD_TENANT_ID=your-tenant-id
AZURE_AD_REDIRECT_URI=http://localhost:8000/api/auth/callback

# Memori (uses existing PostgreSQL)
MEMORI_DATABASE_URL=${DATABASE_URL}
```

## Success Criteria

- [ ] Users can sign in with Microsoft account
- [ ] Users can sign in with Google account
- [ ] JWT tokens validated on protected endpoints
- [ ] User profile displayed in UI
- [ ] Conversation history persisted per user
- [ ] Agent recalls context from previous sessions
- [ ] Lesson progress tracked and displayed
- [ ] Conversation sessions recorded with metrics

## Non-Goals (Phase 4)

- Email/password authentication (use social only)
- Admin dashboard
- User roles/permissions
- Multi-tenancy

## References

- [Microsoft Identity Platform](https://learn.microsoft.com/en-us/entra/identity-platform/)
- [MSAL Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [MSAL React](https://github.com/AzureAD/microsoft-authentication-library-for-js)
- [Memori](https://github.com/matthewbergvinson/memori)
