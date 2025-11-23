import re
import types
from typing import List, Dict

import pytest

from Exercise_2.agent import (
    Filters,
    Movie,
    build_query_from_filters,
    filter_and_rank_itunes_results,
    map_itunes_to_movie,
    enrich_movie,
)


def test_filters_describe_basic():
    f = Filters(query="comedy", genres=["Comedy"], year=1999, include_terms=["space"], exclude_terms=["horror"])
    desc = f.describe()
    assert "query='comedy'" in desc
    assert "genres=Comedy" in desc
    assert "year=1999" in desc
    assert "include=space" in desc
    assert "exclude=horror" in desc


def test_build_query_from_filters_combines_fields():
    f = Filters(query="funny", genres=["Comedy"], actors=["Carrey"], directors=["Nolan"], year=2000)
    q = build_query_from_filters(f)
    # Should include all elements and the year string
    for term in ["funny", "Comedy", "Carrey", "Nolan", "2000"]:
        assert term in q


def test_filter_and_rank_itunes_results_excludes_and_sorts():
    # Create fake items mimicking iTunes payload
    items: List[Dict] = [
        {
            "trackName": "Space Laughs",
            "primaryGenreName": "Comedy",
            "longDescription": "A hilarious comedy in space",
            "releaseDate": "2001-01-01T00:00:00Z",
        },
        {
            "trackName": "Haunted Ship",
            "primaryGenreName": "Horror",
            "longDescription": "Scary ghosts on a ship",
            "releaseDate": "2001-01-01T00:00:00Z",
        },
        {
            "trackName": "Romantic Stars",
            "primaryGenreName": "Romance",
            "longDescription": "A love story among the stars",
            "releaseDate": "1999-05-05T00:00:00Z",
        },
    ]

    f = Filters(genres=["comedy"], include_terms=["space"], exclude_terms=["ghosts"], year_from=1998, year_to=2005)
    filtered = filter_and_rank_itunes_results(items, f)

    # Haunted Ship should be excluded due to exclude_terms (ghosts)
    titles = [it["trackName"] for it in filtered]
    assert "Haunted Ship" not in titles

    # Space Laughs should score higher than Romantic Stars (matches genre + include term)
    assert titles[0] == "Space Laughs"


def test_map_itunes_to_movie_poster_size_and_trailer_fallback():
    it = {
        "trackName": "Example Movie",
        "releaseDate": "2010-06-01T00:00:00Z",
        "primaryGenreName": "Comedy",
        "longDescription": "A long description",
        "artworkUrl100": "https://image.example.com/100x100bb.jpg",
        # No previewUrl -> should fallback to YouTube search link
    }
    m = map_itunes_to_movie(it)
    assert m.title == "Example Movie"
    assert m.year == 2010
    assert m.genre == "Comedy"
    assert m.poster_url.endswith("600x600bb.jpg")
    assert "youtube.com/results" in m.trailer_url


def test_enrich_movie_uses_wikipedia_when_overview_missing(monkeypatch):
    # Arrange: movie without overview
    movie = Movie(title="Test Title", overview=None)

    # Monkeypatch wikipedia_summary used inside enrich_movie
    from Exercise_2 import agent as agent_module

    def fake_wiki(title):
        assert title == "Test Title"
        return "Wikipedia summary here."

    monkeypatch.setattr(agent_module, "wikipedia_summary", fake_wiki)

    enriched = enrich_movie(movie)
    assert enriched.overview == "Wikipedia summary here."
