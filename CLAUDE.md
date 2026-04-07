# Project: SEO Backlink Opportunity Agent

## Overview
An autonomous AI SEO agent that covers a meaningful portion of what a human SEO specialist does day-to-day. Uses real-time web intelligence (Tavily) and an LLM (Groq) to analyse domains, find competitors, surface backlink opportunities, run SERP analysis, and generate gap reports with action plans.

## Tech Stack
* Backend: Python 3.11+, FastAPI
* Agent Orchestration: LangGraph
* LLM Interface: LiteLLM → Groq (`llama-3.3-70b-versatile`)
* Web Intelligence: Tavily API (real-time search + website extraction)
* Frontend: Vanilla HTML, CSS, JavaScript (dark theme, 4-tab dashboard)
* Version Control: Git / GitHub → https://github.com/wajahatariq/SEO-Backlinks.git
* Deployment: Vercel (serverless Python via `@vercel/python`)

## Project Structure
```
SEO Backlinks/
├── agent/
│   ├── __init__.py
│   ├── state.py          # AgentState TypedDict (Module 1)
│   ├── nodes.py          # Module 1 LangGraph nodes
│   ├── graph.py          # Module 1 compiled graph (seo_agent)
│   ├── niche_agent.py    # Module 2 — Niche Outreach Finder
│   ├── serp_agent.py     # Module 3 — SERP Analyzer
│   └── gap_agent.py      # Module 4 — Gap Analysis (LangGraph)
├── api/
│   └── index.py          # Vercel serverless entry point
├── frontend/
│   ├── index.html        # 4-tab dashboard UI
│   ├── style.css         # Dark theme styles
│   └── app.js            # Tab logic, API calls, CSV export
├── main.py               # FastAPI app — 4 endpoints
├── tools.py              # Tavily helpers: search_web(), extract_website()
├── requirements.txt
├── vercel.json           # Vercel routing config
├── .env                  # Local secrets (gitignored)
└── .gitignore
```

## Modules & API Endpoints

| Module | Endpoint | What it does |
|--------|----------|-------------|
| 1 — Backlink Finder   | `POST /api/find-links`    | Identifies competitors, surfaces 15 backlink opportunities |
| 2 — Niche Outreach    | `POST /api/niche-finder`  | Finds guest post / outreach sites by niche + location |
| 3 — SERP Analyzer     | `POST /api/serp-analyzer` | Returns top 10 SERP competitors for a keyword + insights |
| 4 — Gap Analysis      | `POST /api/gap-analysis`  | Link gaps, content gaps, authority gap, 15-step action plan |

## LangGraph Agent Flows

### Module 1 (Backlink Finder)
```
analyze_competitors → fetch_backlink_stats → filter_and_rank → END
```
- Node 1: Tavily searches for competitors → LLM extracts domains
- Node 2: Tavily extracts target site + searches competitor profiles → LLM builds profiles
- Node 3: Tavily searches niche opportunities → LLM generates 15 ranked opportunities

### Module 4 (Gap Analysis)
```
extract_sites → research_competitor → generate_gap_report → END
```
- Node 1: Tavily extracts both your site and competitor site
- Node 2: Tavily searches competitor authority/backlink data
- Node 3: LLM generates link gaps, content gaps, authority gap, action plan

### Modules 2 & 3
Simple sync functions (no graph needed) — Tavily search → LLM structured output.

## Coding Standards & Rules
1. Python: Use Type Hints. Adhere to PEP 8. Use Pydantic for data validation.
2. LangGraph: Clear separation of concerns per node. Use `TypedDict` for state.
3. Credentials: Never hardcode. Always use environment variables via `.env`.
4. Frontend: Vanilla JS (ES6+), Fetch API, semantic HTML5. No frameworks.
5. API Endpoints: FastAPI exposes all endpoints under `/api/`.
6. Git: Small, logical commits per feature.
7. Deployment: `VERCEL=1` auto-set by Vercel — used to skip local-only behaviour.

## Environment Variables
| Variable        | Where         | Description                              |
|-----------------|---------------|------------------------------------------|
| TAVILY_API_KEY  | .env + Vercel | Tavily web search + extraction API key   |
| GROQ_API_KEY    | .env + Vercel | Groq LLM API key (used via LiteLLM)      |
| LITELLM_MODEL   | .env + Vercel | `groq/llama-3.3-70b-versatile`           |
| VERCEL_TOKEN    | .env only     | Vercel deploy token (never commit)       |

## Running Locally
```bash
venv/Scripts/uvicorn main:app --reload
# Open http://127.0.0.1:8000
```

## Deploying to Vercel
```bash
venv/Scripts/python deploy.py
```
Or push to GitHub — Vercel auto-deploys on every push to `main`.

## Tavily Usage Per Request
| Module | Calls | Purpose |
|--------|-------|---------|
| 1 — Backlink Finder | ~3 | Competitor search, site extract, niche search |
| 2 — Niche Outreach  | 1  | Niche guest post search |
| 3 — SERP Analyzer   | 1  | Keyword SERP search |
| 4 — Gap Analysis    | ~3 | Extract both sites, competitor research |
Free tier: 1,000 calls/month

## Future Roadmap — Remaining Modules

### Module 1 Enhancement — Real Backlink Data (pending DataForSEO fix)
- Hook DataForSEO Backlinks API back in once account is unblocked
- Add real DA, Spam Score, Dofollow/Nofollow per backlink
- Categorize links: Guest Post, Profile, Directory, Forum, Web 2.0

### Phase 5 — Technical SEO Checker
- Check sitemap, robots.txt, page speed signals, mobile-friendliness
- Surface critical technical issues with fix instructions

### Phase 6 — Rank Tracking & Reporting
- Weekly automated agent runs via Vercel Cron
- Track keyword positions over time
- Email/Slack digest of wins, drops, and opportunities

### Phase 7 — Outreach Assistant
- For each link opportunity, draft a personalised outreach email
- Use Tavily to find the site owner's contact information
- Store outreach status in a simple database
