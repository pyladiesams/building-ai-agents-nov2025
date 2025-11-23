### Disclaimer
# This file is generated with the help of Junie. It is not meant for production use. If there are any mistakes or misinformation, please summit an issue [here](https://github.com/Cheukting/BuildingAIAgent/issues).
###

"""
Centralized configuration for llamafile LLM backend.

This module reads environment variables once at import time and exposes
constants for use across the app. Keeping this here avoids scattering
os.getenv calls throughout the codebase.
"""
from __future__ import annotations

import os

# Whether llamafile-backed LLM parsing is enabled
# Now always enabled; the agent assumes llamafile backend is required.
LLAMAFILE_ENABLED = True

# Base URL of the OpenAI-compatible llamafile server
LLAMAFILE_BASE_URL = os.getenv("LLAMAFILE_BASE_URL", "http://localhost:8080/v1")

# Optional model id; when not set we query GET /v1/models and use the first
LLAMAFILE_MODEL = os.getenv("LLAMAFILE_MODEL")

# API key used by llamafile's OpenAI-compatible server (often any non-empty string)
LLAMAFILE_API_KEY = os.getenv("LLAMAFILE_API_KEY", "sk-local-123")

# HTTP timeout for calls to llamafile server
try:
    LLAMAFILE_TIMEOUT = int(os.getenv("LLAMAFILE_TIMEOUT", "20"))
except ValueError:
    LLAMAFILE_TIMEOUT = 20
