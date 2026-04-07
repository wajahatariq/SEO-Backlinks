import asyncio
import json
import math
import os
from collections import Counter

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

load_dotenv()

from agent.graph import seo_agent
from agent.niche_agent import run_niche_finder
from agent.serp_agent import run_serp_analyzer
from agent.gap_agent import gap_agent
from agent.pdf_agent import (
    CATEGORIES,
    CHUNK_SIZE,
    _extract_domain,
    _rule_classify,
    classify_chunk_llm,
    extract_items_from_pdf,
)

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


# ---------------------------------------------------------------------------
# Module 5 — PDF Backlink Classifier (SSE streaming)
# ---------------------------------------------------------------------------

@app.post("/api/classify-pdf", tags=["Module 5"])
async def classify_pdf(file: UploadFile = File(...)) -> StreamingResponse:
    """
    Upload a PDF containing backlink URLs. AI classifies each into:
    Guest Post | Profile Creation | Business Directory | Forum/Comment | Web 2.0.

    Returns a Server-Sent Events stream so the frontend can show live progress.
    Events: start → progress (per chunk) → done | error
    """
    pdf_bytes = await file.read()

    async def event_stream():
        # ── 1. Extract URLs from PDF ──────────────────────────────────────
        try:
            items = await asyncio.to_thread(extract_items_from_pdf, pdf_bytes)
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': f'PDF extraction failed: {exc}'})}\n\n"
            return

        if not items:
            yield f"data: {json.dumps({'type': 'error', 'message': 'No URLs or domains found in the PDF. Make sure the file contains backlink data.'})}\n\n"
            return

        # ── 2. Fast rule-based pass ───────────────────────────────────────
        pre: list[dict | None] = []
        unknown: list[str] = []
        for item in items:
            cat = _rule_classify(_extract_domain(item))
            if cat:
                pre.append({
                    "url": item,
                    "domain": _extract_domain(item),
                    "category": cat,
                    "confidence": "High",
                })
            else:
                pre.append(None)
                unknown.append(item)

        total_chunks = math.ceil(len(unknown) / CHUNK_SIZE) if unknown else 0

        yield f"data: {json.dumps({'type': 'start', 'total': len(items), 'rule_classified': len(items) - len(unknown), 'llm_needed': len(unknown), 'chunks': total_chunks})}\n\n"

        # ── 3. LLM classification in chunks ──────────────────────────────
        llm_results: list[dict] = []
        for i in range(total_chunks):
            chunk = unknown[i * CHUNK_SIZE: (i + 1) * CHUNK_SIZE]
            try:
                classified = await asyncio.to_thread(classify_chunk_llm, chunk)
            except Exception:
                classified = [
                    {"url": u, "category": "Guest Post", "confidence": "Low"}
                    for u in chunk
                ]
            for r in classified:
                r["domain"] = _extract_domain(r.get("url", ""))
            llm_results.extend(classified)

            yield f"data: {json.dumps({'type': 'progress', 'chunk': i + 1, 'total_chunks': total_chunks, 'processed': min((i + 1) * CHUNK_SIZE, len(unknown)), 'total_llm': len(unknown)})}\n\n"

        # ── 4. Merge rule + LLM results ───────────────────────────────────
        final: list[dict] = []
        llm_idx = 0
        for entry in pre:
            if entry is not None:
                final.append(entry)
            else:
                if llm_idx < len(llm_results):
                    final.append(llm_results[llm_idx])
                    llm_idx += 1

        # ── 5. Build summary and emit done ────────────────────────────────
        counts = Counter(r.get("category", "Guest Post") for r in final)
        summary = {cat: counts.get(cat, 0) for cat in CATEGORIES}
        summary["total"] = len(final)

        yield f"data: {json.dumps({'type': 'done', 'results': final, 'summary': summary})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
