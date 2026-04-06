"""
api/index.py — Vercel serverless entry point.

Vercel looks for an `app` object in this file.
We import the FastAPI app from the project root.
"""

import sys
import os

# Ensure the project root is on the path so all local imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: F401, E402 — re-exported for Vercel
