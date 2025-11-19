# Run local LLMs with llamafile (.llamafile) and the OpenAI API

This guide shows how to:
- Obtain self-contained .llamafile binaries from Hugging Face.
- Run a local OpenAI-compatible server using llamafile.
- Call your local model using the OpenAI SDK (Python) or curl.

It focuses on minimal steps that work across macOS, Linux, and Windows.


## What is llamafile?

llamafile packages a llama.cpp runtime and (optionally) model weights as a single, self-contained executable.

This guide uses only the self-contained “model.llamafile” approach:
- You download a single `.llamafile` that already includes the model weights.
- Make it executable and run it as a local OpenAI-compatible server.

The server exposes OpenAI-style endpoints under `/v1/...`.


## Prerequisites

- A machine with enough RAM/VRAM for the chosen model.
- Basic terminal/PowerShell access.
- Python 3.8+ if you’ll run the Python example (this repo requires Python 3.13+, but the example code works on 3.8+).


## Download and run a .llamafile

1) Get a .llamafile from Hugging Face
   - Many repos publish self-contained `.llamafile` binaries that include the weights (see “Where to find .llamafile on Hugging Face” below).
   - Download the `.llamafile` that matches your OS and CPU/GPU capabilities if variants are provided.

2) Run the server
- macOS/Linux:
  - `chmod +x ./ModelName.llamafile`
  - `./ModelName.llamafile --server --port 8080 --nobrowser`
- Windows (PowerShell):
  - `./ModelName.llamafile --server --port 8080 --nobrowser`

Notes:
- `--port 8080` is optional; you can use any free port.
- `--nobrowser` avoids auto-opening a UI/tab.
- Some builds support GPU offloading flags similar to llama.cpp (e.g., `--gpu auto`), depending on how the `.llamafile` was built.

3) Verify the server
- Open `http://localhost:8080/v1/models` in a browser. The response shows the model id to use in API calls.




## Use with the OpenAI SDK (Python)

Install the modern OpenAI SDK:

- `pip install --upgrade openai`

Example chat completion against your local llamafile server:

```python
from openai import OpenAI

# Point the client to your local server and use any placeholder API key
client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="sk-local-123",  # llamafile doesn't validate this
)

# Find your model id via GET /v1/models
# Example: model_name = "ModelName"  # use the id returned by /v1/models
model_name = "your-model-id-from-/v1/models"

resp = client.chat.completions.create(
    model=model_name,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Give me a 2-sentence summary of llamafile."},
    ],
    temperature=0.7,
)

print(resp.choices[0].message.content)
```


## Use with curl

```bash
curl -s http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-local-123" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model-id-from-/v1/models",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is llamafile in one sentence?"}
    ]
  }'
```

Streaming example (Python):

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8080/v1", api_key="sk-local")
stream = client.chat_completions.create(
    model="your-model-id-from-/v1/models",
    messages=[{"role": "user", "content": "Write a haiku about llamafile."}],
    stream=True,
)
for event in stream:
    delta = event.choices[0].delta
    if delta and delta.content:
        print(delta.content, end="", flush=True)
print()
```


## Tips for choosing .llamafile models

- Start small: 3–8B instruct models are a good baseline for many laptops.
- Prefer instruct-tuned variants for chat (names often include `Instruct` or `-it`).
- After launching, `GET /v1/models` shows the model id to use in the `model` field.


## Troubleshooting

- Port is busy: Change `--port` to a free one, e.g., `--port 8081` and update `base_url` accordingly.
- High memory usage / crashes: Pick a smaller model variant (e.g., fewer parameters) or use a build with reduced context size.
- Slow responses: Enable GPU offloading if supported (`--gpu auto`, `--n-gpu-layers`), reduce `--ctx-size`, or choose a smaller model.
- Model not found (404 or 400): Ensure your `model` value matches the name returned by `GET /v1/models`.
- CORS for browsers: Some builds support `--cors` options; otherwise call from backend code.
- Security: This server is unauthenticated. Do not expose it to the public internet without protections (reverse proxy, firewall, network ACLs).


## Where to find .llamafile on Hugging Face

- Browse/search: https://huggingface.co/models?search=llamafile
- Examples under Mozilla (availability can change):
  - https://huggingface.co/mozilla/Llama-3.1-8B-Instruct-llamafile
  - https://huggingface.co/mozilla/Qwen2.5-7B-Instruct-llamafile
  - https://huggingface.co/mozilla/Mistral-7B-Instruct-v0.3-llamafile
  - https://huggingface.co/mozilla/Phi-3.5-mini-instruct-llamafile

## Useful links

- llamafile releases: https://github.com/Mozilla-Ocho/llamafile/releases
- llama.cpp docs (flags and performance): https://github.com/ggerganov/llama.cpp

## Disclaimer

This file is generated with the help of Junie. If there are any mistakes or misinformation, please summit an issue [here](https://github.com/Cheukting/BuildingAIAgent/issues).
