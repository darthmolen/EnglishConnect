# Phase 2B: Testing Infrastructure & VibeVoice Recovery

**Status**: ✅ Complete
**Duration**: 1 session
**Goal**: Establish TDD infrastructure and recover voice stack after directory reorganization

## Summary

Phase 2B addressed critical infrastructure needs before Phase 3 development:
1. Reorganized codebase to standard structure (`src/`, `tests/`, `docs/`, `planning/`)
2. Established comprehensive test infrastructure with pytest
3. Recovered VibeVoice TTS service after directory moves broke venvs
4. Achieved full GPU-accelerated voice pipeline (STT + TTS with flash-attn)

## Directory Reorganization

### Before
```
backend/
services/
  stt/
  tts-mcp/
  content-mcp/
tools/
content/ec1/
raw/ec1/
```

### After
```
src/
  backend/
  services/
    stt/
    tts-mcp/
    content-mcp/
  tools/
content/
  refined/ec1/
  raw/ec1/
tests/
  unit/
  integration/
  e2e/
documentation/
planning/
  completed/
  in_progress/
  backlog/
```

## Test Infrastructure Created

### Test Structure
```
tests/
├── conftest.py              # Project-wide fixtures, path setup
├── unit/                    # 43 tests (no services required)
│   ├── test_lesson_parser.py  # 24 tests - content parsing
│   └── test_vad.py            # 19 tests - voice activity detection
├── integration/             # 35 tests (require services)
│   ├── conftest.py           # Skip tests when DB unavailable
│   ├── test_content_mcp.py   # 25 tests - content MCP tools
│   ├── test_stt_service.py   # 10 tests - STT HTTP/WebSocket
│   └── test_tts_service.py   # 14 tests - TTS MCP tools
└── e2e/                     # Placeholder for Phase 3
    ├── conftest.py           # Skip when frontend not running
    └── test_placeholder.py   # Test stubs
```

### Test Results
- **88 tests passing**
- **4 skipped** (require VibeVoice in test venv)
- Tests auto-skip when services unavailable

### Running Tests
```bash
# All tests
.venv-test/bin/pytest tests/

# Unit only (fast, no services)
.venv-test/bin/pytest tests/unit/

# Integration (requires services)
.venv-test/bin/pytest tests/integration/
```

## VibeVoice Recovery

### Problem
Directory reorganization broke Python virtual environments due to hardcoded shebang paths. Venvs had to be recreated, which caused dependency mismatches.

### Solution Journey
1. Deleted stale venvs with hardcoded paths
2. Recreated venvs via `start.sh`
3. Reinstalled VibeVoice from GitHub
4. **flash-attn compilation battle**:
   - Downloaded CUDA 12.8 toolkit
   - Compiled flash-attn against CUDA 12.8
   - Compiled for PyTorch 2.9.x only
   - Increased WSL memory: 16GB → 48GB RAM + 32GB swap
   - Clean compile achieved

### Final Stack
| Component | Version | Status |
|-----------|---------|--------|
| PyTorch | 2.9.1+cu128 | Working |
| CUDA | 12.8 | Working |
| flash-attn | 2.x (compiled) | Working |
| VibeVoice | 0.5B-Realtime | Working |
| faster-whisper | medium | Working |

## Configuration Updates

### Files Modified
- `start.sh` - Updated all paths to `src/` structure
- `stop.sh` - Updated pkill patterns
- `CLAUDE.md` - Complete rewrite with new structure
- `pytest.ini` - Added markers for integration, e2e
- `.vscode/settings.json` - Set test interpreter
- `tests/conftest.py` - Path setup for imports

### Key Fixes
- Module import conflicts between TTS and Content MCP servers (both named `server.py`)
- Integration tests skip gracefully when PostgreSQL not running
- VSCode test explorer configured with `.venv-test`

## Voice Stack Performance

| Service | Model | Latency | Status |
|---------|-------|---------|--------|
| STT | Whisper medium (CUDA) | ~800ms/5s | Running |
| TTS | VibeVoice (flash-attn) | ~300ms TTFA | Running |
| VAD | Silero | ~0ms | Ready |

## Lessons Learned

1. **Venv paths are fragile** - Moving directories breaks Python venvs due to hardcoded shebangs
2. **flash-attn is picky** - Requires exact CUDA version match with PyTorch
3. **WSL memory matters** - Model compilation needs substantial RAM (48GB helped)
4. **Test isolation is key** - Module name conflicts require explicit import handling

## Files Created

- `tests/unit/test_vad.py` - 19 VAD unit tests
- `tests/integration/test_stt_service.py` - 10 STT tests
- `tests/integration/test_tts_service.py` - 14 TTS tests
- `tests/integration/conftest.py` - DB availability check
- `tests/e2e/conftest.py` - Frontend availability check
- `tests/e2e/test_placeholder.py` - E2E test stubs

## Next Steps

Phase 3: React SPA Conversation Partner
- Frontend: Vite + React + TypeScript + shadcn/ui
- Voice conversation via WebSocket
- Lesson selection and progression
