# EnglishConnect 1 - Azure Cost Estimates

This document provides cost estimates for running EnglishConnect 1 on Azure infrastructure with cloud-based AI services.

## Per-Lesson API Costs

Based on test simulation of Lesson 7 (11 exchanges: 6 help mode + 5 practice mode):

| Component | Usage | Cost |
|-----------|-------|------|
| **LLM** (GPT-4o-mini) | ~147k tokens | $0.023 |
| **TTS** (GPT-4o-mini-realtime) | ~74s audio output | $0.147 |
| **STT** (GPT-4o-mini-realtime) | ~28s audio input | $0.028 |
| **Per Lesson Total** | | **~$0.20** |

### Realistic Range

With overhead for retries, confusion recovery, and extended practice:
- **Optimistic**: $0.20/lesson
- **Typical**: $0.35/lesson
- **Pessimistic**: $0.50/lesson

### Per-Course Cost (EnglishConnect 1 = 25 lessons)

| Scenario | Per Student |
|----------|-------------|
| Optimistic | $5.00 |
| Typical | $8.75 |
| Pessimistic | $12.50 |

### API Cost at Scale

| Students | Optimistic | Typical | Pessimistic |
|----------|------------|---------|-------------|
| 100 | $500 | $875 | $1,250 |
| 1,000 | $5,000 | $8,750 | $12,500 |
| 10,000 | $50,000 | $87,500 | $125,000 |

## Azure Infrastructure Costs (Monthly)

### Minimum Viable Infrastructure

| Service | SKU | Monthly Cost | Notes |
|---------|-----|--------------|-------|
| **PostgreSQL Flexible Server** | Burstable B1ms | ~$12.50 | 1 vCPU, 2 GiB RAM, 32 GB storage |
| **Azure Cache for Redis** | Basic C0 | ~$16.00 | 250 MB, retiring 2028 |
| **Azure Container Apps** | Consumption | ~$0-20 | Pay-per-use, 180k vCPU-s free |
| **Total Infrastructure** | | **~$30-50/month** | |

### Notes on Infrastructure

**PostgreSQL Flexible Server** ([Pricing](https://azure.microsoft.com/en-us/pricing/details/postgresql/flexible-server/))
- B1ms is the smallest burstable tier
- Stop/Start capability - only pay for storage when stopped
- Free tier available: 750 hours/month for 12 months

**Azure Cache for Redis** ([Pricing](https://azure.microsoft.com/en-us/pricing/details/cache/))
- Basic C0 (250MB) is cheapest at ~$16/month
- **Retiring September 2028** - migrate to Azure Managed Redis
- Azure Managed Redis starts at ~$173/month (Memory Optimized M10)
- Consider: serverless Redis alternatives or in-memory caching for MVP

**Azure Container Apps** ([Pricing](https://azure.microsoft.com/en-us/pricing/details/container-apps/))
- Consumption plan with generous free tier:
  - 180,000 vCPU-seconds free
  - 360,000 GiB-seconds free
  - 2 million requests free
- Scale to zero when idle (no cost)
- Active rate: ~$0.000024/vCPU-second

## Total Monthly Cost Projections

### Low Usage (100 students completing course over 3 months)

| Category | Monthly Cost |
|----------|--------------|
| Infrastructure | $40 |
| API costs (~33 students/month × $8.75) | $290 |
| **Total** | **~$330/month** |

### Medium Usage (1,000 students over 3 months)

| Category | Monthly Cost |
|----------|--------------|
| Infrastructure | $50 |
| API costs (~333 students/month × $8.75) | $2,915 |
| **Total** | **~$3,000/month** |

### High Usage (10,000 students over 3 months)

| Category | Monthly Cost |
|----------|--------------|
| Infrastructure (scaled) | $200 |
| API costs (~3,333 students/month × $8.75) | $29,165 |
| **Total** | **~$29,400/month** |

## Cost Breakdown Analysis

At typical usage, API costs dominate:
- **Audio (TTS/STT)**: ~88% of API cost
- **LLM**: ~12% of API cost

Infrastructure is negligible at scale (<1% of total cost).

## Cost Optimization Opportunities

### Immediate (No code changes)
1. **Azure Reserved Instances** - 1-year commitment for 30-40% savings on PostgreSQL
2. **Stop non-prod databases** - Only pay for storage when stopped

### Medium-term
1. **Prompt compression** - Reduce system prompt tokens (currently ~8k per exchange)
2. **Conversation summarization** - Compress history instead of full replay
3. **Response caching** - Pre-generate common vocabulary explanations

### Long-term
1. **Azure OpenAI commitment tiers** - Volume discounts at scale
2. **Regional pricing** - Some regions have lower costs
3. **Model optimization** - Fine-tuned smaller models for specific tasks

## Pricing Sources

- [Azure PostgreSQL Flexible Server](https://azure.microsoft.com/en-us/pricing/details/postgresql/flexible-server/)
- [Azure Cache for Redis](https://azure.microsoft.com/en-us/pricing/details/cache/)
- [Azure Managed Redis](https://azure.microsoft.com/en-us/pricing/details/managed-redis/)
- [Azure Container Apps](https://azure.microsoft.com/en-us/pricing/details/container-apps/)
- [OpenAI API Pricing](https://openai.com/api/pricing/)
- [GPT-4o-mini Realtime](https://platform.openai.com/docs/models/gpt-4o-mini-realtime-preview)

## Test Methodology

Cost estimates derived from `tests/integration/test_lesson_token_usage.py` which simulates:
1. Help mode: 6 vocabulary/pattern questions in Spanish
2. Practice mode: 5 conversation exchanges until role flip

Run the test to regenerate estimates:
```bash
source src/backend/.venv/bin/activate
python -m pytest tests/integration/test_lesson_token_usage.py -v -s
```

---
*Last updated: January 2025*
*Prices are estimates and may vary by region and agreement type.*
