### Example Movie Recommendation AI agent

This repo requires a self-contained llamafile model at `Exercise_2/your_choosen_model.llamafile`. You can run it as a local OpenAI-compatible server and let the movie agent use it for natural language parsing. To see how to get a llamafile model, see `Exercise_1/how_to_llamafile.md`.

1) Start the llamafile server (macOS/Linux):
- `chmod +x Exercise_2/your_choosen_model.llamafile`
- `./Exercise_2/your_choosen_model.llamafile --server --port 8080 --nobrowser`

2) Agent backend configuration:
- Optional: `export LLAMAFILE_BASE_URL=http://localhost:8080/v1`
- Optional: `export LLAMAFILE_MODEL=<id from GET /v1/models>`

3) Run the CLI agent:
- `python -m Exercise_2.agent`

4) Or run the web frontend (FastAPI):
- Install deps once: `pip install -e .` (or `pip install fastapi uvicorn`)
- Start the server: `uvicorn Exercise_2.web_app:app --reload`
- Open http://127.0.0.1:8000 in your browser.

5) Testing (no llamafile required for tests):
- Install test deps: `pip install pytest httpx`
  - If you see `pytest: command not found`, install it with `pip install pytest` and re-run.
- Run tests (in the repository root directory): `pytest`
  - The tests stub the LLM backend and network calls where needed, so you can run them without starting llamafile.

Notes:
- Llamafile is required for the agent to work.
- If a search yields no suggestions, the backend will ask a concise clarifying question (via LLM). Reply with more details (e.g., genre, year range, actor) or use `refine ...` to update filters.
- If a search returns many matches (more than 10), the backend will ask a short question to help you narrow down the results (e.g., sub-genre, year range, actor/director, language, or exclusions).
- See `Exercise_1/how_to_llamafile.md` for more details on running llamafile and its API.

## Disclaimer

This file is generated with the help of Junie. If there are any mistakes or misinformation, please summit an issue [here](https://github.com/Cheukting/BuildingAIAgent/issues).