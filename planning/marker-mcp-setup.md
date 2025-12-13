# Plan: Marker MCP Server with Code Executor Skill

## Goal

Set up PDF→Markdown conversion for Spanish EnglishConnect curriculum using:

1. **marker MCP server** - High-quality PDF conversion
2. **cc-mcp-executor-skill** - 98% token reduction via subagent architecture

## File Locations

- **Input PDFs**: `raw/`
- **Output markdown**: `content/` (parallel folder structure)

## Architecture

```
Main Claude Code (clean context, ~1,600 tokens)
    ↓ Task Tool
Subagent (loads marker MCP, processes PDFs)
    ↓ Returns summary
Main context receives results without token bloat
```

## Part 1: Install Code Executor Skill

### 1.1 Clone the skill

```bash
git clone https://github.com/mcfearsome/cc-mcp-executor-skill.git ~/.claude/skills/code-executor
```

### 1.2 Install Deno (for TypeScript execution)

```bash
# DONE - already installed
curl -fsSL https://deno.land/install.sh | sh
```

## Part 2: Create Marker MCP Server

### 2.1 Create `/home/smolen/dev/EnglishConnect/tools/marker_mcp/server.py`

Python MCP server using `mcp` SDK:

- `convert_pdf(file_path, output_dir)` - Convert single PDF
- `batch_convert(input_dir, output_dir)` - Convert all PDFs in directory
- Writes markdown + images to output_dir, returns summary (not full content)

### 2.2 Create `/home/smolen/dev/EnglishConnect/tools/marker_mcp/requirements.txt`

```
mcp
marker-pdf
```

## Part 3: Configure Subagent MCP

### 3.1 Create `~/.claude/subagent-mcp.json`

```json
{
  "mcpServers": {
    "marker": {
      "command": "python",
      "args": ["/home/smolen/dev/EnglishConnect/tools/marker_mcp/server.py"]
    }
  }
}
```

**Note:** This is NOT loaded into main Claude Code - only subagents use it.

## Part 4: Fallback Option

If marker has issues, add markitdown to subagent config:

```bash
pip install markitdown-mcp-server
```

```json
{
  "mcpServers": {
    "marker": { "..." },
    "markitdown": {
      "command": "markitdown-mcp-server"
    }
  }
}
```

## Implementation Steps

1. [x] Install Deno
2. [x] Clone cc-mcp-executor-skill to `~/.claude/skills/code-executor/`
3. [x] Create `tools/marker_mcp/` directory
4. [x] Write `server.py` with MCP tools
5. [x] Write `requirements.txt` and install deps (using venv)
6. [x] Create `~/.claude/subagent-mcp.json` with marker server config
7. [x] Test: Convert sample PDF (ec1-lesson-1-slides.pdf → markdown)

## Reference Links

- cc-mcp-executor-skill: https://github.com/mcfearsome/cc-mcp-executor-skill
- marker: https://github.com/VikParuchuri/marker
- markitdown-mcp-server (fallback): https://pypi.org/project/markitdown-mcp-server/
