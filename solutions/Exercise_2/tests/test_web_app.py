from typing import List

import pytest
from fastapi.testclient import TestClient


def make_app_and_client(monkeypatch):
    # Import after monkeypatch as needed
    import Exercise_2.web_app as web

    # Pretend LLM backend is ready
    monkeypatch.setattr(web, "_llm_backend_ready", lambda: True)

    # Stub parse_filters to avoid llamafile dependency
    from Exercise_2.agent import Filters

    def fake_parse_filters(text, base=None):
        # Minimal behavior: set query to text and keep others
        f = base or Filters()
        f.query = text
        return f

    monkeypatch.setattr(web, "parse_filters", fake_parse_filters)

    # Stub the agent search to avoid network and produce stable data
    class DummyAgent:
        def __init__(self):
            from Exercise_2.agent import Movie
            self.filters = Filters()
            self.last_results: List[Movie] = []
            self.page = 0
            self.per_page = 5

        def search(self):
            from Exercise_2.agent import Movie
            # Create 12 mock results to exercise paging and refine message
            self.last_results = [
                Movie(title=f"Movie {i}", year=2000 + (i % 3), genre="Comedy", overview=f"Overview {i}")
                for i in range(12)
            ]
            self.page = 0
            return self.last_results

        def current_page(self):
            start = self.page * self.per_page
            end = start + self.per_page
            return self.last_results[start:end]

        def has_more(self):
            return (self.page + 1) * self.per_page < len(self.last_results)

        def next_page(self):
            if self.has_more():
                self.page += 1
            return self.current_page()

    dummy = DummyAgent()
    monkeypatch.setattr(web, "_agent", dummy)

    return web.app, TestClient(web.app), dummy


def test_index_returns_html(monkeypatch):
    app, client, _ = make_app_and_client(monkeypatch)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


def test_message_validation_and_commands(monkeypatch):
    app, client, dummy = make_app_and_client(monkeypatch)

    # Empty input -> 400
    resp = client.post("/api/message", json={"input": ""})
    assert resp.status_code == 400

    # Help -> ok and no results
    resp = client.post("/api/message", json={"input": "help"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["results"] == []

    # Restart -> resets state
    dummy.last_results = ["X"]
    resp = client.post("/api/message", json={"input": "restart"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 0
    assert body["results"] == []

    # More before any search -> 400
    resp = client.post("/api/message", json={"input": "more"})
    assert resp.status_code == 400


def test_message_search_and_paging(monkeypatch):
    app, client, dummy = make_app_and_client(monkeypatch)

    # Trigger a search with results; we stubbed 12 results
    resp = client.post("/api/message", json={"input": "comedy"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    # Since total > 10, message should be a refining question or similar string, but not empty
    assert isinstance(data["message"], str) and len(data["message"]) > 0
    # First page should contain up to 5 results
    assert len(data["results"]) == 5
    assert data["has_more"] is True

    # Next page via 'more'
    resp2 = client.post("/api/message", json={"input": "more"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["results"]) == 5
    assert data2["has_more"] is True

    # Third page
    resp3 = client.post("/api/message", json={"input": "more"})
    assert resp3.status_code == 200
    data3 = resp3.json()
    # Remaining 2 results
    assert len(data3["results"]) == 2
    assert data3["has_more"] is False


def test_details_returns_single_movie(monkeypatch):
    app, client, dummy = make_app_and_client(monkeypatch)

    # Seed with initial results by performing a search
    client.post("/api/message", json={"input": "anything"})

    # Request details for second item on current page
    resp = client.post("/api/message", json={"input": "details 2"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"].lower() == "details"
    assert len(data["results"]) == 1
    assert data["results"][0]["title"].startswith("Movie ")
