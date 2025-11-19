#!/usr/bin/env python3

### Disclaimer
# This file is generated with the help of Junie. It is not meant for production use. If there are any mistakes or misinformation, please summit an issue [here](https://github.com/Cheukting/BuildingAIAgent/issues).
###


"""
Movie Recommendation AI Agent (CLI)

Features:
- Conversational CLI to gather preferences and refine recommendations with follow-ups.
- Internet tools to search for movies and fetch details:
  - Primary search via Apple iTunes Search API (no API key required).
  - Details via Wikipedia summary when available (no API key required).
  - Poster images from iTunes artwork.
  - Trailer link via iTunes previewUrl (if available) or YouTube search link.
- Maintains session state (filters) to allow iterative refinement.

How to run:
  python Exercise_2/agent.py

Note:
- This agent uses only Python's standard library (urllib, json, re, os) for zero-install setup.
- Internet access is required for live search/details.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# -----------------------------
# Optional LLM backend (llamafile) config
# -----------------------------
from .config import (
    LLAMAFILE_ENABLED,
    LLAMAFILE_BASE_URL,
    LLAMAFILE_MODEL,
    LLAMAFILE_API_KEY,
    LLAMAFILE_TIMEOUT,
)

# -----------------------------
# Data models
# -----------------------------

@dataclass
class Movie:
    title: str
    year: Optional[int] = None
    genre: Optional[str] = None
    overview: Optional[str] = None
    cast: Optional[List[str]] = None
    poster_url: Optional[str] = None
    trailer_url: Optional[str] = None
    source: Optional[str] = None  # e.g., 'iTunes', 'OMDb'
    itunes_track_id: Optional[int] = None
    imdb_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Filters:
    query: str = ""
    include_terms: List[str] = field(default_factory=list)
    exclude_terms: List[str] = field(default_factory=list)
    genres: List[str] = field(default_factory=list)
    actors: List[str] = field(default_factory=list)
    directors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    country: Optional[str] = None

    def describe(self) -> str:
        parts = []
        if self.query:
            parts.append(f"query='{self.query}'")
        if self.genres:
            parts.append("genres=" + ", ".join(self.genres))
        if self.actors:
            parts.append("actors=" + ", ".join(self.actors))
        if self.directors:
            parts.append("directors=" + ", ".join(self.directors))
        if self.year:
            parts.append(f"year={self.year}")
        if self.year_from or self.year_to:
            parts.append(f"year_range={self.year_from or ''}-{self.year_to or ''}")
        if self.include_terms:
            parts.append("include=" + ", ".join(self.include_terms))
        if self.exclude_terms:
            parts.append("exclude=" + ", ".join(self.exclude_terms))
        return "; ".join(parts) or "(none)"


# -----------------------------
# Utility HTTP helpers
# -----------------------------

def http_get_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> Any:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "MovieAgent/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8", errors="replace")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None




# -----------------------------
# LLM backend (llamafile) client
# -----------------------------
class LlamafileClient:
    def __init__(self, base_url: str, api_key: str, model: Optional[str] = None, timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return None

    def get_model_id(self) -> Optional[str]:
        try:
            data = self._request("GET", "/models")
            if not data:
                return None
            # Data shape: {"data": [{"id": "..."}, ...]}
            arr = data.get("data") or []
            if arr:
                return arr[0].get("id")
        except Exception:
            return None
        return None

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: Optional[int] = None) -> Optional[str]:
        model = self.model or self.get_model_id()
        if not model:
            return None
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        try:
            data = self._request("POST", "/chat/completions", payload)
            if not data:
                return None
            # OpenAI-style: choices[0].message.content
            choices = data.get("choices") or []
            if not choices:
                return None
            msg = choices[0].get("message") or {}
            return msg.get("content")
        except Exception:
            return None


_LLM_CLIENT: Optional[LlamafileClient] = None
if LLAMAFILE_ENABLED:
    _LLM_CLIENT = LlamafileClient(
        base_url=LLAMAFILE_BASE_URL,
        api_key=LLAMAFILE_API_KEY,
        model=LLAMAFILE_MODEL,
        timeout=LLAMAFILE_TIMEOUT,
    )


def try_llm_parse_filters(user_text: str, base: Optional["Filters"]) -> Optional["Filters"]:
    if not (_LLM_CLIENT and LLAMAFILE_ENABLED):
        return None
    # Compact schema prompt to constrain output to JSON only
    system = (
        "You extract movie search filters from user requests. "
        "Output only minified JSON matching this schema: "
        '{"query":str,"include_terms":[str],"exclude_terms":[str],"genres":[str],'
        '"actors":[str],"directors":[str],"year":int|null,"year_from":int|null,'
        '"year_to":int|null,"country":str|null}. '
        "Do not include any text before or after the JSON."
    )
    base_obj = vars(base) if base else {}
    user = (
        "Base filters (use as defaults; override if user specifies):\n" + json.dumps(base_obj, ensure_ascii=False)
        + "\nUser request: " + user_text
    )
    content = _LLM_CLIENT.chat([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ], temperature=0.0)
    if not content:
        return None
    # Extract JSON (some models may wrap in code fences); be defensive
    try:
        s = content.strip()
        if s.startswith("```"):
            s = re.sub(r"^```[a-zA-Z]*", "", s).strip()
            if s.endswith("```"):
                s = s[:-3].strip()
        obj = json.loads(s)
        # Build Filters from returned JSON; keep dedupe below to sanitize
        f = Filters(
            query=obj.get("query") or (base.query if base else ""),
            include_terms=list(obj.get("include_terms") or []),
            exclude_terms=list(obj.get("exclude_terms") or []),
            genres=list(obj.get("genres") or []),
            actors=list(obj.get("actors") or []),
            directors=list(obj.get("directors") or []),
            year=(int(obj["year"]) if obj.get("year") is not None else None),
            year_from=(int(obj["year_from"]) if obj.get("year_from") is not None else None),
            year_to=(int(obj["year_to"]) if obj.get("year_to") is not None else None),
            country=(obj.get("country") or None),
        )
        # Merge with base defaults if fields are empty
        if base:
            if not f.query:
                f.query = base.query
            if not f.include_terms:
                f.include_terms = list(base.include_terms)
            if not f.exclude_terms:
                f.exclude_terms = list(base.exclude_terms)
            if not f.genres:
                f.genres = list(base.genres)
            if not f.actors:
                f.actors = list(base.actors)
            if not f.directors:
                f.directors = list(base.directors)
            if f.year is None:
                f.year = base.year
            if f.year_from is None:
                f.year_from = base.year_from
            if f.year_to is None:
                f.year_to = base.year_to
            if f.country is None:
                f.country = base.country
        # Final sanity: ensure types
        f.include_terms = [str(x) for x in f.include_terms]
        f.exclude_terms = [str(x) for x in f.exclude_terms]
        f.genres = [str(x) for x in f.genres]
        f.actors = [str(x) for x in f.actors]
        f.directors = [str(x) for x in f.directors]
        return f
    except Exception:
        return None


# Wrapper used by CLI: llamafile is required; no fallback
def parse_filters(text: str, base: Optional["Filters"] = None) -> "Filters":
    f = try_llm_parse_filters(text, base)
    if f:
        return f
    raise RuntimeError(
        "LLM parsing failed. Ensure llamafile server is running and accessible (see README.md)."
    )


# -----------------------------
# Tools: External data sources
# -----------------------------

def itunes_search_movies(term: str, limit: int = 20, country: str = "US", lang: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search movies via Apple iTunes Search API.

    Docs: https://performance-partners.apple.com/search-api
    Notes:
    - Endpoint: https://itunes.apple.com/search
    - For movies, recommended params: media=movie, entity=movie
    - attribute=movieTerm biases search to movie titles (per docs attribute list)
    - limit: API allows up to 200 results; clamp to [1, 200]
    - country: two-letter country code (e.g., US)
    - lang: optional, e.g., en_us (defaults per Apple if omitted)
    """
    if not term:
        return []
    # Clamp limit to API bounds
    try:
        limit_val = max(1, min(int(limit), 200))
    except Exception:
        limit_val = 20
    params: Dict[str, Any] = {
        "term": term,
        "media": "movie",
        "entity": "movie",
        "country": country,
        "limit": str(limit_val),
        # Bias search to movie titles
        "attribute": "movieTerm",
    }
    if lang:
        params["lang"] = lang
    url = f"https://itunes.apple.com/search?{urllib.parse.urlencode(params)}"
    data = http_get_json(url)
    results: List[Dict[str, Any]] = []
    if data and isinstance(data, dict):
        results = data.get("results", [])
    return results or []




