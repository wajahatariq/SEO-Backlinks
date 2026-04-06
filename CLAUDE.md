# Project: SEO Backlink Opportunity Agent

## Overview
We are building an autonomous SEO agent that analyzes a target domain, queries the DataForSEO API to find competitor backlink strategies, and filters the results using an LLM to generate a clean list of high-quality link-building opportunities.

## Tech Stack
* Backend: Python 3.11+, FastAPI.
* Agent Orchestration: LangGraph.
* LLM Interface: LiteLLM (Standardized API for all model calls).
* LLM Provider: Groq — model `groq/llama-3.3-70b-versatile`.
* Data Source: DataForSEO API v3 (Specifically the Backlinks API).
* Frontend: Vanilla HTML, CSS, JavaScript.
* Version Control: Git / GitHub → https://github.com/wajahatariq/SEO-Backlinks.git
* Deployment: Vercel (serverless Python via `@vercel/python`).

## Project Structure
```
SEO Backlinks/
├── agent/
│   ├── __init__.py
│   ├── state.py       # AgentState TypedDict
│   ├── nodes.py       # Three LangGraph nodes
│   └── graph.py       # Compiled StateGraph (seo_agent)
├── api/
│   └── index.py       # Vercel serverless entry point (imports main.app)
├── frontend/
│   ├── index.html     # Main UI
│   ├── style.css      # Dark theme styles
│   └── app.js         # Fetch API calls + result rendering
├── main.py            # FastAPI app + /api/find-links endpoint
├── tools.py           # DataForSEO API helper (fetch_referring_domains)
├── requirements.txt
├── vercel.json        # Vercel routing config
├── .env               # Local secrets (gitignored)
└── .gitignore
```

## LangGraph Agent Flow
```
analyze_competitors → fetch_dataforseo → filter_and_rank → END
```
Each node writes to AgentState. Conditional edges short-circuit to END on error.

## Coding Standards & Rules
1. Python: Use Type Hints (`typing`). Adhere to PEP 8. Use `Pydantic` for data validation.
2. LangGraph: Structure the graph with clear separation of concerns (Nodes: Analyze Competitors, Fetch DataForSEO, Filter & Rank). Define a clear `TypedDict` for the agent's State.
3. LiteLLM & DataForSEO: Never hardcode API credentials. Always use environment variables (`.env`). The DataForSEO credentials will be `DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD`.
4. Authentication: Use standard `requests` or `httpx` with HTTP Basic Auth for DataForSEO (it handles the Base64 encoding automatically).
5. Frontend: Keep it simple. Use modern Vanilla JS (ES6+), Fetch API for backend calls, and semantic HTML5. No heavy frameworks.
6. API Endpoints: The FastAPI backend must expose a `/api/find-links` endpoint that the frontend can call.
7. Git: Make small, logical commits as you build features.
8. Deployment: `VERCEL=1` is auto-set by Vercel at runtime — use it to skip local-only behaviour (e.g. static file mounting).

## Environment Variables
| Variable              | Where to set          | Description                              |
|-----------------------|-----------------------|------------------------------------------|
| DATAFORSEO_LOGIN      | .env + Vercel         | DataForSEO account email                 |
| DATAFORSEO_PASSWORD   | .env + Vercel         | DataForSEO API password                  |
| GROQ_API_KEY          | .env + Vercel         | Groq API key (used by LiteLLM)           |
| LITELLM_MODEL         | .env + Vercel         | e.g. `groq/llama-3.3-70b-versatile`      |

## Running Locally
```bash
venv/Scripts/uvicorn main:app --reload
# Open http://127.0.0.1:8000
```

## Deploying to Vercel
1. Push to GitHub (remote: https://github.com/wajahatariq/SEO-Backlinks.git).
2. In Vercel dashboard → New Project → import `wajahatariq/SEO-Backlinks`.
3. Add the four environment variables above in Vercel → Settings → Environment Variables.
4. Vercel auto-deploys on every push to `main`.
