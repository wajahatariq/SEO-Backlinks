import asyncio
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

load_dotenv()

from agent.graph import seo_agent
from agent.niche_agent import run_niche_finder
from agent.serp_agent import run_serp_analyzer
from agent.gap_agent import gap_agent

app = FastAPI(
    title="SEO Backlink Opportunity Agent",
    description="Autonomous AI SEO agent — backlinks, niche outreach, SERP analysis, gap reports.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend locally (Vercel handles this via vercel.json in production)
if not os.environ.get("VERCEL"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend() -> FileResponse:
        return FileResponse("frontend/index.html")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    return {"status": "ok", "version": "2.0.0"}


# ---------------------------------------------------------------------------
# Module 1 — Backlink Opportunity Finder
# ---------------------------------------------------------------------------

class FindLinksRequest(BaseModel):
    target_domain: str

    @field_validator("target_domain")
    @classmethod
    def strip_protocol(cls, v: str) -> str:
        return v.replace("https://", "").replace("http://", "").rstrip("/")


class FindLinksResponse(BaseModel):
    target_domain: str
    competitors: list[str]
    opportunities: list[dict]
    error: str | None = None


@app.post("/api/find-links", response_model=FindLinksResponse, tags=["Module 1"])
async def find_links(body: FindLinksRequest) -> FindLinksResponse:
    """Identify competitors and surface backlink opportunities for a domain."""
    result = await seo_agent.ainvoke({
        "target_domain": body.target_domain,
        "competitors": [],
        "raw_referring_domains": [],
        "opportunities": [],
        "_target_content": "",
        "error": None,
    })
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return FindLinksResponse(
        target_domain=result["target_domain"],
        competitors=result["competitors"],
        opportunities=result["opportunities"],
    )


# ---------------------------------------------------------------------------
# Module 2 — Niche Outreach Finder
# ---------------------------------------------------------------------------

class NicheFinderRequest(BaseModel):
    query: str
    location: str = ""


class NicheFinderResponse(BaseModel):
    query: str
    location: str
    sites: list[dict]
    error: str | None = None


@app.post("/api/niche-finder", response_model=NicheFinderResponse, tags=["Module 2"])
async def niche_finder(body: NicheFinderRequest) -> NicheFinderResponse:
    """Search for niche-specific guest post and outreach opportunities."""
    result = await asyncio.to_thread(run_niche_finder, body.query, body.location)
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return NicheFinderResponse(
        query=body.query,
        location=body.location,
        sites=result["sites"],
    )


# ---------------------------------------------------------------------------
# Module 3 — SERP Analyzer
# ---------------------------------------------------------------------------

class SerpRequest(BaseModel):
    keyword: str


class SerpResponse(BaseModel):
    keyword: str
    competitors: list[dict]
    insights: str
    error: str | None = None


@app.post("/api/serp-analyzer", response_model=SerpResponse, tags=["Module 3"])
async def serp_analyzer(body: SerpRequest) -> SerpResponse:
    """Analyse the top 10 SERP competitors for a keyword."""
    result = await asyncio.to_thread(run_serp_analyzer, body.keyword)
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return SerpResponse(
        keyword=body.keyword,
        competitors=result["competitors"],
        insights=result["insights"],
    )


# ---------------------------------------------------------------------------
# Module 4 — Gap Analysis
# ---------------------------------------------------------------------------

class GapRequest(BaseModel):
    your_domain: str
    competitor_domain: str

    @field_validator("your_domain", "competitor_domain")
    @classmethod
    def strip_protocol(cls, v: str) -> str:
        return v.replace("https://", "").replace("http://", "").rstrip("/")


class GapResponse(BaseModel):
    your_domain: str
    competitor_domain: str
    authority_gap: dict
    link_gaps: list[dict]
    content_gaps: list[dict]
    action_plan: list[dict]
    error: str | None = None


@app.post("/api/gap-analysis", response_model=GapResponse, tags=["Module 4"])
async def gap_analysis(body: GapRequest) -> GapResponse:
    """Full gap analysis — link gaps, content gaps, authority gap, action plan."""
    result = await gap_agent.ainvoke({
        "your_domain": body.your_domain,
        "competitor_domain": body.competitor_domain,
        "your_content": "",
        "competitor_content": "",
        "competitor_research": "",
        "link_gaps": [],
        "content_gaps": [],
        "action_plan": [],
        "authority_gap": {},
        "error": None,
    })
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return GapResponse(
        your_domain=result["your_domain"],
        competitor_domain=result["competitor_domain"],
        authority_gap=result["authority_gap"],
        link_gaps=result["link_gaps"],
        content_gaps=result["content_gaps"],
        action_plan=result["action_plan"],
    )
