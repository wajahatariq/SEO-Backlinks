"""
agent/pdf_agent.py — Module 5: PDF Backlink Classifier

Extracts all URLs/domains from an uploaded PDF, runs a fast rule-based pass,
then sends unknown domains to the LLM in chunks of CHUNK_SIZE for classification into:
  Guest Post | Profile Creation | Business Directory | Forum/Comment | Web 2.0

Deduplicates by domain first so even very large PDFs with repeated URLs are handled
efficiently. Rule-based pass covers ~60-70 % of common domains at zero API cost.
"""

import io
import json
import os
import re
from typing import Any

import litellm
import pdfplumber
from dotenv import load_dotenv

load_dotenv()

_MODEL = os.environ.get("LITELLM_MODEL", "gpt-4o-mini")
CHUNK_SIZE = 100

CATEGORIES = [
    "Guest Post",
    "Profile Creation",
    "Business Directory",
    "Forum/Comment",
    "Web 2.0",
]

# ── Rule-based domain patterns ───────────────────────────────────────────────

_WEB2 = {
    "blogspot", "wordpress", "tumblr", "weebly", "wix", "medium", "blogger",
    "livejournal", "typepad", "hubpages", "squidoo", "ezinearticles",
    "goarticles", "articlesbase", "isnare", "selfgrowth", "buzzle",
    "triond", "helium", "suite101", "xanga", "pen", "jimdo",
}
_DIR = {
    "yelp", "yellowpages", "manta", "hotfrog", "foursquare", "citysearch",
    "superpages", "bbb", "angieslist", "angi", "thumbtack", "chamberofcommerce",
    "openfirm", "bizify", "cylex", "brownbook", "expressbusinessdirectory",
    "merchantcircle", "showmelocal", "tuugo", "salespider", "spokeo",
    "corporationwiki", "dnb", "businessdirectory",
}
_PROFILE = {
    "linkedin", "twitter", "facebook", "instagram", "pinterest", "about.me",
    "crunchbase", "github", "behance", "dribbble", "vimeo", "youtube",
    "soundcloud", "gravatar", "flickr", "xing", "myspace", "angel",
    "angellist", "producthunt", "kaggle", "researchgate", "academia",
    "slideshare", "scribd", "quora", "goodreads",
}
_FORUM = {
    "reddit", "stackexchange", "stackoverflow", "digg", "slashdot",
    "disqus", "intensedebate", "nabble", "boardreader", "warriorforum",
    "digitalpoint", "v7n", "sitepoint",
}


def _rule_classify(domain: str) -> str | None:
    d = domain.lower().replace("www.", "")
    if any(p in d for p in _WEB2):
        return "Web 2.0"
    if any(p in d for p in _DIR):
        return "Business Directory"
    if any(p in d for p in _PROFILE):
        return "Profile Creation"
    if any(p in d for p in _FORUM):
        return "Forum/Comment"
    if any(kw in d for kw in ("forum", "community", "discuss", "board", "talk", "hub")):
        return "Forum/Comment"
    if any(kw in d for kw in ("directory", "listing", "pages", "bizz", "biz.")):
        return "Business Directory"
    return None


def _extract_domain(url: str) -> str:
    url = url.lower().strip()
    for p in ("https://", "http://", "www."):
        if url.startswith(p):
            url = url[len(p):]
    return url.split("/")[0].split("?")[0].split("#")[0]


_URL_RE = re.compile(
    r"https?://[^\s<>\"',;{}\[\]\\]+|"
    r"(?:www\.)[a-zA-Z0-9\-]+(?:\.[a-zA-Z]{2,})+(?:/[^\s<>\"',;]*)?",
    re.IGNORECASE,
)


def extract_items_from_pdf(pdf_bytes: bytes) -> list[str]:
    """
    Extract and deduplicate all URLs/domains from PDF bytes.
    Handles text-based and table-formatted PDFs (e.g. CSV exported as PDF).
    Returns a list of unique URL strings, deduplicated by domain.
    """
    raw: list[str] = []

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                # Tables first (handles spreadsheet-style PDFs)
                for table in (page.extract_tables() or []):
                    for row in table:
                        for cell in (row or []):
                            if cell:
                                raw.extend(_URL_RE.findall(str(cell)))
                # Raw text fallback
                text = page.extract_text() or ""
                raw.extend(_URL_RE.findall(text))
    except Exception:
        pass

    seen: set[str] = set()
    unique: list[str] = []
    for item in raw:
        domain = _extract_domain(item)
        if domain and len(domain) > 3 and "." in domain and domain not in seen:
            seen.add(domain)
            unique.append(item.strip().rstrip("/"))

    return unique


def classify_chunk_llm(items: list[str]) -> list[dict[str, Any]]:
    """
    Send a chunk of URLs/domains to the LLM for classification.
    Returns one classified dict per input item, in the same order.
    """
    numbered = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))
    prompt = f"""You are an SEO backlink analyst. Classify each URL/domain into exactly one of these 5 categories:
- "Guest Post"          — editorial blogs, article sites, news sites, niche content blogs
- "Profile Creation"    — social profiles, author pages, bio/portfolio sites, professional networks
- "Business Directory"  — local/business citation sites, listings, yellow-pages-style directories
- "Forum/Comment"       — discussion boards, Q&A platforms, comment sections, online communities
- "Web 2.0"             — free hosted blog/site platforms (Blogspot, WordPress.com, Tumblr, Medium, Wix, Weebly, etc.)

URLs to classify:
{numbered}

Return ONLY a JSON object with key "results" — an array of exactly {len(items)} objects in the same order.
Each object must have:
  "url": the original URL string
  "category": one of the 5 category strings above
  "confidence": "High", "Medium", or "Low"

No extra keys, no markdown."""

    resp = litellm.completion(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    raw_out = resp.choices[0].message.content.strip()
    data = json.loads(raw_out)
    results: list[dict[str, Any]] = data.get("results", [])

    # Ensure length matches input
    while len(results) < len(items):
        results.append({
            "url": items[len(results)],
            "category": "Guest Post",
            "confidence": "Low",
        })

    return results[: len(items)]
