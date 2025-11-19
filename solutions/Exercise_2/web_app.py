### Disclaimer
# This file is generated with the help of Junie. It is not meant for production use. If there are any mistakes or misinformation, please summit an issue [here]().
###

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .agent import (
    MovieAgent,
    Filters,
    enrich_movie,
    _LLM_CLIENT,
    parse_filters,
    generate_clarifying_question,
    generate_narrowing_question,
)
from .config import (
    LLAMAFILE_ENABLED,
    LLAMAFILE_BASE_URL,
)

app = FastAPI(title="Movie Agent Web UI", version="0.1.0")

# Single in-memory agent instance (simple demo)
_agent = MovieAgent()


def _llm_backend_ready() -> bool:
    if not (LLAMAFILE_ENABLED and _LLM_CLIENT and _LLM_CLIENT.get_model_id()):
        return False
    return True


class MessageIn(BaseModel):
    input: str


class MovieOut(BaseModel):
    title: str
    year: Optional[int] = None
    genre: Optional[str] = None
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    trailer_url: Optional[str] = None
    imdb_id: Optional[str] = None


class MessageOut(BaseModel):
    status: str
    message: str
    filters: str
    page: int
    has_more: bool
    results: List[MovieOut]


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    tpl_path = Path(__file__).parent / "templates" / "index.html"
    try:
        html_template = tpl_path.read_text(encoding="utf-8")
    except Exception:
        html_template = "<html><body><p>Template not found.</p></body></html>"
    html = html_template.replace("__BASE_URL__", LLAMAFILE_BASE_URL)
    return HTMLResponse(content=html)


@app.post("/api/message", response_model=MessageOut)
async def message(msg: MessageIn) -> MessageOut:
    if not _llm_backend_ready():
        raise HTTPException(status_code=503, detail=(
            "LLM backend not ready. Ensure llamafile server is running. "
            f"Tried base URL: {LLAMAFILE_BASE_URL}"
        ))

    text = (msg.input or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty input")

    # Commands similar to CLI
    if text.lower() in ("help",):
        return MessageOut(
            status="ok",
            message="Help: type natural language (e.g., 'lighthearted sci-fi from the 90s'). Commands: more, details N, refine ..., restart.",
            filters=_agent.filters.describe(),
            page=_agent.page,
            has_more=_agent.has_more(),
            results=[],
        )

    if text.lower() in ("restart",):
        _agent.filters = Filters()
        _agent.last_results = []
        _agent.page = 0
        return MessageOut(
            status="ok",
            message="Restarted. Tell me what you're in the mood for.",
            filters=_agent.filters.describe(),
            page=_agent.page,
            has_more=False,
            results=[],
        )

    if text.lower().startswith("details "):
        m = re.search(r"details\s+(\d+)", text.lower())
        if not m:
            raise HTTPException(status_code=400, detail="Please specify a result number, e.g., 'details 2'.")
        idx = int(m.group(1))
        page_results = _agent.current_page()
        if idx < 1 or idx > len(page_results):
            raise HTTPException(status_code=400, detail="That number isn't on the current page. Use 'more' to see more.")
        movie = page_results[idx - 1]
        movie = enrich_movie(movie)
        # Return single detailed movie
        return MessageOut(
            status="ok",
            message="Details",
            filters=_agent.filters.describe(),
            page=_agent.page,
            has_more=_agent.has_more(),
            results=[MovieOut(
                title=movie.title,
                year=movie.year,
                genre=movie.genre,
                overview=movie.overview,
                poster_url=movie.poster_url,
                trailer_url=movie.trailer_url,
                imdb_id=movie.imdb_id,
            )],
        )

    if text.lower() == "more":
        if not _agent.last_results:
            raise HTTPException(status_code=400, detail="We haven't searched yet. Say what you want first.")
        next_results = _agent.next_page()
        results = [MovieOut(
            title=m.title, year=m.year, genre=m.genre, overview=m.overview,
            poster_url=m.poster_url, trailer_url=m.trailer_url, imdb_id=m.imdb_id
        ) for m in next_results]
        return MessageOut(
            status="ok",
            message=f"Showing more results (page {_agent.page + 1}).",
            filters=_agent.filters.describe(),
            page=_agent.page,
            has_more=_agent.has_more(),
            results=results,
        )

    # Allow explicit refine command
    if text.lower().startswith("refine "):
        text = text[7:].strip()

    # Parse and update filters via llamafile
    try:
        _agent.filters = parse_filters(text, base=_agent.filters)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Perform search
    try:
        _agent.search()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {e}")

    page_results = _agent.current_page()
    results = [MovieOut(
        title=m.title, year=m.year, genre=m.genre, overview=m.overview,
        poster_url=m.poster_url, trailer_url=m.trailer_url, imdb_id=m.imdb_id
    ) for m in page_results]

    if not results:
        # Ask for clarification using LLM. Fallback to static message if unavailable.
        clarification = generate_clarifying_question(text, _agent.filters) or (
            "I couldn’t find matches. Could you add genre, year/range, actors, directors, or relax constraints?"
        )
        return MessageOut(
            status="ok",
            message=clarification,
            filters=_agent.filters.describe(),
            page=_agent.page,
            has_more=False,
            results=[],
        )

    total = len(_agent.last_results)
    # If too many results, ask a refining question but still return the first page of results
    msg = "Here are some picks:"
    if total > 10:
        refine_q = generate_narrowing_question(text, _agent.filters, total) or (
            "I found many matches. Do you want to narrow by sub-genre, year range, specific actors/directors, or exclude something?"
        )
        msg = refine_q

    return MessageOut(
        status="ok",
        message=msg,
        filters=_agent.filters.describe(),
        page=_agent.page,
        has_more=_agent.has_more(),
        results=results,
    )


# Optional: quick launcher with `python -m Exercise_2.web_app`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("Exercise_2.web_app:app", host="127.0.0.1", port=8000, reload=False)
