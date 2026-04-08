# Project: SEO Backlink Opportunity Agent

## Overview
An autonomous AI SEO agent that covers a meaningful portion of what a human SEO specialist does day-to-day. Uses real-time web intelligence (Tavily) and an LLM (Groq) to analyse domains, find competitors, surface backlink opportunities, run SERP analysis, generate gap reports with action plans, and perform comprehensive bulk backlink searches.

## Tech Stack
* Backend: Python 3.11+, FastAPI
* Agent Orchestration: LangGraph (Modules 1 & 4), plain async functions (Modules 2, 3, 6)
* LLM Interface: LiteLLM → Groq (`llama-3.3-70b-versatile`)
* Web Intelligence: Tavily API (real-time search + website extraction)
* Frontend: Vanilla HTML, CSS, JavaScript (dark theme, 6-tab dashboard)
* Version Control: Git / GitHub → https://github.com/wajahatariq/SEO-Backlinks.git
* Deployment: Vercel (serverless Python via `@vercel/python`)

## Project Structure
```
SEO Backlinks/
├── agent/
│   ├── __init__.py
│   ├── state.py                  # AgentState TypedDict (Module 1)
│   ├── nodes.py                  # Module 1 LangGraph nodes
│   ├── graph.py                  # Module 1 compiled graph (seo_agent)
│   ├── niche_agent.py            # Module 2 — Niche Outreach Finder
│   ├── serp_agent.py             # Module 3 — SERP Analyzer
│   ├── gap_agent.py              # Module 4 — Gap Analysis (LangGraph)
│   ├── pdf_agent.py              # Module 5 — PDF Backlink Classifier
│   └── backlink_search_agent.py  # Module 6 — Comprehensive Backlink Search
├── api/
│   └── index.py          # Vercel serverless entry point
├── frontend/
│   ├── index.html        # 6-tab dashboard UI
│   ├── style.css         # Dark theme styles
│   └── app.js            # Tab logic, API calls, CSV export
├── main.py               # FastAPI app — 6 endpoints
├── tools.py              # Tavily helpers: search_web(), extract_website()
├── requirements.txt
├── vercel.json           # Vercel routing config
├── .env                  # Local secrets (gitignored)
└── .gitignore
```

## Modules & API Endpoints

| Module | Endpoint | What it does |
|--------|----------|-------------|
| 1 — Backlink Finder      | `POST /api/find-links`       | Identifies competitors, surfaces 15 backlink opportunities |
| 2 — Niche Outreach       | `POST /api/niche-finder`     | Finds guest post / outreach sites by niche + location |
| 3 — SERP Analyzer        | `POST /api/serp-analyzer`    | Returns top 10 SERP competitors for a keyword + insights |
| 4 — Gap Analysis         | `POST /api/gap-analysis`     | Link gaps, content gaps, authority gap, 15-step action plan |
| 5 — PDF Classifier       | `POST /api/classify-pdf`     | Uploads a PDF of backlink URLs; AI classifies each via SSE stream |
| 6 — Backlink Search      | `POST /api/backlink-search`  | Free-form query → 300–1,000+ unique backlink opportunities |

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
- **Note:** Prompt uses an explicit example JSON with all string values quoted to prevent Groq `json_validate_failed` errors.

### Modules 2 & 3
Simple sync functions (no graph needed) — Tavily search → LLM structured output.

### Module 5 (PDF Classifier)
SSE streaming endpoint. Pipeline: extract URLs from PDF → rule-based fast pass → LLM batch classification in chunks of 20 → merge results → emit `done` event.

### Module 6 (Backlink Search) — 4-Phase Pipeline
```
generate_queries → concurrent_search → extract_list_pages → batch_enrich → END
```
- **Phase 1:** LLM generates 40 diverse search queries (guest posts, directories, forums, .edu, Q&A, podcasts, Web 2.0, etc.) + 5 hardcoded list-hunting queries = 45 total
- **Phase 2:** All 45 queries run concurrently via `ThreadPoolExecutor` (max 10 workers), `max_results=10` each → up to 450 raw URLs, deduplicated by domain
- **Phase 3:** Pages whose title/URL/snippet contains list keywords (e.g. "top 100", "mega list", "500 sites") are deep-extracted via Tavily; LLM mines every domain mentioned — each page can yield 100–300 additional domains
- **Phase 4:** All unique domains batch-enriched in chunks of 50 (3 parallel workers) → each gets DA estimate, type, relevance, how-to-get action
- Results sorted: High relevance → Medium → Low, then by DA descending
- Frontend: live progress bar, relevance filter buttons (High/Medium/Low), pagination (100/page), CSV export

## Coding Standards & Rules
1. Python: Use Type Hints. Adhere to PEP 8. Use Pydantic for data validation.
2. LangGraph: Clear separation of concerns per node. Use `TypedDict` for state.
3. Credentials: Never hardcode. Always use environment variables via `.env`.
4. Frontend: Vanilla JS (ES6+), Fetch API, semantic HTML5. No frameworks.
5. API Endpoints: FastAPI exposes all endpoints under `/api/`.
6. Git: Small, logical commits per feature.
7. Deployment: `VERCEL=1` auto-set by Vercel — used to skip local-only behaviour.
8. LLM JSON prompts: Always include a fully-quoted example JSON structure + explicit "Every string value MUST be in double quotes" rule to prevent Groq `json_validate_failed` errors.

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
| 1 — Backlink Finder  | ~3    | Competitor search, site extract, niche search |
| 2 — Niche Outreach   | 1     | Niche guest post search |
| 3 — SERP Analyzer    | 1     | Keyword SERP search |
| 4 — Gap Analysis     | ~3    | Extract both sites, competitor research |
| 5 — PDF Classifier   | 0     | No Tavily calls — PDF + LLM only |
| 6 — Backlink Search  | ~53   | 45 searches + up to 8 page extractions |
Free tier: 1,000 calls/month (~18 Module 6 uses/month on free tier)

## Future Roadmap — Remaining Modules

### Module 1 Enhancement — Real Backlink Data (pending DataForSEO fix)
- Hook DataForSEO Backlinks API back in once account is unblocked
- Add real DA, Spam Score, Dofollow/Nofollow per backlink
- Categorize links: Guest Post, Profile, Directory, Forum, Web 2.0

### Module 6 Enhancement — Deeper Coverage
- Add pagination through Tavily results (if API supports offset)
- Integrate DataForSEO or Moz API for verified DA scores
- Cache results per query to reduce Tavily usage

### Phase 7 — Technical SEO Checker
- Check sitemap, robots.txt, page speed signals, mobile-friendliness
- Surface critical technical issues with fix instructions

### Phase 8 — Rank Tracking & Reporting
- Weekly automated agent runs via Vercel Cron
- Track keyword positions over time
- Email/Slack digest of wins, drops, and opportunities

### Phase 9 — Outreach Assistant
- For each link opportunity, draft a personalised outreach email
- Use Tavily to find the site owner's contact information
- Store outreach status in a simple database
