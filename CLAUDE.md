# Project: SEO Backlink Opportunity Agent

## Overview
An autonomous SEO agent that analyses a target domain using real-time web intelligence (Tavily), identifies competitors, enriches their backlink profiles, and uses an LLM (Groq) to generate a ranked list of high-quality link-building opportunities.

## Tech Stack
* Backend: Python 3.11+, FastAPI
* Agent Orchestration: LangGraph
* LLM Interface: LiteLLM → Groq (`llama-3.3-70b-versatile`)
* Web Intelligence: Tavily API (real-time search + website extraction)
* Frontend: Vanilla HTML, CSS, JavaScript (dark theme)
* Version Control: Git / GitHub → https://github.com/wajahatariq/SEO-Backlinks.git
* Deployment: Vercel (serverless Python via `@vercel/python`)

## Project Structure
```
SEO Backlinks/
├── agent/
│   ├── __init__.py
│   ├── state.py       # AgentState TypedDict
│   ├── nodes.py       # Three LangGraph nodes (Tavily + LLM powered)
│   └── graph.py       # Compiled StateGraph (seo_agent)
├── api/
│   └── index.py       # Vercel serverless entry point
├── frontend/
│   ├── index.html     # Main UI
│   ├── style.css      # Dark theme styles
│   └── app.js         # Fetch API + result rendering
├── main.py            # FastAPI app + /api/find-links endpoint
├── tools.py           # Tavily helpers: search_web(), extract_website()
├── requirements.txt
├── vercel.json        # Vercel routing config
├── .env               # Local secrets (gitignored)
└── .gitignore
```

## LangGraph Agent Flow
```
analyze_competitors → fetch_backlink_stats → filter_and_rank → END
```

### Node Details
| Node | What it does |
|------|-------------|
| `analyze_competitors` | Tavily searches web for actual competitors → LLM extracts domains |
| `fetch_backlink_stats` | Tavily extracts target website + searches competitor link profiles → LLM builds structured profiles |
| `filter_and_rank` | Tavily searches niche link-building opportunities → LLM generates 15 ranked opportunities |

Each node writes to `AgentState`. Conditional edges short-circuit to END on any error.

## Coding Standards & Rules
1. Python: Use Type Hints. Adhere to PEP 8. Use Pydantic for data validation.
2. LangGraph: Clear separation of concerns per node. Use `TypedDict` for state.
3. Credentials: Never hardcode. Always use environment variables via `.env`.
4. Frontend: Vanilla JS (ES6+), Fetch API, semantic HTML5. No frameworks.
5. API Endpoints: FastAPI exposes `POST /api/find-links` for the frontend.
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

## Tavily Usage Per Request (~3 API calls)
- 1 search: find competitors for target domain
- 1 extract: read target website content
- 1 search: competitor backlink profiles + niche opportunities
- Free tier: 1,000 calls/month (~333 full agent runs/month)
