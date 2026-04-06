import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="SEO Backlink Opportunity Agent",
    description="Autonomous agent that finds high-quality backlink opportunities.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Confirm the API is running."""
    return {"status": "ok", "version": "0.1.0"}


# /api/find-links will be wired up once the LangGraph agent is built.
