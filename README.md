# Cronometer MCP

**Cronometer nutrition tracking via a remote MCP server — no Gold subscription required.** Uses the mobile REST API to search foods, log meals, track macros, and manage fasting data through the Model Context Protocol.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)


## Features

- **No Gold Required** — Uses the free mobile API (`mobile.cronometer.com`)
- **Full Nutrition Tracking** — Search foods, log meals, track macros and micronutrients
- **Fasting Support** — View fasting history and statistics
- **Remote MCP server** — Streamable-HTTP transport (FastMCP), deployable anywhere that runs a container and gives you a `$PORT`
- **Gated access** — GitHub OAuth restricted to an allowlist of GitHub usernames, or a secret-URL-path fallback
- **No plaintext secrets** — Cronometer credentials and OAuth secrets are read from environment variables only


## How It Works

```
┌─────────────────┐   HTTPS    ┌──────────────────┐   HTTPS   ┌─────────────────┐
│  MCP Client      │──────────▶│  Cronometer MCP   │──────────▶│  Cronometer     │
│  (Claude, etc.)  │  OAuth or │  Server (this repo)│           │  Mobile API     │
└─────────────────┘  secret   └──────────────────┘           └─────────────────┘
                       path            │
                                       ▼
                              GitHub OAuth (optional)
                              restricted to an allowlist
                              of GitHub usernames
```

The server authenticates to Cronometer with standard email/password login, the same flow the mobile app uses. Your Cronometer credentials only ever leave the server bound for `mobile.cronometer.com` — never to any third party.