def wikipedia_summary(title: str) -> Optional[str]:
    # Use Wikipedia REST API summary; title should be URL-encoded with spaces replaced by underscores
    if not title:
        return None
    slug = title.replace(" ", "_")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(slug)}"
    data = http_get_json(url, headers={"User-Agent": "MovieAgent/1.0 (https://example.com)"})
    if not data:
        return None
    extract = data.get("extract") or data.get("description")
    return extract


def youtube_trailer_search_link(title: str, year: Optional[int] = None) -> str:
    q = f"{title} trailer" + (f" {year}" if year else "")
    return "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": q})


# -----------------------------
# Agent logic helpers
# -----------------------------

ITUNES_TO_COMMON_GENRE = {
    # iTunes primaryGenreName mapped to simplified genre labels
    "Action & Adventure": ["Action", "Adventure"],
    "Comedy": ["Comedy"],
    "Documentary": ["Documentary"],
    "Drama": ["Drama"],
    "Horror": ["Horror"],
    "Kids & Family": ["Family"],
    "Romance": ["Romance"],
    "Sci-Fi & Fantasy": ["Sci-Fi", "Fantasy"],
    "Thriller": ["Thriller"],
    "Western": ["Western"],
    "Independent": ["Indie"],
    "Music Documentaries": ["Music", "Documentary"],
    "Musicals": ["Music"],
    "Sports": ["Sports"],
}



