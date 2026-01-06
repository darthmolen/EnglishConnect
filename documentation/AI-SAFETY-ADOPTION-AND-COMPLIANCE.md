# AI Safety Adoption and Compliance

This document outlines how EnglishConnect aligns with industry AI safety standards and frameworks, including ISO/IEC 42001, NIST AI RMF, and EU AI Act principles.

## Compliance Summary

| Framework | Status | Mechanism |
|-----------|--------|-----------|
| **ISO/IEC 42001** | Inherited | Azure AI Foundry (certified) |
| **NIST AI RMF** | Aligned | Risk-based controls |
| **EU AI Act** | Limited Risk | Transparency + data protection |
| **OWASP LLM Top 10** | Mitigated | Prompt injection guards, output validation |

## Azure AI Platform Compliance

EnglishConnect uses **Azure AI Foundry** (Azure OpenAI) as its LLM provider, which provides ISO/IEC 42001:2023 certification out of the box.

### What This Means

> "Customers using Microsoft's Azure AI Foundry Models are assured that Microsoft's solutions feature robust governance, risk management, and compliance practices."
> — [Microsoft Azure Blog](https://azure.microsoft.com/en-us/blog/microsoft-azure-ai-foundry-models-and-microsoft-security-copilot-achieve-iso-iec-420012023-certification/)

Azure AI Foundry certification covers:
- **Govern**: Policy frameworks embedded in design
- **Map**: Risk mapping throughout AI lifecycle
- **Measure**: Technical performance and ethical alignment
- **Manage**: Ongoing risk management processes

### Inherited Compliance

By building on Azure AI Foundry, EnglishConnect inherits:
- ISO/IEC 42001:2023 (AI Management System)
- SOC 2 Type II
- GDPR compliance infrastructure
- Content filtering and safety systems
- Responsible AI monitoring

**Reference**: [Microsoft ISO/IEC 42001 Compliance](https://learn.microsoft.com/en-us/compliance/regulatory/offering-iso-42001)

### Azure AI Content Safety (Defense in Depth)

Azure OpenAI includes **built-in content filtering** that operates independently of application prompts. This provides a critical safety net.

#### Default Risk Category Filters

Azure AI Foundry applies these filters at **Medium severity threshold** by default:

| Category | Input Filter | Output Filter | Severity |
|----------|-------------|---------------|----------|
| **Hate & Fairness** | ✓ | ✓ | Medium+ blocked |
| **Sexual** | ✓ | ✓ | Medium+ blocked |
| **Violence** | ✓ | ✓ | Medium+ blocked |
| **Self-Harm** | ✓ | ✓ | Medium+ blocked |

**Severity Levels**: Low → Medium → High. Medium threshold blocks Medium and High severity content while allowing Low severity (educational/informational context).

#### Prompt Shield (Jailbreak Detection)

| Protection | Applied To | Behavior |
|------------|-----------|----------|
| **User prompt attacks** | Input | Detects attempts to manipulate model behavior |
| **Document attacks** | Input | Detects malicious content in retrieved documents |

When jailbreak attempts are detected, the request is blocked before reaching the model.

#### Protected Material Detection

| Type | Protection |
|------|------------|
| **Text** | Blocks verbatim reproduction of copyrighted text |
| **Code** | Detects code from public repositories (with license info) |

#### How It Works

```
User Input → [Prompt Shield] → [Input Filters] → Model → [Output Filters] → Response
                   ↓                 ↓                          ↓
            Blocks jailbreaks   Blocks harmful          Blocks harmful
                                   input                   output
```

**Key Benefit**: Even if application-level prompts miss something, Azure's guardrails catch it at the model layer. This is **defense in depth** - multiple layers of protection.

**References**:

- [Content Safety Overview](https://learn.microsoft.com/en-us/azure/ai-foundry/ai-services/content-safety-overview)
- [Default Safety Policies](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/default-safety-policies)
- [Azure AI Content Safety](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/)

## Application-Level Safety Controls

Beyond platform-level compliance, EnglishConnect implements additional safety measures:

### 1. PII Protection (CRITICAL)

**Location**: `src/backend/app/prompts/agent/base.md`

The agent is explicitly prohibited from collecting or storing personally identifiable information:

```
CRITICAL: PII PROTECTION
You must NEVER ask for, store, or repeat back:
- Email addresses
- Phone numbers
- Physical addresses
- Social Security numbers
- Driver's license numbers
- ID numbers (passport, national ID, etc.)

If a student volunteers contact information, politely redirect:
"Thanks, but I don't need that information. Let's practice something else!"
```

**Allowed Exception**: First names only (for introduction practice scenarios)

### 2. Persona Consistency & Truthfulness

**Location**: `src/backend/app/prompts/agent/mode_practice.md`

The agent maintains honesty about its AI nature:

```
When students ask personal questions, REDIRECT to them:
- "Tell me about YOUR family" → "I'm an AI, so I don't have family.
  But tell me about YOUR family!"

NEVER invent personal details. You are a tutor, not a person.
```

**Alignment**: ISO 42001 Transparency requirements, EU AI Act Article 52

### 3. Confusion Recovery & Input Validation

**Location**: `src/backend/app/prompts/agent/base.md`

Three-tier validation prevents misinterpretation:

| Input Type | Agent Behavior |
|------------|----------------|
| Ambiguous | Ask for clarification |
| Garbled but clear intent | Proceed with understood meaning |
| Incoherent | Request re-statement |

**Phonetic Awareness**: Special handling for homophones (marry/Mary, their/there/they're) common in language learning contexts.

### 4. Curriculum Alignment & Scope Control

**Location**: `src/backend/app/prompts/agent/mode_help.md`

The agent operates within defined educational boundaries:
- Vocabulary limited to current + previous lessons
- Out-of-scope words acknowledged as such
- No improvisation beyond curriculum

**Alignment**: NIST AI RMF "Constrained Output" principle

### 5. Output Cleanliness

Enforced through automated LLM-as-Judge evaluation:
- No markdown syntax in spoken text
- No URLs leaked to audio output
- Clean formatting for TTS synthesis

**Pass Rate**: 100% (ADR-006)

### 6. Authentication & User Isolation

**Location**: `src/backend/app/middleware/auth.py`

- Azure AD token validation on all API requests
- User ID tracking for conversation isolation
- JWT validation with issuer/audience verification
- Per-request database session isolation

## Automated Safety Evaluation

EnglishConnect implements continuous safety monitoring via LLM-as-Judge evaluation (ADR-006):

| Dimension | Description | Current Pass Rate |
|-----------|-------------|-------------------|
| **language_choice** | Correct language selection | 70% |
| **tool_usage** | Proper tool invocation | 83% |
| **output_cleanliness** | No markdown/URLs in speech | 100% |
| **confusion_recovery** | Graceful handling of unclear input | 75% |
| **persona_consistency** | AI identity maintained | 100% |
| **curriculum_alignment** | Within lesson scope | 50% |

**Reference**: `documentation/ADR/ADR-006-AGENT-RESPONSE-QUALITY.md`

## Risk Classification

Under the **EU AI Act**, EnglishConnect qualifies as **Limited Risk**:

| Criteria | EnglishConnect Status |
|----------|----------------------|
| Interacts with humans | Yes - disclosed as AI |
| Generates content | Yes - educational only |
| High-risk category | No - not in Annex III |
| Biometric identification | No |
| Critical infrastructure | No |

### Required Transparency Measures (Implemented)

1. **AI Disclosure**: Agent identifies as AI when asked
2. **Purpose Limitation**: Educational use only
3. **Data Minimization**: No PII collection
4. **User Control**: Clear session boundaries

## OWASP LLM Top 10 Mitigations

| Risk | Mitigation |
|------|------------|
| **LLM01: Prompt Injection** | System prompts isolated, user input treated as data |
| **LLM02: Insecure Output** | Output validation, no code execution |
| **LLM03: Training Data Poisoning** | Using Azure's curated models |
| **LLM06: Sensitive Info Disclosure** | PII guards in prompts |
| **LLM07: Insecure Plugin Design** | Tool handlers validate all parameters |
| **LLM09: Overreliance** | Educational context, human oversight expected |

## Data Handling Practices

### What We Collect

| Data Type | Purpose | Retention |
|-----------|---------|-----------|
| Conversation history | Session continuity | Session-scoped |
| Learning progress | Track mastery | Persistent (user-linked) |
| Audio (STT input) | Speech-to-text | Not stored |
| Audio (TTS output) | Streamed to client | Not stored |

### What We Don't Collect

- Email addresses
- Phone numbers
- Physical addresses
- Government IDs
- Payment information
- Biometric data (beyond voice for STT)

## Compliance Roadmap

### Currently Implemented

- [x] PII protection in prompts
- [x] AI transparency (persona consistency)
- [x] Azure AI Foundry (ISO 42001)
- [x] Authentication & authorization
- [x] Automated safety evaluation
- [x] Output validation

### Future Enhancements

- [ ] Rate limiting on API endpoints
- [ ] Explicit content filtering for student input
- [ ] Data retention policy automation
- [ ] Audit logging for compliance reporting
- [ ] GDPR data export/deletion endpoints
- [ ] Accessibility compliance (WCAG 2.1)

## References

### Standards & Frameworks

- [ISO/IEC 42001:2023](https://www.iso.org/standard/81230.html) - AI Management System
- [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) - Risk Management Framework
- [EU AI Act](https://artificialintelligenceact.eu/) - European AI Regulation
- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

### Azure Compliance

- [Azure AI ISO 42001 Certification](https://azure.microsoft.com/en-us/blog/microsoft-azure-ai-foundry-models-and-microsoft-security-copilot-achieve-iso-iec-420012023-certification/)
- [Microsoft Compliance Offerings](https://learn.microsoft.com/en-us/compliance/regulatory/offering-iso-42001)
- [Azure Service Trust Portal](https://servicetrust.microsoft.com/)

### Internal Documentation

- `documentation/ADR/ADR-006-AGENT-RESPONSE-QUALITY.md` - Safety evaluation framework
- `src/backend/app/prompts/agent/base.md` - PII protection rules
- `src/backend/app/prompts/agent/mode_practice.md` - Persona guidelines

---
*Last updated: January 2025*
*This document should be reviewed quarterly and updated as standards evolve.*
