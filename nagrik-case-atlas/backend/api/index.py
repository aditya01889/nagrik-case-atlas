"""Vercel serverless entrypoint for the Nagrik Case Atlas FastAPI app."""
from app.main import app

# Vercel's Python runtime detects this ASGI application as the function handler.