def build_query_from_filters(f: Filters) -> str:
    # For iTunes, we can only bias via the term query, so we combine key terms.
    terms = []
    if f.query:
        terms.append(f.query)
    terms += f.genres
    terms += f.actors
    terms += f.directors
    if f.year:
        terms.append(str(f.year))
    elif f.year_from or f.year_to:
        # no direct filter; include a year keyword loosely (from-to median)
        yr = f.year_from or f.year_to
        if yr:
            terms.append(str(yr))
    # Include include_terms and subtract exclude_terms conceptually by avoiding candidates later
    terms += f.include_terms
    q = " ".join(terms).strip()
    return q or f.query or "popular movies"


def filter_and_rank_itunes_results(items: List[Dict[str, Any]], f: Filters) -> List[Dict[str, Any]]:
    def score(item: Dict[str, Any]) -> int:
        s = 0
        title = item.get("trackName", "")
        genre = item.get("primaryGenreName", "")
        long_desc = item.get("longDescription") or item.get("shortDescription") or ""
        hay = f"{title} {genre} {long_desc}".lower()
        for term in f.include_terms:
            if term.lower() in hay:
                s += 2
        for g in f.genres:
            if g.lower() in hay:
                s += 2
        for a in f.actors:
            if a.lower() in hay:
                s += 1
        if f.year:
            if str(f.year) in hay:
                s += 1
            # or match release date
            rd = item.get("releaseDate", "")[:4]
            if rd and f.year and abs(int(rd) - f.year) <= 1:
                s += 1
        # penalize excluded terms
        for term in f.exclude_terms:
            if term.lower() in hay:
                s -= 3
        # recency bonus slight
        try:
            rd = int(item.get("releaseDate", "")[:4])
            s += max(0, rd - 1980) // 10
        except Exception:
            pass
        return s

    # Apply hard filters we can check locally
    filtered = []
    for it in items:
        title = it.get("trackName", "")
        hay = f"{title} {it.get('primaryGenreName','')} {it.get('longDescription','')}".lower()
        if any(term.lower() in hay for term in f.exclude_terms):
            continue
        if f.year and it.get("releaseDate"):
            try:
                if int(it["releaseDate"][:4]) != f.year:
                    continue
            except Exception:
                pass
        if (f.year_from or f.year_to) and it.get("releaseDate"):
            try:
                yr = int(it["releaseDate"][:4])
                if f.year_from and yr < f.year_from:
                    continue
                if f.year_to and yr > f.year_to:
                    continue
            except Exception:
                pass
        # If specific genres requested, require at least a loose match
        if f.genres:
            if not any(g.lower() in hay for g in f.genres):
                # try iTunes mapped genre
                ig = it.get("primaryGenreName", "")
                mapped = ITUNES_TO_COMMON_GENRE.get(ig, [])
                if not any(g.lower() in (" ".join(mapped)).lower() for g in f.genres):
                    continue
        filtered.append(it)

    filtered.sort(key=score, reverse=True)
    return filtered