Access to the server itself is gated separately, before any Cronometer tool can be called — either by GitHub OAuth (recommended) or by a secret path segment in the URL (fallback, see [Auth modes](#auth-modes) below).


## MCP Tools

| Tool | Description |
|------|-------------|
| `search_foods` | Search Cronometer food database by name |
| `get_food_details` | Get full nutrition profile and serving sizes |
| `get_food_log` | Get diary entries for a date (defaults to today) |
| `get_daily_nutrition` | Get daily macro and micronutrient totals |
| `get_nutrition_scores` | Get nutrition category scores (Vitamins, Minerals, etc.) |
| `add_food_entry` | Log a food serving to your diary |
| `remove_food_entry` | Remove food entries from your diary by serving ID |
| `mark_day_complete` | Mark a diary day as complete or incomplete |
| `copy_day` | Copy entries from previous day to given date |
| `get_macro_targets` | Get weekly macro schedule and saved target templates |
| `get_fasting_history` | View fasts within a date range |
| `get_fasting_stats` | Aggregate fasting statistics |


## Configuration

All configuration is via environment variables — there is no config file.

| Variable | Required | Description |
|----------|----------|-------------|
| `CRONOMETER_USERNAME` | Yes | Your Cronometer email |
| `CRONOMETER_PASSWORD` | Yes | Your Cronometer password |
| `PORT` | No (default `8000`) | Port to listen on — set automatically by most PaaS platforms |
| `HOST` | No (default `0.0.0.0`) | Host to bind to |
| `GITHUB_CLIENT_ID` | For OAuth mode | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | For OAuth mode | GitHub OAuth App client secret |
| `GITHUB_ALLOWED_USERNAME` | For OAuth mode | Your GitHub username(s), comma-separated — anyone else who completes GitHub login is rejected |
| `PUBLIC_BASE_URL` | For OAuth mode | The server's public https URL (e.g. `https://cronometer-mcp-production.up.railway.app`) |
| `MCP_PATH_SECRET` | For secret-path mode | A long random string used as a URL path segment instead of OAuth |

The server refuses to start unless either the OAuth variables or `MCP_PATH_SECRET` are set — it will not bind an unauthenticated endpoint to a public port.


## Auth modes

### GitHub OAuth (recommended)

Set `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_ALLOWED_USERNAME`, and `PUBLIC_BASE_URL`. Any GitHub account can start the OAuth handshake, but a login not in `GITHUB_ALLOWED_USERNAME` is rejected before any tool call runs. The MCP endpoint is at `<PUBLIC_BASE_URL>/mcp`.

To create the GitHub OAuth App:
1. GitHub → Settings → Developer settings → OAuth Apps → **New OAuth App**
2. Homepage URL: `<PUBLIC_BASE_URL>`
3. Authorization callback URL: `<PUBLIC_BASE_URL>/auth/callback`
4. Copy the generated Client ID and Client secret into `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`

### Secret path (fallback)

Set `MCP_PATH_SECRET` instead (leave the `GITHUB_*` vars unset). No OAuth app needed — the MCP endpoint is mounted at `<PUBLIC_BASE_URL>/<MCP_PATH_SECRET>/mcp` instead of a fixed `/mcp`. Generate a secret with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

This is **obscurity, not authentication** — anyone who learns the full URL has full access to your Cronometer account via the server. Only use it over HTTPS, with a long random secret, and treat the URL itself as a credential (don't paste it anywhere public).


## Local development & testing

Requires Python 3.11+.

```bash
git clone https://github.com/fhthx/cronometer-mcp.git
cd cronometer-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

export CRONOMETER_USERNAME="your-email@example.com"
export CRONOMETER_PASSWORD="your-password"
export MCP_PATH_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
export PORT=8000

python cronometer_mcp_server.py
```

Test it with the [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
npx @modelcontextprotocol/inspector
```

In the Inspector UI: **Add Servers → Add manually**, set Transport to `streamable-http`, and use `http://127.0.0.1:8000/<MCP_PATH_SECRET>/mcp` as the URL (print `$MCP_PATH_SECRET` to get the value). Connect, open the **Tools** tab, and confirm all 12 tools are listed. Running `search_foods` will confirm the request reaches `mobile.cronometer.com` even if you don't want to fully verify a real search result.

GitHub OAuth mode is harder to exercise purely locally since it needs a public callback URL; verify it after deploying (below), or register a GitHub OAuth App with a `http://localhost:<port>/auth/callback` callback for local-only testing.


## Deploying to Railway

1. Push this repo (or your fork) to GitHub.
2. In Railway: **New Project → Deploy from GitHub repo**, select the repo. Railway detects the `Dockerfile` and builds it automatically.
3. In the service's **Variables** tab, set `CRONOMETER_USERNAME`, `CRONOMETER_PASSWORD`, and either the `GITHUB_*` + `PUBLIC_BASE_URL` set or `MCP_PATH_SECRET`. Railway sets `PORT` itself — don't set it manually.
4. Under **Settings → Networking**, click **Generate Domain** to get a public `https://*.up.railway.app` URL.
5. If using GitHub OAuth: set `PUBLIC_BASE_URL` to that domain, and use the same domain's `/auth/callback` as the OAuth App's callback URL (see [Auth modes](#auth-modes)). Redeploy after setting `PUBLIC_BASE_URL` so the server picks it up.
6. Connect your MCP client to `https://<your-domain>/mcp` (OAuth mode) or `https://<your-domain>/<MCP_PATH_SECRET>/mcp` (secret-path mode).

Building and running locally with Docker, if you want to test the exact deployed image first:

```bash
docker build -t cronometer-mcp .
docker run -p 8000:8000 \
  -e CRONOMETER_USERNAME=... \
  -e CRONOMETER_PASSWORD=... \
  -e MCP_PATH_SECRET=... \
  -e PORT=8000 \
  cronometer-mcp
```


## Security

- **Credentials scoped to Cronometer**: `CRONOMETER_USERNAME`/`PASSWORD` are only ever sent to `mobile.cronometer.com` (login, diary, food-search, and delete endpoints) — never to any other host.
- **No plaintext config**: all secrets come from environment variables; there is no on-disk credential file.
- **Gated by default**: the server refuses to start without either GitHub OAuth configuration or `MCP_PATH_SECRET` — there's no way to accidentally expose it unauthenticated.
- **GitHub OAuth is identity-based**: access is restricted to the exact GitHub logins in `GITHUB_ALLOWED_USERNAME`, checked on every request, not just at login.


## Troubleshooting

### Login Failures

If you get "Login failed" errors:
1. Verify your credentials are correct
2. Check if you're rate-limited (wait a few minutes)
3. Ensure your Cronometer account is active

### Rate Limiting

The API may rate-limit after many rapid requests. The server includes retry logic with exponential backoff.

### Connection Issues

If the server can't reach Cronometer:
1. Check the deployment's outbound internet access
2. Verify `mobile.cronometer.com` is reachable from it
3. Check for any firewall or egress restrictions on your hosting platform


## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request


## License

All rights reserved.


## Acknowledgments

- Built with [FastMCP](https://gofastmcp.com)
- Uses [httpx](https://github.com/encode/httpx) for HTTP requests
- Inspired by the need for free nutrition tracking in AI agents
