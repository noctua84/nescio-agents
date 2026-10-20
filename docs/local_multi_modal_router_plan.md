# Local Multi-Model Router Architecture

## Overview

A self-learning, tiered routing system for local LLM inference that dynamically assigns tasks to models based on complexity, learns from outcomes, and optimizes for both speed and capability.

---

## Architecture Components

### 1. The Hybrid Semantic Router (B+C)

Combines embedding-based similarity matching with a tiny LLM for nuanced classification.

**How it works:**
1. User prompt arrives
2. Embed the prompt using `qwen3-embedding:0.6b`
3. Check semantic distance against reference library in database
4. **If confidence is high** (close match to known patterns): Use embedding result directly
5. **If confidence is low** (ambiguous or novel): Invoke `qwen3.5:0.8b` as classifier
6. Log the classification decision with metadata

**Why this works:**
- Embeddings are fast (~10-50ms) and capture semantic similarity
- The 0.8b model can reason about edge cases and nuance
- Database accumulates learned patterns over time

### 2. The Tiered Execution Layer

**Tier 1: Fast & Simple** → `qwen3.5:2b`
- Single-file edits, regex, boilerplate, simple explanations
- Target latency: < 1 second
- ~2.7GB VRAM

**Tier 2: Daily Driver** → `qwen3.5:9b` (RESIDENT)
- Multi-file reasoning, moderate debugging, standard coding tasks
- Target latency: 2-5 seconds
- ~6.6GB VRAM
- **Always loaded** for immediate response

**Tier 3: Heavy Lifting** → *On-demand* (pull when needed)
- Cross-repo refactoring, architecture decisions, complex debugging
- Examples: `qwen2.5-coder:14b`, `qwen3:14b`, or larger
- ~9-12GB VRAM
- Loaded only when explicitly needed

### 3. The Feedback Loop (Self-Learning Mechanism)

**Signal Sources:**

1. **Escalation as Negative Feedback**
   - Router labels task "simple" (Tier 1)
   - Tier 1 fails verification → escalates to Tier 2
   - System logs: original prompt, embedding, classification, escalation event
   - Future similar prompts get routed directly to Tier 2

2. **User Override as Ground Truth**
   - Manual tier selection (e.g., "force Tier 3")
   - Strongest learning signal
   - Updates reference library immediately

3. **Latency as Soft Signal**
   - If Tier 1 takes unusually long → task might be misclassified
   - Weak signal but useful for pattern detection

**Database Evolution:**
- **Reference Library**: Curated examples of simple/medium/complex tasks
- **Correction Log**: Every misclassification with context
- **Confidence Threshold**: Starts conservative, becomes more aggressive as accuracy improves

### 4. The Verification Layer

**Key Insight:** With Qwen/Nexus models, "I don't know" is a valid output.

**Verification checks:**
- Did the model attempt the task or defer?
- Is the deferral appropriate? (e.g., "I don't know this obscure API" = honest; "I don't know how to write a loop" = failure)
- If deferred: escalate to next tier
- If next tier also defers: surface honestly to user

**Simple verification script:**
- Check for explicit deferral phrases
- Check for syntax errors (if code output)
- Check for excessive hedging language

---

## Your Model Lineup & Assignments

| Model | Size | VRAM | Role | Notes |
|-------|------|------|------|-------|
| `qwen3-embedding:0.6b` | 639MB | ~0.7GB | **Semantic Router (B)** | Lightning-fast embeddings for similarity matching |
| `qwen3.5:0.8b` | 1.3GB | ~1.5GB | **Tiny LLM Classifier (C)** | Handles edge cases, updates database |
| `qwen3.5:2b` | 2.7GB | ~3GB | **Tier 1: Fast Tasks** | Quick responses for simple requests |
| `qwen3.5:9b` | 6.6GB | ~7GB | **Tier 2: Daily Driver** | Resident model, always loaded |
| *On-demand* | 9-12GB | ~10-13GB | **Tier 3: Complex Tasks** | Pull `qwen2.5-coder:14b` or similar when needed |

**Total VRAM for core system:** ~11.5GB (embedding + 0.8b + 2b + 9b)
**Your RTX 5070 (12GB):** Can run the entire core system with minimal headroom

---

## VRAM Management Strategy

### Default State (Fast Mode)
- **Loaded:** `qwen3-embedding:0.6b` + `qwen3.5:0.8b` + `qwen3.5:2b` + `qwen3.5:9b`
- **Total:** ~11.5GB
- **Use case:** Most tasks, immediate response

### Heavy Mode (When Tier 3 needed)
- **Unload:** `qwen3.5:2b` (Tier 1)
- **Load:** Tier 3 model (e.g., `qwen2.5-coder:14b`)
- **Total:** ~11.8GB
- **Trade-off:** Lose Tier 1 speed, gain Tier 3 capability

### Alternative: Staged Loading
- Keep embedding + 0.8b + 9b always loaded (~8.2GB)
- Load 2b or 14b on-demand based on router decision
- More flexible, slightly slower tier transitions

---

## Database Schema (Conceptual)

### Table: `reference_library`
```
id: UUID
prompt_text: TEXT
embedding: VECTOR(1024)  # From qwen3-embedding:0.6b
tier: INT (1, 2, or 3)
confidence: FLOAT (0.0 to 1.0)
source: ENUM ('curated', 'learned', 'user_override')
created_at: TIMESTAMP
```