def map_itunes_to_movie(it: Dict[str, Any]) -> Movie:
    title = it.get("trackName") or it.get("collectionName") or ""
    year = None
    if it.get("releaseDate"):
        try:
            year = int(it["releaseDate"][:4])
        except Exception:
            pass
    genre = it.get("primaryGenreName")
    overview = it.get("longDescription") or it.get("shortDescription") or it.get("collectionHdPrice")
    poster_url = it.get("artworkUrl100") or it.get("artworkUrl60")
    if poster_url:
        poster_url = re.sub(r"\d+x\d+bb\.jpg", "600x600bb.jpg", poster_url)
    trailer_url = it.get("previewUrl") or youtube_trailer_search_link(title, year)
    return Movie(
        title=title,
        year=year,
        genre=genre,
        overview=overview,
        cast=None,  # iTunes API doesn't provide cast
        poster_url=poster_url,
        trailer_url=trailer_url,
        source="iTunes",
        itunes_track_id=it.get("trackId"),
        raw=it,
    )


def enrich_movie(movie: Movie) -> Movie:
    """
    Enrich movie details without using any API keys.
    - Tries Wikipedia summary for plot if overview is missing.
    - Leaves other fields as-is to avoid API-keyed services.
    """
    if not movie.overview:
        summary = wikipedia_summary(movie.title)
        if summary:
            movie.overview = summary
    return movie


def generate_clarifying_question(user_text: str, filters: "Filters") -> Optional[str]:
    """
    Use the LLM backend to craft a short clarifying question when zero results are found.
    Keeps it focused on useful signals: genre, year or range, actors, directors, country,
    or whether to relax constraints.
    Returns None if LLM is unavailable; caller can fallback to a static prompt.
    """
    if not (_LLM_CLIENT and LLAMAFILE_ENABLED):
        return None
    try:
        system = (
            "You are a helpful movie recommendation assistant.\n"
            "The previous search returned zero results.\n"
            "Ask the user ONE concise question to disambiguate or broaden their request.\n"
            "Prefer asking about genre, year range, actors, directors, language/country, or willingness to relax constraints.\n"
            "Keep it under 25 words. Output just the question."
        )
        user = (
            "User request: " + (user_text or "") + "\n"
            "Current filters (JSON):\n" + json.dumps(vars(filters), ensure_ascii=False)
        )
        content = _LLM_CLIENT.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], temperature=0.2, max_tokens=64)
        if content:
            q = content.strip()
            if len(q) > 0:
                return q
    except Exception:
        pass
    return None


