"""Auth and transport wiring for the remote Cronometer MCP server.

Two mutually exclusive modes, chosen from env vars at startup:

1. GitHub OAuth (primary) — set GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, and
   GITHUB_ALLOWED_USERNAME (comma-separated GitHub logins). PUBLIC_BASE_URL
   must also be set to the server's public https URL. Any GitHub account can
   complete the OAuth handshake, but the AuthMiddleware below rejects every
   login except the allowlisted ones before a tool call is allowed to run.

2. Secret path (fallback) — set MCP_PATH_SECRET instead. No OAuth app
   needed; the MCP endpoint is mounted under an unguessable path segment
   instead of a fixed "/mcp". This is obscurity, not authentication — anyone
   who learns the URL has full access — so it only makes sense over HTTPS
   with a long random secret, e.g. `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

If neither mode is configured, startup fails loudly rather than binding an
unauthenticated endpoint to a public port.
"""
import os

from fastmcp.server.auth.providers.github import GitHubProvider
from fastmcp.server.middleware import AuthMiddleware
from fastmcp.utilities.authorization import AuthContext


def _github_login_allowlist(allowed_logins: set[str]):
    def check(ctx: AuthContext) -> bool:
        if ctx.token is None:
            return False
        login = str((ctx.token.claims or {}).get("login", "")).lower()
        return login in allowed_logins

    return check


def build_auth():
    """Return (auth_provider_or_None, middleware_list, mcp_path, mode_description)."""
    client_id = os.environ.get("GITHUB_CLIENT_ID")
    client_secret = os.environ.get("GITHUB_CLIENT_SECRET")
    allowed_raw = os.environ.get("GITHUB_ALLOWED_USERNAME", "")
    allowed_logins = {u.strip().lower() for u in allowed_raw.split(",") if u.strip()}
    path_secret = os.environ.get("MCP_PATH_SECRET")

    if client_id and client_secret:
        if not allowed_logins:
            raise RuntimeError(
                "GITHUB_CLIENT_ID/SECRET are set but GITHUB_ALLOWED_USERNAME is empty. "
                "Set it to your GitHub username (comma-separate for more than one) — "
                "otherwise any GitHub account could authenticate."
            )
        base_url = os.environ.get("PUBLIC_BASE_URL")
        if not base_url:
            raise RuntimeError(
                "PUBLIC_BASE_URL is required in GitHub OAuth mode (it's used for the "
                "OAuth redirect and must match your deployed https URL)."
            )
        auth = GitHubProvider(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
        )
        middleware = [AuthMiddleware(auth=_github_login_allowlist(allowed_logins))]
        return auth, middleware, "/mcp", f"GitHub OAuth, restricted to: {', '.join(sorted(allowed_logins))}"

    if path_secret:
        return None, [], f"/{path_secret}/mcp", "secret-path fallback (no OAuth)"

    raise RuntimeError(
        "Refusing to start an unauthenticated remote server. Set either:\n"
        "  - GITHUB_CLIENT_ID + GITHUB_CLIENT_SECRET + GITHUB_ALLOWED_USERNAME + PUBLIC_BASE_URL "
        "(GitHub OAuth, recommended), or\n"
        "  - MCP_PATH_SECRET (fallback: a long random path segment gates the endpoint instead)"
    )
