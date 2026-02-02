# Grok2API Copilot Instructions
## Architecture Snapshot
- [main.py](../main.py) bootstraps FastAPI + FastMCP under a shared lifespan: storage → config → token pool → call log; routers mounted under `/v1` + `/images` mirror OpenAI endpoints.
- Public API lives in [app/api/v1/chat.py](../app/api/v1/chat.py), [models.py](../app/api/v1/models.py), and [images.py](../app/api/v1/images.py); admin UI comes from [app/api/admin/manage.py](../app/api/admin/manage.py) and static assets in [app/template](../app/template).
- `app/services/grok/*` encapsulates Grok web reverse-engineering (client, uploads, posts, response processing) so keep new integrations inside this layer instead of routers.
## Configuration & Secrets
- Runtime config is `data/setting.toml` read by [app/core/config.py](../app/core/config.py); mutate settings through `setting.save()` so in-memory + storage stay in sync.
- Global env vars `STORAGE_MODE`, `DATABASE_URL`, `WORKERS` gate storage backend and uvicorn workers; multi-worker mode requires MySQL/Redis storage (see [app/core/storage.py](../app/core/storage.py)).
- `auth_manager` in [app/core/auth.py](../app/core/auth.py) enforces `Authorization: Bearer <api_key>` only when `grok.api_key` is set, so tests can omit headers if the key is blank.
## Token & Proxy Pools
- Token SSO data lives in `data/token.json`; always go through [app/services/grok/token.py](../app/services/grok/token.py) helpers (`add_token`, `select_token`, `reset_failure`) to keep batch-save + refresh tasks consistent.
- Proxy handling in [app/core/proxy_pool.py](../app/core/proxy_pool.py) binds proxies to SSO values, retries on 403/TLS, and persists assignments via the configured storage; when adding network calls fetch proxies through `proxy_pool` instead of reading config directly.
- `retry_status_codes`, `max_upload_concurrency`, and other knobs come from `setting.grok_config`; expose new tuning flags there rather than scattering literals.
## Request & Streaming Flow
- [app/services/grok/client.py](../app/services/grok/client.py) converts OpenAI-style messages into Grok payloads, uploads images concurrently, retries with proxy feedback, and records results via [app/services/call_log.py](../app/services/call_log.py); any new outbound call should report to `call_log_service` for observability.
- Response handling sits in [app/services/grok/processer.py](../app/services/grok/processer.py) which maintains SSE framing, `<think>` rendering, media caching, and timeout envelopes (`StreamTimeoutManager`); preserve those contracts if you tweak streaming.
- Video generation for `grok-imagine-0.9` goes through [app/services/grok/create.py](../app/services/grok/create.py) before the main request; reuse that workflow when introducing other media-first models.
## Media Caching & Delivery
- Image/video bytes are cached locally via [app/services/grok/cache.py](../app/services/grok/cache.py); [app/api/v1/images.py](../app/api/v1/images.py) rewrites `/images/<hashed-path>` to cache hits and needs `global.base_url` so Markdown links resolve externally.
- `global.image_mode` toggles between returning proxied URLs and base64 payloads; make sure new renderers respect that flag when assembling assistant content.
## Observability & Admin
- Call history persists in `data/call_logs.json`, capped via `global.log_max_count`; use the helpers in [app/services/call_log.py](../app/services/call_log.py) instead of writing files yourself.
- Admin API + UI (login, token import, cache purge, settings) live under `/api/*` in [app/api/admin/manage.py](../app/api/admin/manage.py); mirror its JSON shapes if you extend the dashboard.
- Health and root redirects are defined in [main.py](../main.py); keep `/health` lightweight for container probes.
## Developer Workflow
- Create `data/setting.toml` from the example, then run `STORAGE_MODE=file WORKERS=1 uvicorn main:app --host 0.0.0.0 --port 8001` (or `python main.py` for Windows) to match production wiring.
- For live reload during development, prefer `uvicorn main:app --reload` with single worker; the lifespan hook spins background tasks (token saver, proxy pool, call log) so watch the startup logs for failures.
- When debugging Grok calls, enable verbose logging via `global.log_level=DEBUG` and watch the structured messages in `app/core/logger.py` outputs.
## MCP & Tooling
- The FastMCP server in [app/services/mcp/server.py](../app/services/mcp/server.py) mounts onto the same ASGI app; new MCP tools should register via `@mcp.tool` and rely on shared Grok services to avoid duplicate auth flows.
- Keep third-party HTTP calls going through `curl_cffi` (see [requirements.txt](../requirements.txt)) to preserve browser impersonation; mismatched clients often trigger Grok TLS/403 defenses.