def generate_narrowing_question(user_text: str, filters: "Filters", total_results: int) -> Optional[str]:
    """
    Use the LLM backend to craft a short refining question when many results are found.
    Focus on helpful narrowing signals: specific sub-genre, year or range, runtime, actors, directors,
    language/country, or exclusions.
    Returns None if LLM is unavailable; caller can fallback to a static prompt.
    """
    if not (_LLM_CLIENT and LLAMAFILE_ENABLED):
        return None
    try:
        system = (
            "You are a helpful movie recommendation assistant.\n"
            "The previous search returned many results.\n"
            "Ask the user ONE concise question to help narrow down the list.\n"
            "Suggest narrowing by sub-genre, year range, specific actors/directors, runtime, language/country, or exclusions.\n"
            "Keep it under 25 words. Output just the question."
        )
        user = (
            f"Total results: {total_results}\n"
            "User request: " + (user_text or "") + "\n"
            "Current filters (JSON):\n" + json.dumps(vars(filters), ensure_ascii=False)
        )
        content = _LLM_CLIENT.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], temperature=0.2, max_tokens=64)
        if content:
            q = content.strip()
            if len(q) > 0:
                return q
    except Exception:
        pass
    return None

# -----------------------------
# Main agent class
# -----------------------------

class MovieAgent:
    def __init__(self):
        self.filters = Filters()
        self.last_results: List[Movie] = []
        self.page = 0
        self.per_page = 5

    # Core action: search and prepare movies
    def search(self) -> List[Movie]:
        term = build_query_from_filters(self.filters)
        raw = itunes_search_movies(term, limit=30)
        ranked = filter_and_rank_itunes_results(raw, self.filters)
        movies = [map_itunes_to_movie(it) for it in ranked]
        # Enrich top N slightly for better UX
        for i in range(min(10, len(movies))):
            try:
                movies[i] = enrich_movie(movies[i])
            except Exception:
                # Never crash on enrichment
                pass
        self.last_results = movies
        self.page = 0
        return movies

    def current_page(self) -> List[Movie]:
        start = self.page * self.per_page
        end = start + self.per_page
        return self.last_results[start:end]

    def has_more(self) -> bool:
        return (self.page + 1) * self.per_page < len(self.last_results)

    def next_page(self) -> List[Movie]:
        if self.has_more():
            self.page += 1
        return self.current_page()

    def render_movie_brief(self, idx: int, m: Movie) -> str:
        parts = [f"{idx}. {m.title}" + (f" ({m.year})" if m.year else "")]
        if m.genre:
            parts.append(f"   Genre: {m.genre}")
        if m.overview:
            parts.append("   " + truncate(m.overview, 180))
        if m.poster_url:
            parts.append(f"   Poster: {m.poster_url}")
        if m.trailer_url:
            parts.append(f"   Trailer: {m.trailer_url}")
        return "\n".join(parts)

    def render_movie_full(self, m: Movie) -> str:
        lines = [f"Title: {m.title}"]
        if m.year:
            lines.append(f"Year: {m.year}")
        if m.genre:
            lines.append(f"Genre: {m.genre}")
        if m.cast:
            lines.append("Cast: " + ", ".join(m.cast))
        if m.overview:
            lines.append("Plot: " + m.overview)
        if m.poster_url:
            lines.append(f"Poster: {m.poster_url}")
        if m.trailer_url:
            lines.append(f"Trailer: {m.trailer_url}")
        if m.imdb_id:
            lines.append(f"IMDb: https://www.imdb.com/title/{m.imdb_id}/")
        return "\n".join(lines)


# -----------------------------
# CLI helpers
# -----------------------------

def truncate(s: str, n: int) -> str:
    if not s:
        return s
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def print_divider():
    print("-" * 72)


def print_help():
    print("Commands you can use:")
    print("- Type what you like: 'funny space comedies', 'thrillers with DiCaprio', 'romance 1999'")
    print("- details N        Show full details for result number N on screen")
    print("- more             Show more results")
    print("- refine ...       Further narrow down, e.g., 'refine no horror from 2015-2020'")
    print("- restart          Clear filters and start over")
    print("- help             Show this help")
    print("- exit             Quit")