### Table: `classification_log`
```
id: UUID
prompt_text: TEXT
embedding: VECTOR(1024)
router_decision: INT (1, 2, or 3)
router_method: ENUM ('embedding', 'tiny_llm', 'hybrid')
confidence_score: FLOAT
actual_tier_used: INT
escalated: BOOLEAN
escalation_reason: TEXT
user_override: BOOLEAN
latency_ms: INT
created_at: TIMESTAMP
```

### Table: `corrections`
```
id: UUID
original_classification_id: UUID (FK to classification_log)
correct_tier: INT
reason: TEXT
feedback_type: ENUM ('escalation', 'user_override', 'latency')
created_at: TIMESTAMP
```

---

## Implementation Phases

### Phase 0: Database Setup (Day 1)
**Goal:** Design and create the database schema

**Tasks:**
- Choose database (SQLite for simplicity, PostgreSQL for production)
- Create tables: `reference_library`, `classification_log`, `corrections`
- Seed `reference_library` with 10-20 hand-curated examples of each tier
- Test embedding generation with `qwen3-embedding:0.6b`

**Deliverable:** Working database with seed data

---

### Phase 1: Manual Switchboard (Days 2-3)
**Goal:** Prove you can programmatically talk to Ollama and swap models

**Tasks:**
- Write Python script that connects to Ollama API
- Create function: `generate(prompt, tier)` that calls correct model
- Test calling each tier manually
- Verify responses are correct

**Deliverable:** Script that can invoke any tier on demand

---

### Phase 2: Hybrid Router (Days 4-6)
**Goal:** Automate tier selection using B+C approach

**Tasks:**
- Implement embedding generation for incoming prompts
- Implement distance calculation against `reference_library`
- Set confidence threshold (e.g., 0.85)
- If confidence < threshold, invoke `qwen3.5:0.8b` as classifier
- Log every classification decision to `classification_log`

**Deliverable:** Router that automatically assigns tiers and logs decisions

---

### Phase 3: Feedback Loop (Days 7-9)
**Goal:** Create self-correcting system that learns from mistakes

**Tasks:**
- Add verification step after Tier 1 execution
- Check for deferral phrases, syntax errors, excessive hedging
- If verification fails, escalate to Tier 2
- Log escalation event to `corrections` table
- Implement periodic job to update `reference_library` with corrections
- Add manual override command (e.g., `--force-tier 3`)

**Deliverable:** System that learns from its mistakes and improves over time

---

### Phase 4: Evaluate LangGraph (Day 10+)
**Goal:** Determine if framework provides value

**Questions to ask:**
- Is state management becoming complex in plain Python?
- Do I need persistent state across sessions?
- Do I need human-in-the-loop interrupts?
- Do I need visual observability of decision flows?

**If yes to any:** Migrate to LangGraph
**If no:** Stick with plain Python (it's working fine)

**Deliverable:** Decision on framework adoption

---

## Testing Strategy

### Test Case 1: Simple Task
**Prompt:** "Write a regex to match email addresses"
**Expected:** Router → Tier 1 (2b) → Fast response
**Verify:** Response is correct, latency < 1s

### Test Case 2: Medium Task
**Prompt:** "Refactor this 50-line function to use async/await"
**Expected:** Router → Tier 2 (9b) → Moderate response
**Verify:** Response is correct, latency 2-5s

### Test Case 3: Complex Task
**Prompt:** "Analyze these 3 files and suggest an architectural refactor"
**Expected:** Router → Tier 3 (14b) → Slow but thorough response
**Verify:** Response demonstrates cross-file reasoning

### Test Case 4: Learning Test
**Prompt:** "Explain quantum computing" (initially misclassified as simple)
**Expected:** Tier 1 attempts, fails/defers → escalates to Tier 2
**Verify:** Correction logged, future similar prompts go to Tier 2

---

## Future Enhancements

1. **Batch Processing:** Process multiple prompts in parallel
2. **Model Swapping:** Automatically unload/load models based on usage patterns
3. **Advanced Verification:** Use a separate model to grade output quality
4. **Multi-Modal:** Add image understanding (screenshots of UI bugs)
5. **Distributed:** Run router on CPU, models on GPU
6. **API Layer:** Expose as local API for other tools to consume

---

## Key Insights

1. **"I Don't Know" is a Feature:** Embrace uncertainty. Honest deferral is better than confident hallucination.

2. **Feedback is Everything:** The system only improves if it learns from mistakes. Escalation events are gold.

3. **Start Simple:** Plain Python first. Add complexity only when needed.

4. **VRAM is Finite:** Plan for memory constraints. You can't run everything at once.

5. **The Router is the Product:** The models are commodities. The intelligence is in how you route between them.

---

## Next Steps

1. Review this plan
2. Set up the database (Phase 0)
3. Start with Phase 1 (Manual Switchboard)
4. Iterate through phases, testing at each step
5. Share learnings and refine the architecture

---

**Created:** October 10, 2026  
**Status:** Planning Phase  
**Hardware:** RTX 5070 (12GB VRAM)  
**Models:** qwen3.5 (0.8b, 2b, 9b), qwen3-embedding:0.6b