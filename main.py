import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

load_dotenv()

from agent.graph import seo_agent  # noqa: E402 — import after load_dotenv

app = FastAPI(
    title="SEO Backlink Opportunity Agent",
    description="Autonomous agent that finds high-quality backlink opportunities.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class FindLinksRequest(BaseModel):
    target_domain: str

    @field_validator("target_domain")
    @classmethod
    def strip_protocol(cls, v: str) -> str:
        """Accept bare domains or URLs — normalise to 'example.com'."""
        return v.replace("https://", "").replace("http://", "").rstrip("/")


class FindLinksResponse(BaseModel):
    target_domain: str
    competitors: list[str]
    opportunities: list[dict]
    error: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Confirm the API is running."""
    return {"status": "ok", "version": "0.2.0"}


@app.post("/api/find-links", response_model=FindLinksResponse, tags=["Agent"])
async def find_links(body: FindLinksRequest) -> FindLinksResponse:
    """
    Run the full SEO backlink opportunity pipeline for the given domain.

    Steps executed by the agent:
    1. Identify competitor domains (LLM).
    2. Fetch referring domains from DataForSEO for each competitor.
    3. Filter and rank opportunities (LLM).
    """
    initial_state = {
        "target_domain": body.target_domain,
        "competitors": [],
        "raw_referring_domains": [],
        "opportunities": [],
        "error": None,
    }

    result = await seo_agent.ainvoke(initial_state)

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    return FindLinksResponse(
        target_domain=result["target_domain"],
        competitors=result["competitors"],
        opportunities=result["opportunities"],
    )