def run_cli():
    agent = MovieAgent()
    print("🎬 Movie Recommendation Agent")
    # Enforce llamafile requirement
    if not LLAMAFILE_ENABLED:
        print("Error: llamafile is required for this agent. Please:")
        print("- Make the llamafile executable and start the server (see README.md)")
        print("- Optionally set LLAMAFILE_BASE_URL if not using the default http://localhost:8080/v1")
        print("- Then re-run: python Exercise_2/agent.py")
        return
    if not _LLM_CLIENT or not _LLM_CLIENT.get_model_id():
        print(f"Error: could not reach llamafile server at {LLAMAFILE_BASE_URL}. Ensure it is running and reachable.")
        print("See README.md for instructions.")
        return
    print("LLM backend: llamafile (OpenAI-compatible) — enabled and required")
    print("Tell me what you're in the mood for (e.g., 'lighthearted sci-fi adventure from the 90s').")
    print("Type 'help' for tips, or 'exit' to quit.")

    while True:
        try:
            user = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not user:
            continue
        if user.lower() in ("exit", "quit"):  # Exit
            print("Goodbye!")
            break
        if user.lower() == "help":
            print_help()
            continue
        if user.lower() == "restart":
            agent.filters = Filters()
            agent.last_results = []
            agent.page = 0
            print("Okay, let's start fresh. What are you in the mood for?")
            continue

        if user.lower().startswith("details "):
            m = re.search(r"details\s+(\d+)", user.lower())
            if not m:
                print("Please specify a result number, e.g., 'details 2'.")
                continue
            idx = int(m.group(1))
            page_results = agent.current_page()
            if idx < 1 or idx > len(page_results):
                print("That number isn't on the current page of results. Use 'more' to see more.")
                continue
            movie = page_results[idx - 1]
            # Enrich on-demand (again) without OMDb
            movie = enrich_movie(movie)
            print_divider()
            print(agent.render_movie_full(movie))
            print_divider()
            continue

        if user.lower() == "more":
            if not agent.last_results:
                print("We haven't searched yet. Tell me what you want first.")
                continue
            next_results = agent.next_page()
            if not next_results:
                print("No more results. You can refine your request.")
                continue
            print_divider()
            print(f"Showing more results (page {agent.page + 1}). Current filters: {agent.filters.describe()}")
            print_divider()
            for i, m in enumerate(next_results, start=1):
                print(agent.render_movie_brief(i, m))
                print()
            continue

        # Allow explicit refine command
        if user.lower().startswith("refine "):
            user = user[7:].strip()

        # Parse and update filters (llamafile required)
        try:
            agent.filters = parse_filters(user, base=agent.filters)
        except RuntimeError as e:
            print(str(e))
            continue

        # Perform search
        print("Searching with filters:", agent.filters.describe())
        try:
            movies = agent.search()
        except Exception as e:
            print("Sorry, there was an error searching for movies:", e)
            continue

        if not movies:
            clarification = generate_clarifying_question(user, agent.filters) or (
                "I couldn't find anything. Could you add genre, year/range, actors, directors, or relax constraints?"
            )
            print(clarification)
            continue

        # Show first page
        page_results = agent.current_page()
        print_divider()
        # If too many results, prompt a refining question but still show the first page
        if len(agent.last_results) > 10:
            refine_q = generate_narrowing_question(user, agent.filters, len(agent.last_results)) or (
                "I found many matches. Want to narrow by sub-genre, year range, specific actors/directors, or exclude something?"
            )
            print(refine_q)
        else:
            print("Here are some picks:")
        print_divider()
        for i, m in enumerate(page_results, start=1):
            print(agent.render_movie_brief(i, m))
            print()
        if agent.has_more():
            print("Type 'more' to see more, or 'details N' for more info on a result.")


if __name__ == "__main__":
    run_cli()
