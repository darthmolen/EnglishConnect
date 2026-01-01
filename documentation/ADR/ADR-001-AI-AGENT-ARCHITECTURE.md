# ADR-001: AI Agent Architecture

**Status**: Retired (Superseded by ADR-005)
**Date**: 2025-12-12
**Decision Makers**: Project Team

## Context

EnglishConnect is a voice-based English learning application for Spanish speakers. The system requires:
- Real-time voice conversation with low latency (~1.5-2s end-to-end)
- Multilingual support (Spanish/English)
- Agent capabilities for lesson guidance and feedback
- Cost-effective LLM usage (leveraging free Azure credits)

Originally, the project planned to use Claude API (Anthropic) for LLM capabilities. However, we have free credits on Microsoft Azure AI Foundry and want to leverage Microsoft's agent tooling ecosystem.

## Decision

### 1. Primary LLM: GPT-4o-mini via Azure AI Foundry

**Rationale**:
- Cost-effective (~$0.15/M input, $0.60/M output)
- Strong multilingual performance (Spanish/English)
- Available on Azure AI Foundry where we have free credits
- Upgrade path to GPT-4o when needed

### 2. Real-time Voice Loop: Local Agents (Microsoft Agent Framework)

**Rationale**:
- Latency-sensitive: network round-trips to Azure AI Agent Service would add ~100-300ms
- Voice conversation targets ~1.5-2s end-to-end latency
- Microsoft Agent Framework runs in-process, minimizing latency
- Direct Azure OpenAI calls for fastest response

**Implementation**:
```python
from agent_framework import ChatAgent
# Local agent with direct Azure OpenAI connection
```

### 3. Non-realtime Tasks: Azure AI Agent Service ("Existing Agents")

**Rationale**:
- Nice UI for prompt engineering and iteration
- Built-in evaluation framework
- Agent persistence (reusable by ID)
- Grounding services (Bing, Azure AI Search)
- Good for: lesson planning, progress analysis, feedback generation

**Implementation**:
```python
from agent_framework.azure import AzureAIAgentClient
# Reference pre-configured agents by ID
chat_client = AzureAIAgentClient(agents_client=agents_client, agent_id="...")
```

### 4. Keep STT/TTS Local

**Rationale**:
- faster-whisper (STT) and VibeVoice (TTS) already optimized for local GPU
- No licensing cost
- Lower latency than cloud alternatives
- Privacy: voice data processed locally

## Consequences

### Positive
- Free Azure credits cover LLM costs during development
- Flexible architecture: local for speed, cloud for features
- Microsoft Agent Framework supports MCP (already used by project)
- Clear upgrade path (GPT-4o-mini → GPT-4o)

### Negative
- Two agent patterns to maintain (local + Azure AI Agent Service)
- Azure vendor lock-in for cloud agents
- Need to manage Azure AI Foundry project/deployment

### Neutral
- Backend dependencies change from `anthropic` to `agent-framework` + `azure-*`
- Documentation updates required

## Alternatives Considered

1. **Claude API (original plan)**: Good quality but no free credits, different ecosystem
2. **Mistral Large 2**: Competitive pricing ($2/$6 per M tokens) but GPT-4o-mini is cheaper for our use case
3. **Fully local agents only**: Would lose Azure AI Agent Service's UI/eval tooling
4. **Fully cloud agents only**: Latency concerns for real-time voice

## References

- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [Azure AI Agent Service](https://learn.microsoft.com/en-us/azure/ai-services/agents/)
- [GPT-4o-mini](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models)
