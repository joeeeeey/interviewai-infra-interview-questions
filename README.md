# Infra Interview Assignment (Datadog Read-only)

## Context
You are given read-only Datadog access for service `interviewai-core`.

Known facts only:
- Datadog has logs, metrics, and APM traces for this service.
- Business cares about latency signals like `chatFirstTimeToken`.
- The system has both websocket/socket behavior and REST API behavior.
- No additional architecture documents will be provided.

You may use any AI-assisted workflow (ChatGPT, Claude, Cursor, scripts, etc.).
We evaluate your investigation quality, evidence chain, and operational thinking.

## Global Constraints
- Read-only only: do not create/modify/delete any Datadog resources.
- Evidence required: conclusions must map to concrete logs/metrics/traces.
- Separate clearly: Fact vs Inference vs Assumption vs To-validate.
- Security: do not include secrets, tokens, PII, or full sensitive payloads.

## Q1: Service Understanding and Health Model
Deliver:
1. Service Overview (<= 1 page)
2. 3-5 key health indicators (SLI candidates)
3. Top 3 risks (trigger, impact, evidence, missing validation)
4. Runbook v0.1 for oncall first response

## Q2: Top Error Analysis (Recent Window)
Deliver:
1. Top 10 high-value error logs or error patterns
2. Error taxonomy / clustering
3. Noise vs User-impact judgment with evidence
4. Prioritized investigation plan (with rationale)

Notes:
- If error volume is large, pattern-based grouping is preferred.
- If API rate limiting occurs (e.g., 429), show how you handle throttling/retry.

## Q3: Convert Your Method into a Reusable AI Skill/Workflow (Highest Weight)
Deliver:
1. Skill/workflow goal
2. Inputs (service, time window, thresholds, focus dimensions)
3. Data sources/APIs used
4. Output schema/template
5. What can be automated vs what requires human review
6. Risks/limitations and guardrails
7. How the team should run and reuse it

## Submission Format
Submit one document (Markdown or PDF) with this structure:
1. Q1 - Service Overview & Runbook
2. Q2 - Error Analysis
3. Q3 - Skill / Workflow Spec
4. Appendix - Evidence References (queries/screenshots/trace links)

## Submission via Pull Request (Required)
Please submit your assignment through a GitHub Pull Request to this repository.

Required PR content:
1. Add your submission as a single file under `submissions/<your-name-or-id>.md`
2. Include only sanitized evidence references (no secrets, no full sensitive payloads)
3. In PR description, include:
   - time window used for analysis
   - tools/workflow used
   - any assumptions that could not be fully validated

PR title format:
- `Candidate Submission - <your-name-or-id>`

## Evaluation Rubric (What we care about)
- Speed and quality of convergence in an unfamiliar system
- Evidence-backed reasoning (not opinion-only conclusions)
- Signal selection quality (what matters vs what is noise)
- User-impact judgment and prioritization
- Practical runbook quality
- Reusability and safety of your workflow abstraction
