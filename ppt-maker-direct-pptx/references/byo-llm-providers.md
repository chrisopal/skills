# Bring Your Own LLM Provider

The skill speaks the **OpenAI Chat Completions** wire format. Any endpoint
that exposes that protocol works without code changes — set the right env
vars or `model_config.yaml` fields and go.

## Required configuration

| Setting   | Env var (preferred) | Env var (legacy)        | model_config.yaml |
|-----------|---------------------|-------------------------|-------------------|
| API key   | `LLM_API_KEY`       | `OPENROUTER_API_KEY`    | (n/a — env only)  |
| Base URL  | `LLM_BASE_URL`      | `OPENROUTER_BASE_URL`   | `base_url`        |
| Text model| `LLM_TEXT_MODEL`    | `OPENROUTER_TEXT_MODEL` | `text_model`      |
| Vision    | `LLM_VISION_MODEL`  | `OPENROUTER_VISION_MODEL` | `vision_model`  |
| Image gen | `LLM_IMAGE_MODEL`   | (n/a)                   | `image_model`     |

There is **no hardcoded base URL default** — you must set one of the
options above. The error message on miss lists every option.

## Provider quick-start

### OpenAI

```bash
export LLM_API_KEY="sk-..."
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_TEXT_MODEL="gpt-4o-mini"
export LLM_IMAGE_MODEL="dall-e-3"   # uses /v1/images/generations
```

`model_config.yaml` would set `provider: openai` so image generation routes
to `/v1/images/generations` (OpenAI's native API), not `/chat/completions`.

### OpenRouter

```bash
export LLM_API_KEY="sk-or-..."
export LLM_BASE_URL="https://openrouter.ai/api/v1"
export LLM_TEXT_MODEL="anthropic/claude-3.5-sonnet"
export LLM_IMAGE_MODEL="google/gemini-2.5-flash-image"
```

OpenRouter prefixes models with provider (`vendor/model`). Image generation
routes to `/chat/completions` with image content because OpenRouter doesn't
expose `/v1/images/generations`.

### Azure OpenAI

```bash
export LLM_API_KEY="<azure-api-key>"
export LLM_BASE_URL="https://<resource>.openai.azure.com/openai/deployments/<deployment>"
export LLM_TEXT_MODEL="gpt-4o-mini"   # uses your deployment id
```

Azure uses deployment IDs in the URL path; treat them as the model name.

### Groq

```bash
export LLM_API_KEY="gsk_..."
export LLM_BASE_URL="https://api.groq.com/openai/v1"
export LLM_TEXT_MODEL="llama-3.3-70b-versatile"
```

### Together AI

```bash
export LLM_API_KEY="<together-key>"
export LLM_BASE_URL="https://api.together.ai/v1"
export LLM_TEXT_MODEL="Qwen/Qwen2.5-72B-Instruct-Turbo"
```

### DeepSeek

```bash
export LLM_API_KEY="<deepseek-key>"
export LLM_BASE_URL="https://api.deepseek.com/v1"
export LLM_TEXT_MODEL="deepseek-chat"
```

### Local vLLM

```bash
export LLM_API_KEY="placeholder"   # vLLM ignores it but the var must be set
export LLM_BASE_URL="http://localhost:8000/v1"
export LLM_TEXT_MODEL="<your-served-model-name>"
```

### Ollama

```bash
export LLM_API_KEY="placeholder"
export LLM_BASE_URL="http://localhost:11434/v1"
export LLM_TEXT_MODEL="qwen2.5:14b"
```

### LiteLLM proxy

If you front multiple providers behind a single LiteLLM proxy:

```bash
export LLM_API_KEY="<litellm-master-key>"
export LLM_BASE_URL="http://localhost:4000/v1"
export LLM_TEXT_MODEL="<one-of-litellm's-routed-models>"
```

## Image generation routing

Image generation is the only place the protocol diverges:

- **OpenAI / Azure / Together** expose `POST /v1/images/generations`. The
  skill sends `{prompt, model, size, n, response_format: "b64_json"}`.
- **OpenRouter / Anthropic-via-OpenRouter / multimodal-via-chat providers**
  return images by way of `POST /v1/chat/completions` with the image
  embedded in the response message. The skill walks the response payload
  for `message.images[*].image_url.url` or a `data:image/...` URI in the
  text content.

The route is auto-picked from the base URL but you can override:

```yaml
# model_config.yaml
image_route: "images_api"   # or "chat"
```

If you point at a provider that doesn't support image generation at all,
set `image_model` to a non-image model and rely on the placeholder fallback
in `generate_image_assets.py` (it draws a styled placeholder PNG locally
and records `fallback_reason`).

## Backward compatibility

The legacy `OPENROUTER_*` env vars still work as fallbacks. Existing
deployments that rely on them keep functioning until a base URL is missing.
