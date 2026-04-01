"""Compatibility entrypoint for Railway's default FastAPI detection."""

from __future__ import annotations

import os

from backend.app.main import app


def main() -> None:
    """Run the FastAPI app for direct `python main.py` execution."""
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
